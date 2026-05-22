"""Constraint-based itinerary scheduler.

The planner does not ask an LLM to invent travel content. It selects, arranges,
and schedules only destination-locked structured place entities.
"""
from __future__ import annotations

from typing import Any

from agents.constants import normalize_destination
from agents.rag_agent import retrieve_place_entities

SYSTEM_PROMPT = "Internal only: deterministic scheduler. No creative generation."


def build_planner_input(structured_query: dict, behavior_profile: dict, allowed_places: list[dict]) -> dict:
    destination = normalize_destination(structured_query.get("destination", ""))
    clean_places = [
        {
            "name": place["name"],
            "destination": place["destination"],
            "category": place["category"],
            "tags": place.get("tags", []),
            "crowd_level": place.get("crowd_level", "normal"),
            "ideal_time": place.get("ideal_time", "morning"),
            "duration_hours": place.get("duration_hours", 2),
        }
        for place in allowed_places
        if place.get("destination", "").lower() == destination.lower()
    ]
    return {
        "destination": destination,
        "days": int(structured_query.get("days", 3)),
        "budget": int(structured_query.get("budget", 20000)),
        "cards": structured_query.get("cards", []),
        "avoid": structured_query.get("avoid", []),
        "behavior_profile": behavior_profile,
        "allowed_places": clean_places,
    }


def _slot(activity: str, location: str, duration: str, transport: str, notes: str, time: str) -> dict:
    return {
        "time": time,
        "activity": activity,
        "location": location,
        "duration": duration,
        "transport": transport,
        "notes": notes,
    }


def _duration_text(hours: float | int | str) -> str:
    try:
        value = float(hours)
    except Exception:
        return "2 hours"
    return f"{int(value)} hours" if value.is_integer() else f"{value:g} hours"


def _food_line(destination: str, place: str, food_style: str, meal: str) -> str:
    cuisine = {
        "Manali": "local Himachali food",
        "Kullu": "local Himachali food",
        "Goa": "local Goan food",
        "Jaipur": "local Rajasthani food",
    }.get(destination, "local food")
    if food_style == "cafes":
        return f"{meal} at a local cafe near {place}"
    return f"{meal} with {cuisine} near {place}"


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


def _select_for_slot(pool: list[dict], used_today: set[str], used_trip: set[str], slot: str, offset: int) -> dict:
    preferred = {
        "morning": {"culture", "heritage", "scenic", "nature"},
        "afternoon": {"adventure", "nature", "beach", "scenic"},
        "evening": {"shopping", "food", "cafe/culture", "beach"},
    }[slot]
    candidates = [place for place in pool if place["name"] not in used_today]
    candidates = [place for place in candidates if place["name"] not in used_trip] or candidates or pool
    preferred_candidates = [
        place for place in candidates
        if place.get("ideal_time") == slot or place.get("category") in preferred
    ]
    choices = preferred_candidates or candidates
    return choices[offset % len(choices)]


def assemble_schedule(planner_input: dict) -> dict[str, Any]:
    destination = planner_input.get("destination", "Goa")
    days = int(planner_input.get("days", 3))
    profile = planner_input.get("behavior_profile", {})
    avoid = " ".join(planner_input.get("avoid", [])).lower()
    pool = [p for p in planner_input.get("allowed_places", []) if p["name"].lower() not in avoid]
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
    slow = profile.get("pace") == "slow"
    plan_days = []
    used_trip: set[str] = set()
    for day in range(1, days + 1):
        used_today: set[str] = set()
        morning_place = _select_for_slot(pool, used_today, used_trip, "morning", day - 1)
        used_today.add(morning_place["name"])
        afternoon_place = _select_for_slot(pool, used_today, used_trip, "afternoon", day)
        used_today.add(afternoon_place["name"])
        evening_place = _select_for_slot(pool, used_today, used_trip, "evening", day + 1)
        used_today.add(evening_place["name"])
        used_trip.update(used_today)
        pacing = (
            "Relaxed pacing with meal windows, transfer buffers, and rest time."
            if slow else
            "Moderate pacing with realistic transfers and no backtracking."
        )
        plan_days.append({
            "day": day,
            "theme": f"{morning_place.get('category', 'Local').title()} + {evening_place.get('category', 'Local').title()}",
            "base_area": destination,
            "morning": [_slot(
                _activity_label(morning_place, "morning"),
                morning_place["name"],
                _duration_text(morning_place.get("duration_hours", 2)),
                "Local cab/auto; start after breakfast",
                "Keep one transfer buffer before lunch.",
                "09:00",
            )],
            "afternoon": [_slot(
                _activity_label(afternoon_place, "afternoon"),
                afternoon_place["name"],
                _duration_text(afternoon_place.get("duration_hours", 2)),
                "Short local transfer after lunch",
                "Keep the afternoon focused on one main area.",
                "13:30",
            )],
            "evening": [_slot(
                _activity_label(evening_place, "evening"),
                evening_place["name"],
                _duration_text(min(float(evening_place.get("duration_hours", 2)), 2)),
                "Walk/auto depending on hotel area",
                "Keep this light and close with dinner nearby.",
                "18:00",
            )],
            "food_recommendations": [
                {"meal": "Breakfast", "suggestion": f"Simple local breakfast in {destination}", "area": destination},
                {"meal": "Lunch", "suggestion": _food_line(destination, afternoon_place["name"], profile.get("food_style", "local"), "Lunch"), "area": destination},
                {"meal": "Dinner", "suggestion": _food_line(destination, evening_place["name"], profile.get("food_style", "local"), "Dinner"), "area": destination},
            ],
            "pacing": pacing,
        })
    return {
        "destination": destination,
        "days": plan_days,
        "planning_notes": [
            "Internal: schedule assembled from structured behavior profile and destination-locked place pool.",
        ],
    }


def itinerary_to_text(plan: dict[str, Any]) -> str:
    lines: list[str] = []
    for day in plan.get("days", []):
        lines.append(f"Day {day.get('day')} — {day.get('theme', 'Balanced day')}")
        for slot_name in ["morning", "afternoon", "evening"]:
            lines.append(f"{slot_name.title()}:")
            for item in day.get(slot_name, []) or []:
                lines.append(f"- {item.get('activity', item.get('location', ''))}")
                lines.append(f"- {item.get('duration', '')}")
                if item.get("transport"):
                    lines.append(f"- {item.get('transport')}")
        if day.get("food_recommendations"):
            lines.append("Food:")
            for food in day["food_recommendations"]:
                lines.append(f"- {food.get('meal')}: {food.get('suggestion')}")
        lines.append(f"Pacing: {day.get('pacing', '')}")
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
    allowed_places = allowed_places or retrieve_place_entities(destination, interests, n=12)
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
