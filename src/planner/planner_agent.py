"""Constraint-based itinerary scheduler with Geographic Clustering, Day Themes, and Local Food.

The planner selects, arranges, and schedules destination-locked structured place entities 
using LLM generation as the primary execution path and a fallback rule-engine scheduler.
"""
from __future__ import annotations

import json
import os
import re
import math
import random
from typing import Any

from agents.constants import normalize_destination
from rag.rag_agent import retrieve_place_entities
from agents.common import invoke_json

SYSTEM_PROMPT = """You are an elite travel consultant.
Generate a realistic itinerary.
Optimize:
* travel time
* geography
* budget
* pacing
* user interests
* weather
* operating hours

You must return ONLY a valid JSON object matching the following structure:
{
  "destination": "Name of the destination",
  "days": [
    {
      "day": 1,
      "theme": "Theme of the day",
      "narrative": "A paragraph describing the daily adventure narrative",
      "daily_budget": "Estimated budget description, e.g. ₹4,000",
      "pacing": "Pacing description, e.g. Moderate",
      "morning": [
        {
          "time": "09:00",
          "location": "Attraction Name",
          "activity": "Activity description",
          "duration": "Duration in hours",
          "transport": "Transit method details",
          "notes": "Expert local advice, historical tips, or reservation warnings",
          "expected_cost": "Estimated admission cost or Free"
        }
      ],
      "afternoon": [
        {
          "time": "13:30",
          "location": "Attraction Name",
          "activity": "Activity description",
          "duration": "Duration in hours",
          "transport": "Transit method details",
          "notes": "Expert local advice",
          "expected_cost": "Estimated admission cost or Free"
        }
      ],
      "evening": [
        {
          "time": "18:00",
          "location": "Attraction Name",
          "activity": "Activity description",
          "duration": "Duration in hours",
          "transport": "Transit method details",
          "notes": "Expert local advice",
          "expected_cost": "Estimated admission cost or Free"
        }
      ],
      "food_recommendations": [
        {"meal": "Breakfast", "suggestion": "Breakfast suggestion"},
        {"meal": "Lunch", "suggestion": "Lunch suggestion"},
        {"meal": "Dinner", "suggestion": "Dinner suggestion"}
      ]
    }
  ],
  "planning_notes": [
    "General notes about the trip, weather, packing tips"
  ]
}

Ensure every single attraction comes from LLM reasoning, geographical proximity, and logical sequencing. Do not use hardcoded lists.
Do not output any explanation or markdown formatting, output ONLY JSON."""

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
        place_dest = place.get("destination") or destination
        if place_dest.lower() != destination.lower():
            continue
        name = place["name"]
        geo_info = m_geo.get(name.lower(), {})
        clean_places.append({
            "name": name,
            "destination": place_dest,
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
    from agents.demo_data import DEMO_FOOD
    place_info = m_geo.get(place_name.lower(), {})
    place_food = place_info.get("food", "")
    
    selected_food = DEMO_FOOD.get(destination, {
        "Breakfast": "Simple local breakfast dishes",
        "Lunch": "Local regional cuisine specialty",
        "Dinner": "Traditional local dinner recipes"
    }).get(meal, "local specialities")
    
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
        
    place_names = [p["name"].lower() for p in all_places]
    
    # 1. Uniqueness check
    duplicates = len(place_names) - len(set(place_names))
    uniqueness_penalty = -10000000.0 * duplicates if duplicates > 0 else 1000.0
    
    same_day_duplicates = 0
    for day in candidate:
        day_names = [day["morning"]["name"].lower(), day["afternoon"]["name"].lower(), day["evening"]["name"].lower()]
        if len(day_names) != len(set(day_names)):
            same_day_duplicates += 1
    if same_day_duplicates > 0:
        uniqueness_penalty -= 10000000.0 * same_day_duplicates
    
    # 2. Coverage score
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
        
        # Avoid checks
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
    clusters = {}
    for p in pool:
        c = p.get("cluster", "Unknown")
        clusters.setdefault(c, []).append(p)
        
    sorted_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)
    
    if len(sorted_clusters) >= days:
        baseline = []
        used = set()
        for d in range(days):
            day_cluster_places = sorted_clusters[d][1]
            day_selection = [p for p in day_cluster_places if p["name"].lower() not in used]
            if len(day_selection) < 3:
                day_selection += [p for p in pool if p["name"].lower() not in used and p not in day_selection]
            
            while len(day_selection) < 3:
                for p in pool:
                    if p["name"].lower() not in used and p not in day_selection:
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
            used.update([morning["name"].lower(), afternoon["name"].lower(), evening["name"].lower()])
        candidates.append(baseline)
        
    for _ in range(2000):
        shuffled_pool = list(pool)
        random.shuffle(shuffled_pool)
        
        used_here = set()
        candidate_days = []
        for d in range(days):
            day_places = []
            day_names_lower = set()
            for slot in range(3):
                chosen = None
                for p in shuffled_pool:
                    if p["name"].lower() not in used_here:
                        chosen = p
                        break
                if not chosen:
                    for p in shuffled_pool:
                        if p["name"].lower() not in day_names_lower:
                            chosen = p
                            break
                if not chosen:
                    chosen = shuffled_pool[slot % len(shuffled_pool)]
                day_places.append(chosen)
                used_here.add(chosen["name"].lower())
                day_names_lower.add(chosen["name"].lower())
                
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
    destination = planner_input.get("destination", "Destination")
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
        from agents.demo_data import DEMO_ATTRACTIONS
        if destination in DEMO_ATTRACTIONS:
            pool = []
            categories = ["scenic", "culture", "shopping", "food", "adventure"]
            for idx, name in enumerate(DEMO_ATTRACTIONS[destination]):
                cat = categories[idx % len(categories)]
                pool.append({
                    "name": name,
                    "category": cat,
                    "destination": destination,
                    "ideal_time": "morning" if idx % 3 == 0 else "afternoon" if idx % 3 == 1 else "evening",
                    "duration_hours": 2,
                    "crowd_level": "normal"
                })
        else:
            from agents.demo_data import GENERIC_CLEAN_ATTRACTIONS
            pool = []
            categories = ["scenic", "culture", "shopping", "food", "adventure"]
            for idx, name in enumerate(GENERIC_CLEAN_ATTRACTIONS):
                cat = categories[idx % len(categories)]
                pool.append({
                    "name": name,
                    "category": cat,
                    "destination": destination,
                    "ideal_time": "morning" if idx % 3 == 0 else "afternoon" if idx % 3 == 1 else "evening",
                    "duration_hours": 2,
                    "crowd_level": "normal"
                })
            
    # Ensure pool size is at least days * 3 to avoid duplicates
    required_count = days * 3
    if len(pool) < required_count:
        from agents.demo_data import DEMO_ATTRACTIONS, GENERIC_CLEAN_ATTRACTIONS
        existing_names = {p["name"].lower() for p in pool}
        categories = ["scenic", "culture", "shopping", "food", "adventure"]
        
        # 1. Pull from destination-specific demo registry first
        demo_list = DEMO_ATTRACTIONS.get(destination, [])
        for idx, name in enumerate(demo_list):
            if name.lower() not in existing_names:
                cat = categories[idx % len(categories)]
                pool.append({
                    "name": name,
                    "category": cat,
                    "destination": destination,
                    "ideal_time": "morning" if idx % 3 == 0 else "afternoon" if idx % 3 == 1 else "evening",
                    "duration_hours": 2,
                    "crowd_level": "normal"
                })
                existing_names.add(name.lower())
                
        # 2. If pool size is still too small, pull from generic non-contaminated clean attractions
        if len(pool) < required_count:
            for idx, name in enumerate(GENERIC_CLEAN_ATTRACTIONS):
                if name.lower() not in existing_names:
                    cat = categories[idx % len(categories)]
                    pool.append({
                        "name": name,
                        "category": cat,
                        "destination": destination,
                        "ideal_time": "morning" if idx % 3 == 0 else "afternoon" if idx % 3 == 1 else "evening",
                        "duration_hours": 2,
                        "crowd_level": "normal"
                    })
                    existing_names.add(name.lower())
                if len(pool) >= required_count:
                    break
    
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
            f"Fallback schedule. Evaluated {len(candidates)} candidates. Best score: {scored[0][0]:.2f}",
        ],
    }

def map_llm_to_standard_itinerary(llm_out: dict, destination: str, allowed_places: list[dict] | None = None) -> dict:
    if not isinstance(llm_out, dict):
        return {"destination": destination, "days": [], "planning_notes": ["Invalid planner response."]}
        
    visited_places = set()
    
    # Compile forbidden templates
    FORBIDDEN_TEMPLATES = [
        r"panoramic city viewpoint",
        r"central botanical gardens",
        r"scenic riverside promenade",
        r"historic old town square",
        r"national history museum",
        r"local food street",
        r"traditional craft bazaar",
        r"sunset hill lookout",
        r"sunset peak",
        r"central gardens",
        r"scenic viewpoint",
        r"heritage street",
        r"museum of .* history",
        r"local .* bazaar"
    ]
    
    def is_forbidden_template(name: str) -> bool:
        name_lower = name.lower()
        for pattern in FORBIDDEN_TEMPLATES:
            if re.search(pattern, name_lower):
                return True
        return False

    def get_alternative_attraction() -> str:
        # 1. Try allowed_places
        if allowed_places:
            for place in allowed_places:
                name = place.get("name", "")
                if name and name.lower() not in visited_places and not is_forbidden_template(name):
                    visited_places.add(name.lower())
                    return name
        
        # 2. Try DEMO_ATTRACTIONS
        from agents.demo_data import DEMO_ATTRACTIONS
        demo_list = DEMO_ATTRACTIONS.get(destination, [])
        for name in demo_list:
            if name.lower() not in visited_places and not is_forbidden_template(name):
                visited_places.add(name.lower())
                return name
                
        # 3. Try GENERIC_CLEAN_ATTRACTIONS
        from agents.demo_data import GENERIC_CLEAN_ATTRACTIONS
        for name in GENERIC_CLEAN_ATTRACTIONS:
            if name.lower() not in visited_places and not is_forbidden_template(name):
                visited_places.add(name.lower())
                return name
                
        return "Unique Attraction Spot"

    def process_location(loc: str) -> str:
        if not loc or loc.strip().lower() in visited_places or is_forbidden_template(loc):
            return get_alternative_attraction()
        visited_places.add(loc.strip().lower())
        return loc.strip()

    days_list = []
    
    # Sort day keys numerically
    day_keys = [k for k in llm_out.keys() if k.startswith("day_")]
    if day_keys:
        day_keys.sort(key=lambda x: int(re.search(r"\d+", x).group(0)) if re.search(r"\d+", x) else 0)
        for idx, key in enumerate(day_keys):
            day_data = llm_out[key]
            day_num = idx + 1
            
            # Morning
            m_data = day_data.get("morning", {})
            m_loc = process_location(m_data.get("location", ""))
            morning_slot = {
                "time": "09:00",
                "activity": m_data.get("activity") or f"Visit {m_loc}",
                "location": m_loc,
                "duration": m_data.get("duration") or "2 hours",
                "transport": m_data.get("transport") or "Local transport",
                "notes": m_data.get("notes") or "Start early",
                "expected_cost": m_data.get("cost") or m_data.get("expected_cost") or "Free"
            }
            
            # Afternoon
            a_data = day_data.get("afternoon", {})
            a_loc = process_location(a_data.get("location", ""))
            afternoon_slot = {
                "time": "13:30",
                "activity": a_data.get("activity") or f"Visit {a_loc}",
                "location": a_loc,
                "duration": a_data.get("duration") or "2 hours",
                "transport": a_data.get("transport") or "Local transport",
                "notes": a_data.get("notes") or "Keep hydrated",
                "expected_cost": a_data.get("cost") or a_data.get("expected_cost") or "Free"
            }
            
            # Evening
            e_data = day_data.get("evening", {})
            e_loc = process_location(e_data.get("location", ""))
            evening_slot = {
                "time": "18:00",
                "activity": e_data.get("activity") or f"Visit {e_loc}",
                "location": e_loc,
                "duration": e_data.get("duration") or "2 hours",
                "transport": e_data.get("transport") or "Local transport",
                "notes": e_data.get("notes") or "Enjoy the sunset",
                "expected_cost": e_data.get("cost") or e_data.get("expected_cost") or "Free"
            }
            
            # Meals
            meals = day_data.get("meals", {})
            food_recs = [
                {"meal": "Breakfast", "suggestion": meals.get("breakfast") or "Local breakfast specialities", "area": destination},
                {"meal": "Lunch", "suggestion": meals.get("lunch") or "Regional lunch specialities", "area": destination},
                {"meal": "Dinner", "suggestion": meals.get("dinner") or "Authentic dinner recipes", "area": destination}
            ]
            
            day_obj = {
                "day": day_num,
                "theme": day_data.get("theme") or "Explore " + destination,
                "base_area": destination,
                "narrative": day_data.get("narrative") or f"Explore local landmarks and sights in {destination}.",
                "daily_budget": day_data.get("daily_budget") or "₹4,000 per person",
                "morning": [morning_slot],
                "afternoon": [afternoon_slot],
                "evening": [evening_slot],
                "food_recommendations": food_recs,
                "pacing": day_data.get("pacing") or "Moderate pacing"
            }
            days_list.append(day_obj)
            
    elif "days" in llm_out:
        for idx, day_data in enumerate(llm_out["days"]):
            day_num = idx + 1
            
            # Extract and process slots
            for slot in ["morning", "afternoon", "evening"]:
                slots_list = day_data.get(slot, [])
                if not isinstance(slots_list, list):
                    slots_list = [slots_list] if slots_list else []
                fixed_slots = []
                for item in slots_list:
                    if not isinstance(item, dict):
                        item = {"location": str(item)}
                    loc = process_location(item.get("location", ""))
                    fixed_item = {
                        "time": item.get("time") or ("09:00" if slot == "morning" else "13:30" if slot == "afternoon" else "18:00"),
                        "activity": item.get("activity") or f"Visit {loc}",
                        "location": loc,
                        "duration": item.get("duration") or "2 hours",
                        "transport": item.get("transport") or "Local transport",
                        "notes": item.get("notes") or "Expert local advice",
                        "expected_cost": item.get("expected_cost") or item.get("cost") or "Free"
                    }
                    fixed_slots.append(fixed_item)
                day_data[slot] = fixed_slots
            
            day_data["day"] = day_num
            day_data["base_area"] = destination
            days_list.append(day_data)
        
    return {
        "destination": llm_out.get("destination", destination),
        "days": days_list,
        "planning_notes": llm_out.get("planning_notes") or ["Itinerary dynamically generated by LLM."]
    }
        
    return {
        "destination": llm_out.get("destination", destination),
        "days": days_list,
        "planning_notes": llm_out.get("planning_notes") or ["Itinerary dynamically generated by LLM."]
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
    destination_guide: str = "",
) -> dict[str, Any]:
    from monitoring.logger import logger
    destination = normalize_destination(structured_query.get("destination", ""))
    logger.info("[Planner Agent] Entering agent")
    logger.info(f"[Planner Agent] Destination received: {destination}")
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
        "transport_style": "local transport"
    }
    
    planner_input = build_planner_input(structured_query, behavior_profile, allowed_places)
    
    # Check if we are in Mock/Test mode
    from agents.llm import get_llm
    is_mock = False
    try:
        provider, _ = get_llm()
        if provider == "Mock":
            is_mock = True
    except Exception:
        pass

    # Make LLM Call
    prompt = f"""
You are an elite travel consultant.
Generate a realistic itinerary for destination: {destination}
Optimize:
* travel time
* geography
* budget
* pacing
* user interests
* weather
* operating hours

Trip details:
- Destination: {destination}
- Number of days: {structured_query.get('days', 3)}
- Total target budget: {structured_query.get('budget', 20000)} INR
- Travelers: 1
- Interests: {structured_query.get('interests', [])}
- Avoid: {structured_query.get('avoid', [])}

Traveler Profile / Preferences:
- Pace: {behavior_profile.get('pace', 'medium')}
- Food style: {behavior_profile.get('food_style', 'mixed')}
- Budget style: {behavior_profile.get('budget_style', 'balanced')}
- Crowd preference: {behavior_profile.get('crowd_preference', 'neutral')}
- Transport preference: {behavior_profile.get('transport_style', 'local transport')}

Destination Guide & Context (use this dynamic insights to shape attractions and schedules):
{destination_guide}

Supporting RAG context (recommended places for this destination to guide your suggestions, but you must dynamically decide the best activities, order, and times to maximize traveler experience):
{json.dumps(allowed_places[:15], indent=2)}

Ensure every single attraction comes from LLM reasoning, geographical proximity, and logical sequencing.
Generate a destination-specific itinerary.
Requirements:
* Use real attractions.
* Use real neighborhoods.
* Use real restaurants/food districts.
* Use real cultural experiences.
* No repeated POIs.
* No repeated attractions.
* No template landmarks.
* Every day must be unique.
* If itinerary spans N days, generate enough unique attractions to fill all N days.

Return structured JSON exactly matching the requested schema.
"""
    try:
        from monitoring.logger import logger
        res = invoke_json(SYSTEM_PROMPT, prompt, fallback=None, temperature=0.2)
        if not res:
            raise Exception("Empty response received from LLM")
        if isinstance(res, dict) and (any(k.startswith("day_") for k in res.keys()) or "days" in res):
            itinerary = map_llm_to_standard_itinerary(res, destination, allowed_places)
            logger.info(f"[Planner Agent] Destination returned: {destination}")
            logger.info("[Planner Agent] Leaving agent")
            return itinerary
        raise Exception("LLM returned invalid JSON schema structure")
    except Exception as e:
        from monitoring.logger import logger
        from agents.constants import valid_destinations
        # Raise error directly if destination is unknown to prevent fake templates
        if destination not in valid_destinations():
            logger.error(f"[Planner Agent] LLM generation failed for unknown destination '{destination}': {e}. Raising exception.")
            raise Exception(f"Failed to plan itinerary for '{destination}' due to AI service rate limits. Please try again. Details: {e}")
            
        if "No AI provider configured" in str(e) or "LLM unavailable" in str(e):
            raise e
        logger.error(f"Planner LLM generation failed: {e}. Falling back to rule-based scheduler.")

    fallback = assemble_schedule(planner_input)
    logger.info(f"[Planner Agent] Destination returned: {destination}")
    logger.info("[Planner Agent] Leaving agent")
    return fallback
