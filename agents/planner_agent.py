"""Constraint-based itinerary scheduler with Geographic Clustering, Day Themes, and Local Food.

The planner selects, arranges, and schedules destination-locked structured place entities 
using a multi-candidate generative search and scoring engine.
"""
from __future__ import annotations

import json
import os
import re
import math
import random
from typing import Any

from agents.constants import normalize_destination
from agents.rag_agent import retrieve_place_entities

SYSTEM_PROMPT = "Internal only: deterministic scheduler. No creative generation."

# Load place geographics as a global fallback map for coordinates/clusters
def load_place_geographics() -> dict[str, dict]:
    try:
        path = os.path.join(os.path.dirname(__file__), "../rag_data/travel_data.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return {
            item["place"].lower(): {
                "coordinates": item.get("coordinates", [0.0, 0.0]),
                "cluster": item.get("cluster", "Unknown"),
                "food": item.get("food", ""),
                "description": item.get("description", "")
            }
            for item in data
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {}

m_geo = load_place_geographics()

def build_planner_input(structured_query: dict, behavior_profile: dict, allowed_places: list[dict]) -> dict:
    destination = normalize_destination(structured_query.get("destination", ""))
    clean_places = []
    for place in allowed_places:
        if place.get("destination", "").lower() != destination.lower():
            continue
        name = place["name"]
        geo_info = m_geo.get(name.lower(), {})
        clean_places.append({
            "name": name,
            "destination": place["destination"],
            "category": place["category"],
            "tags": place.get("tags", []),
            "crowd_level": place.get("crowd_level", "normal"),
            "ideal_time": place.get("ideal_time", "morning"),
            "duration_hours": place.get("duration_hours", 2),
            "food": place.get("food") or geo_info.get("food", ""),
            "nightlife": place.get("nightlife", ""),
            "culture": place.get("culture", ""),
            "shopping": place.get("shopping", ""),
            "nature": place.get("nature", ""),
            "adventure": place.get("adventure", ""),
            "hidden_gems": place.get("hidden_gems", ""),
            "transport_tips": place.get("transport_tips") or "Local transit available",
            "local_tips": place.get("local_tips") or "Standard entry requirements apply",
            "recommended_duration": place.get("recommended_duration") or "2 hours",
            "best_visiting_time": place.get("best_visiting_time") or "morning",
            "budget_category": place.get("budget_category") or "Free entry",
            "coordinates": geo_info.get("coordinates", [0.0, 0.0]),
            "cluster": geo_info.get("cluster", "Unknown"),
            "description": geo_info.get("description", "")
        })
    return {
        "destination": destination,
        "days": int(structured_query.get("days", 3)),
        "budget": int(structured_query.get("budget", 20000)),
        "cards": structured_query.get("cards", []),
        "avoid": structured_query.get("avoid", []),
        "behavior_profile": behavior_profile,
        "allowed_places": clean_places,
    }

def _slot(activity: str, location: str, duration: str, transport: str, notes: str, time: str, expected_cost: str = "Free entry") -> dict:
    return {
        "time": time,
        "activity": activity,
        "location": location,
        "duration": duration,
        "transport": transport,
        "notes": notes,
        "expected_cost": expected_cost,
    }

def _duration_text(hours: float | int | str) -> str:
    try:
        value = float(hours)
    except Exception:
        return "2 hours"
    return f"{int(value)} hours" if value.is_integer() else f"{value:g} hours"

def get_local_food_recommendation(destination: str, meal: str, place_name: str) -> str:
    place_info = m_geo.get(place_name.lower(), {})
    place_food = place_info.get("food", "")
    
    foods = {
        "Manali": {
            "Breakfast": "Hot steamed sweet Siddu or Babru with tea",
            "Lunch": "Traditional Himachali Tudkiya Bhath at a local dhaba",
            "Dinner": "Wood-fired local Trout Fish with herbs or traditional Siddu with hot ghee"
        },
        "Goa": {
            "Breakfast": "Goan poi bread with local jam or fresh fruit smoothies",
            "Lunch": "Spicy Goan Fish Curry Rice or rava fried calamari",
            "Dinner": "Freshly prepared Prawn Balchao followed by traditional sweet Bebinca"
        },
        "Jaipur": {
            "Breakfast": "Hot Pyaaz kachori and sweet saffron Lassi",
            "Lunch": "Traditional Rajasthani Dal Baati Churma cooked in pure ghee",
            "Dinner": "Authentic royal thali followed by sweet Ghewar"
        },
        "Kullu": {
            "Breakfast": "Local Himachali Babru and hot tea",
            "Lunch": "Tudkiya Bhath and simple local lentils",
            "Dinner": "Pan-fried local Trout Fish or hot springs Langar meals"
        }
    }.get(destination, {
        "Breakfast": "Simple local breakfast dishes",
        "Lunch": "Local regional cuisine specialty",
        "Dinner": "Traditional local dinner recipes"
    })
    
    selected_food = foods.get(meal, "local specialities")
    if place_food and any(kw in place_food.lower() for kw in ["siddu", "trout", "babru", "bhath", "curry", "balchao", "bebinca", "baati", "ghewar", "langar"]):
        return f"{place_food} near {place_name}"
    return f"{selected_food} near {place_name}"

def _activity_label(place: dict, slot: str) -> str:
    name = place["name"]
    category = place.get("category", "experience")
    labels = {
        "adventure": f"{name} — adventure activity",
        "scenic": f"{name} — scenic stop",
        "nature": f"{name} — nature visit",
        "beach": f"{name} — beach time",
        "culture": f"{name} — cultural walk",
        "heritage": f"{name} — heritage visit",
        "shopping": f"{name} — shopping walk",
        "food": f"{name} — food stop",
        "cafe/culture": f"{name} — cafes and local walk",
    }
    if slot == "evening" and category not in labels:
        return f"{name} — relaxed evening"
    return labels.get(category, f"{name} — {category}")

def compute_distance(coords1: list[float], coords2: list[float]) -> float:
    if not coords1 or not coords2 or coords1 == [0.0, 0.0] or coords2 == [0.0, 0.0]:
        return 1.0
    return math.sqrt((coords1[0] - coords2[0])**2 + (coords1[1] - coords2[1])**2)

def get_geographic_distance(p1: dict, p2: dict) -> float:
    c1 = p1.get("coordinates", [0.0, 0.0])
    c2 = p2.get("coordinates", [0.0, 0.0])
    dist = compute_distance(c1, c2)
    if p1.get("cluster") != p2.get("cluster"):
        dist += 0.2
    return dist

def generate_day_theme(day_places: list[dict]) -> str:
    categories = [p.get("category", "") for p in day_places]
    if "culture" in categories or "heritage" in categories:
        if "nature" in categories or "scenic" in categories:
            return "Culture & Scenic Vistas"
        return "Heritage & Culture Tour"
    elif "nature" in categories or "scenic" in categories:
        if "adventure" in categories:
            return "Nature & Outdoor Adventure"
        return "Scenic Nature & Springs"
    elif "shopping" in categories or "cafe/culture" in categories:
        return "Local Markets & Cafe Hopping"
    else:
        cats = list(set([c.title() for c in categories if c]))
        return " + ".join(cats)

def generate_narrative(morning: dict, afternoon: dict, evening: dict) -> str:
    m_name = morning["name"]
    a_name = afternoon["name"]
    e_name = evening["name"]
    m_desc = morning.get("description", "explore the beautiful local landmarks.")
    a_desc = afternoon.get("description", "visit the scenic sights.")
    e_desc = evening.get("description", "enjoy the local evening vibes.")
    
    return (
        f"Spend a wonderful day touring {m_name}, {a_name}, and {e_name}. "
        f"Start your morning exploring {m_name}, which is {m_desc.lower().rstrip('.')}. "
        f"In the afternoon, head towards {a_name} to {a_desc.lower().rstrip('.')}. "
        f"Conclude your evening at {e_name}, a perfect place to {e_desc.lower().rstrip('.')}."
    )

def estimate_daily_budget(day_places: list[dict], budget_style: str) -> str:
    base_food = {"budget": 600, "balanced": 1000, "premium": 2000}.get(budget_style, 1000)
    base_transit = {"budget": 400, "balanced": 1000, "premium": 2500}.get(budget_style, 1000)
    
    activity_cost = 0.0
    for p in day_places:
        cost_cat = p.get("budget_category", "Free entry").lower()
        if "free" in cost_cat:
            continue
        nums = [int(n) for n in re.findall(r"\d+", cost_cat)]
        if nums:
            activity_cost += sum(nums) / len(nums)
        else:
            activity_cost += 100
            
    total_day = base_food + base_transit + activity_cost
    return f"₹{int(total_day):,} per person (covers transport, local meals, and entry/activity costs)"

def score_itinerary(candidate: list[dict], planner_input: dict) -> float:
    all_places = []
    for day in candidate:
        all_places.extend([day["morning"], day["afternoon"], day["evening"]])
        
    place_names = [p["name"] for p in all_places]
    
    # 1. Uniqueness check (crucial constraint)
    duplicates = len(place_names) - len(set(place_names))
    uniqueness_penalty = -10000000.0 * duplicates if duplicates > 0 else 1000.0
    
    same_day_duplicates = 0
    for day in candidate:
        day_names = [day["morning"]["name"], day["afternoon"]["name"], day["evening"]["name"]]
        if len(day_names) != len(set(day_names)):
            same_day_duplicates += 1
    if same_day_duplicates > 0:
        uniqueness_penalty -= 10000000.0 * same_day_duplicates
    
    # 2. Coverage score (maximizing destination exploration and categories)
    categories = set(p.get("category", "") for p in all_places)
    coverage_score = len(categories) * 200.0 + len(set(place_names)) * 100.0
    
    # 3. Distance and clustering score
    total_distance = 0.0
    for day in candidate:
        d1 = get_geographic_distance(day["morning"], day["afternoon"])
        d2 = get_geographic_distance(day["afternoon"], day["evening"])
        total_distance += (d1 + d2)
    distance_penalty = -5000.0 * total_distance
    
    # 4. Preference match score
    profile = planner_input.get("behavior_profile", {})
    avoid = set((profile.get("avoid_categories") or []))
    avoid_words = set(planner_input.get("avoid", []))
    pref_score = 0.0
    
    for p in all_places:
        p_cat = p.get("category", "")
        p_tags = p.get("tags", [])
        
        # Avoid category checks
        if p_cat in avoid:
            pref_score -= 15000.0
        for tag in p_tags:
            if tag in avoid or tag in avoid_words:
                pref_score -= 15000.0
                
        # Positive preferences
        interests = set(profile.get("activity_style", []))
        for interest in interests:
            if interest.lower() in p_cat.lower() or any(interest.lower() in t.lower() for t in p_tags):
                pref_score += 150.0
                
        # Cafe style food match
        food_style = profile.get("food_style", "local")
        if food_style == "cafes" and p_cat == "cafe/culture":
            pref_score += 300.0
            
        # Crowd preference
        crowd_pref = profile.get("crowd_preference", "neutral")
        if crowd_pref == "avoid_crowds" and p.get("crowd_level") == "crowded":
            pref_score -= 1000.0
            
    return uniqueness_penalty + coverage_score + distance_penalty + pref_score

def generate_candidates(pool: list[dict], days: int) -> list[list[dict]]:
    candidates = []
    
    # Group by cluster
    clusters = {}
    for p in pool:
        c = p.get("cluster", "Unknown")
        clusters.setdefault(c, []).append(p)
        
    sorted_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)
    
    # 1. Cluster-based baseline candidate
    if len(sorted_clusters) >= days:
        baseline = []
        used = set()
        for d in range(days):
            day_cluster_places = sorted_clusters[d][1]
            day_selection = [p for p in day_cluster_places if p["name"] not in used]
            if len(day_selection) < 3:
                day_selection += [p for p in pool if p["name"] not in used and p not in day_selection]
            
            # Pad if still short
            while len(day_selection) < 3:
                for p in pool:
                    if p not in day_selection:
                        day_selection.append(p)
                        break
                else:
                    day_selection.append(pool[0])
                
            morning = next((p for p in day_selection if p.get("ideal_time") == "morning"), day_selection[0])
            evening = next((p for p in day_selection if p.get("ideal_time") == "evening" and p != morning), day_selection[-1])
            afternoon = next((p for p in day_selection if p != morning and p != evening), day_selection[1] if len(day_selection) > 1 else day_selection[0])
            
            baseline.append({
                "morning": morning,
                "afternoon": afternoon,
                "evening": evening
            })
            used.update([morning["name"], afternoon["name"], evening["name"]])
        candidates.append(baseline)
        
    # 2. Random unique shuffles (generate 2000 variations)
    for _ in range(2000):
        shuffled_pool = list(pool)
        random.shuffle(shuffled_pool)
        
        used_here = set()
        candidate_days = []
        for d in range(days):
            day_places = []
            for slot in range(3):
                chosen = None
                for p in shuffled_pool:
                    if p["name"] not in used_here:
                        chosen = p
                        break
                if not chosen:
                    for p in shuffled_pool:
                        if p not in day_places:
                            chosen = p
                            break
                if not chosen:
                    chosen = shuffled_pool[slot % len(shuffled_pool)]
                day_places.append(chosen)
                used_here.add(chosen["name"])
                
            morning = next((p for p in day_places if p.get("ideal_time") == "morning"), day_places[0])
            evening = next((p for p in day_places if p.get("ideal_time") == "evening" and p != morning), day_places[-1])
            afternoon = next((p for p in day_places if p != morning and p != evening), day_places[1] if len(day_places) > 1 else day_places[0])
            
            candidate_days.append({
                "morning": morning,
                "afternoon": afternoon,
                "evening": evening
            })
        candidates.append(candidate_days)
        
    return candidates

def assemble_schedule(planner_input: dict) -> dict[str, Any]:
    destination = planner_input.get("destination", "Goa")
    days = int(planner_input.get("days", 3))
    profile = planner_input.get("behavior_profile", {})
    avoid = " ".join(planner_input.get("avoid", [])).lower()
    pool = [p for p in planner_input.get("allowed_places", []) if p["name"].lower() not in avoid]
    
    avoid_cats = set(profile.get("avoid_categories", []))
    if avoid_cats:
        filtered_pool = [p for p in pool if p.get("category") not in avoid_cats]
        pool = filtered_pool or pool
        
    if profile.get("crowd_preference") == "avoid_crowds":
        quiet = [p for p in pool if p.get("crowd_level") != "crowded"]
        pool = quiet or pool
        
    if not pool:
        pool = planner_input.get("allowed_places", [])
    if not pool:
        return {
            "destination": destination,
            "days": [],
            "planning_notes": [f"No destination-specific place pool is available for {destination}."],
        }
    
    # Generate and Score candidates
    candidates = generate_candidates(pool, days)
    scored = [(score_itinerary(cand, planner_input), cand) for cand in candidates]
    scored.sort(key=lambda x: x[0], reverse=True)
    best_candidate = scored[0][1]
    
    slow = profile.get("pace") == "slow"
    pacing = (
        "Relaxed slow-paced travel with broad meal windows, transfer buffers, and restorative rest time."
        if slow else
        "Moderate pacing with optimized transfers, localized clustering, and no backtracking."
    )
    
    plan_days = []
    budget_style = profile.get("budget_style", "balanced")
    
    for i, day_item in enumerate(best_candidate):
        d_num = i + 1
        m_place = day_item["morning"]
        a_place = day_item["afternoon"]
        e_place = day_item["evening"]
        
        day_places = [m_place, a_place, e_place]
        theme = generate_day_theme(day_places)
        narrative = generate_narrative(m_place, a_place, e_place)
        daily_budget = estimate_daily_budget(day_places, budget_style)
        
        plan_days.append({
            "day": d_num,
            "theme": theme,
            "base_area": destination,
            "narrative": narrative,
            "daily_budget": daily_budget,
            "morning": [_slot(
                _activity_label(m_place, "morning"),
                m_place["name"],
                m_place.get("recommended_duration") or _duration_text(m_place.get("duration_hours", 2)),
                m_place.get("transport_tips") or "Local cab/auto; start after breakfast",
                m_place.get("local_tips") or "Keep one transfer buffer before lunch.",
                "09:00",
                expected_cost=m_place.get("budget_category", "Free entry")
            )],
            "afternoon": [_slot(
                _activity_label(a_place, "afternoon"),
                a_place["name"],
                a_place.get("recommended_duration") or _duration_text(a_place.get("duration_hours", 2)),
                a_place.get("transport_tips") or "Short local transfer after lunch",
                a_place.get("local_tips") or "Keep the afternoon focused on one main area.",
                "13:30",
                expected_cost=a_place.get("budget_category", "Free entry")
            )],
            "evening": [_slot(
                _activity_label(e_place, "evening"),
                e_place["name"],
                e_place.get("recommended_duration") or _duration_text(min(float(e_place.get("duration_hours", 2)), 2)),
                e_place.get("transport_tips") or "Walk/auto depending on hotel area",
                e_place.get("local_tips") or "Keep this light and close with dinner nearby.",
                "18:00",
                expected_cost=e_place.get("budget_category", "Free entry")
            )],
            "food_recommendations": [
                {"meal": "Breakfast", "suggestion": get_local_food_recommendation(destination, "Breakfast", m_place["name"]), "area": destination},
                {"meal": "Lunch", "suggestion": get_local_food_recommendation(destination, "Lunch", a_place["name"]), "area": destination},
                {"meal": "Dinner", "suggestion": get_local_food_recommendation(destination, "Dinner", e_place["name"]), "area": destination},
            ],
            "pacing": pacing,
        })
        
    return {
        "destination": destination,
        "days": plan_days,
        "planning_notes": [
            f"Optimized schedule. Evaluated {len(candidates)} candidates. Best score: {scored[0][0]:.2f}",
        ],
    }

def itinerary_to_text(plan: dict[str, Any]) -> str:
    lines: list[str] = []
    for day in plan.get("days", []):
        day_num = day.get("day")
        theme = day.get("theme", "Explore")
        lines.append(f"### Day {day_num} — {theme}")
        lines.append(f"**Narrative Vibe**: {day.get('narrative', '')}")
        lines.append("")
        
        # Morning
        lines.append("🌅 **Morning Plan**:")
        for m in day.get("morning", []):
            lines.append(f"- **{m.get('location')}** ({m.get('activity')})")
            lines.append(f"  *Duration*: {m.get('duration')} | *Transit*: {m.get('transport')}")
            lines.append(f"  *Local Expert Tip*: {m.get('notes')}")
        lines.append("")
        
        # Lunch
        lunch_rec = ""
        for f in day.get("food_recommendations", []):
            if f.get("meal") == "Lunch":
                lunch_rec = f.get("suggestion")
        lines.append("🍽️ **Lunch Recommendation**:")
        lines.append(f"- {lunch_rec or 'Sample authentic local foods.'}")
        lines.append("")
        
        # Afternoon
        lines.append("☀️ **Afternoon Plan**:")
        for a in day.get("afternoon", []):
            lines.append(f"- **{a.get('location')}** ({a.get('activity')})")
            lines.append(f"  *Duration*: {a.get('duration')} | *Transit*: {a.get('transport')}")
            lines.append(f"  *Local Expert Tip*: {a.get('notes')}")
        lines.append("")
        
        # Evening
        lines.append("🌙 **Evening Plan**:")
        for e in day.get("evening", []):
            lines.append(f"- **{e.get('location')}** ({e.get('activity')})")
            lines.append(f"  *Duration*: {e.get('duration')} | *Transit*: {e.get('transport')}")
            lines.append(f"  *Local Expert Tip*: {e.get('notes')}")
        lines.append("")
        
        # Dinner
        dinner_rec = ""
        for f in day.get("food_recommendations", []):
            if f.get("meal") == "Dinner":
                dinner_rec = f.get("suggestion")
        lines.append("🍷 **Dinner Recommendation**:")
        lines.append(f"- {dinner_rec or 'Sample authentic local evening specialties.'}")
        lines.append("")
        
        # Daily Budget
        lines.append(f"💵 **Daily Budget**: {day.get('daily_budget', 'Standard local costs apply.')}")
        lines.append("")
        
        # Travel Tips
        lines.append("💡 **Day Travel Tips & Pacing**:")
        lines.append(f"- {day.get('pacing', 'Paced for moderate activity.')}")
        for slot in ["morning", "afternoon", "evening"]:
            for item in day.get(slot, []):
                lines.append(f"- For {item.get('location')}: {item.get('notes')}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
    return "\n".join(lines).strip()

def run_planner_agent(
    structured_query: dict,
    user_id: str,
    behavior_profile: dict | None = None,
    allowed_places: list[dict] | None = None,
) -> dict[str, Any]:
    destination = normalize_destination(structured_query.get("destination", ""))
    interests = structured_query.get("interests", [])
    needed_places = int(structured_query.get("days", 3)) * 3 + 6
    allowed_places = allowed_places or retrieve_place_entities(destination, interests, n=needed_places)
    behavior_profile = behavior_profile or {
        "pace": structured_query.get("travel_pace", "medium"),
        "food_style": structured_query.get("food_preference", "local"),
        "travel_style": structured_query.get("travel_style", "moderate"),
        "budget_style": "balanced",
        "crowd_preference": "neutral",
        "activity_style": structured_query.get("interests", []),
        "avoid_categories": [],
    }
    planner_input = build_planner_input(structured_query, behavior_profile, allowed_places)
    return assemble_schedule(planner_input)
