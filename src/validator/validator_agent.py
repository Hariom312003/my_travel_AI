"""Validator Agent - destination grounding, hallucination checks, and itinerary repair."""
from __future__ import annotations

import copy
import re
from typing import Any

from agents.constants import known_place_names, normalize_destination, valid_destinations


SLOTS = ["morning", "afternoon", "evening"]


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _contains_any(text: str, names: set[str]) -> list[str]:
    lower = text.lower()
    return [name for name in names if name and name.lower() in lower]


def _replacement_item(doc: dict, slot: str, day_number: int, relaxed: bool) -> dict:
    time_by_slot = {"morning": "09:00", "afternoon": "13:30", "evening": "18:00"}
    duration = "2 hours" if relaxed else "2-2.5 hours"
    if slot == "evening":
        duration = "1.5-2 hours"
    place = doc.get("name", "")
    category = doc.get("category", "experience")
    return {
        "time": time_by_slot.get(slot, "10:00"),
        "activity": f"{place} — {category}",
        "location": place,
        "duration": duration,
        "transport": "Local cab/auto with transfer buffer.",
        "notes": "Validated destination activity.",
    }


def _pick_replacement(
    docs: list[dict],
    used: set[str],
    preferred_category: str | None = None,
) -> dict:
    if preferred_category:
        for doc in docs:
            name = doc.get("name")
            if name and name.lower() not in used and doc.get("category") == preferred_category:
                return doc
    for doc in docs:
        name = doc.get("name")
        if name and name.lower() not in used:
            return doc
            
    # Self-healing uniqueness: generate a unique sub-area of the base attraction
    base_doc = docs[0] if docs else {"name": "Scenic Landmark", "category": "scenic"}
    name = base_doc.get("name", "Scenic Landmark")
    i = 2
    while f"{name} (Area {i})".lower() in used:
        i += 1
    new_doc = dict(base_doc)
    new_doc["name"] = f"{name} (Area {i})"
    return new_doc


def _sanitize_food(food: dict, destination: str, off_destination_names: set[str]) -> dict:
    clean = dict(food)
    text = " ".join(str(clean.get(key, "")) for key in ["suggestion", "area"])
    if _contains_any(text, off_destination_names):
        meal = clean.get("meal", "Meal")
        clean["suggestion"] = f"{meal} at a local {destination} eatery matching the user's food preference"
        clean["area"] = destination
    return clean


def sanitize_user_plan(plan: dict[str, Any], destination: str, allowed: set[str]) -> dict[str, Any]:
    if not isinstance(plan, dict):
        plan = {"destination": destination, "days": [], "planning_notes": []}
    clean = copy.deepcopy(plan)
    clean["destination"] = destination
    for day in clean.get("days", []) or []:
        day["base_area"] = destination
        day.pop("planning_notes", None)
        for slot in SLOTS:
            day[slot] = [
                {
                    "time": item.get("time", ""),
                    "activity": item.get("activity", item.get("location", "")),
                    "location": item.get("location", ""),
                    "duration": item.get("duration", ""),
                    "transport": item.get("transport", ""),
                    "notes": item.get("notes", ""),
                }
                for item in day.get(slot, []) or []
                if not allowed or item.get("location") in allowed
            ]
    clean["planning_notes"] = []
    return clean


def clean_itinerary(plan: dict[str, Any], destination: str) -> dict[str, Any]:
    """Final guardrail before API/UI rendering.

    Removes every activity and food reference that is not valid for the locked
    destination. This function is intentionally independent of the planner.
    """
    destination = normalize_destination(destination or plan.get("destination", ""))
    valid_map = valid_destinations()
    allowed = set(valid_map.get(destination, []))
    off_destination = known_place_names(exclude_destination=destination)
    cleaned = sanitize_user_plan(plan, destination, allowed)
    for day in cleaned.get("days", []) or []:
        for slot in SLOTS:
            day[slot] = [
                item for item in day.get(slot, []) or []
                if (not allowed or item.get("location") in allowed)
                and not _contains_any(" ".join(str(item.get(k, "")) for k in ["activity", "location", "notes", "transport"]), off_destination)
            ]
        safe_food = []
        for food in day.get("food_recommendations", []) or []:
            food_text = " ".join(str(food.get(k, "")) for k in ["meal", "suggestion", "area"])
            if _contains_any(food_text, off_destination):
                continue
            food["area"] = destination
            safe_food.append(food)
        day["food_recommendations"] = safe_food
    cleaned["planning_notes"] = []
    return cleaned


def _docs_from_constants(destination: str) -> list[dict[str, Any]]:
    categories = ["scenic", "culture", "shopping", "food", "adventure"]
    ideal_times = ["morning", "afternoon", "evening"]
    return [
        {
            "name": place,
            "destination": destination,
            "category": categories[idx % len(categories)],
            "tags": [categories[idx % len(categories)]],
            "crowd_level": "normal",
            "ideal_time": ideal_times[idx % len(ideal_times)],
            "duration_hours": 2,
        }
        for idx, place in enumerate(valid_destinations().get(destination, []))
    ]


def validate_itinerary(
    plan: dict[str, Any],
    structured_query: dict,
    rag_documents: list[dict] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a repaired plan plus a validation report.

    Enforces:
    1. No duplicate attractions (using global tracking).
    2. No template landmarks (like Scenic Riverside Promenade or [City] Central Gardens).
    3. Correct day count matching requested duration.
    """
    from monitoring.logger import logger
    if not isinstance(plan, dict):
        plan = {"destination": structured_query.get("destination", ""), "days": [], "planning_notes": []}
    destination = normalize_destination(structured_query.get("destination") or plan.get("destination", ""))
    logger.info("[Validator Agent] Entering agent")
    logger.info(f"[Validator Agent] Destination received: {destination}")
    docs = rag_documents or _docs_from_constants(destination)
    docs = [doc for doc in docs if doc.get("destination", "").lower() == destination.lower()]
    allowed = {doc.get("name", "") for doc in docs if doc.get("name")}
    allowed_norm = {_norm(place) for place in allowed}
    off_destination_names = known_place_names(exclude_destination=destination)
    relaxed = structured_query.get("travel_pace") == "slow" or structured_query.get("travel_style") == "relaxed"

    repaired = copy.deepcopy(plan)
    repaired["destination"] = destination
    invalid_places: list[dict] = []
    repaired_days: set[int] = set()
    duplicate_activities: list[dict] = []
    category_sequence: list[str] = []
    
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

    global_used_locations: set[str] = set()
    
    # 1. Day count correction validation
    days_needed = int(structured_query.get("days", 3))
    current_days = repaired.get("days", []) or []
    if len(current_days) != days_needed:
        if len(current_days) > days_needed:
            repaired["days"] = current_days[:days_needed]
            repaired_days.add(days_needed)
        elif len(current_days) < days_needed:
            from planner.planner_agent import assemble_schedule
            # Track used locations in existing days first
            for day in current_days:
                for slot in SLOTS:
                    for item in day.get(slot, []) or []:
                        loc = item.get("location", "")
                        if loc:
                            global_used_locations.add(loc.lower())
            
            missing_days = days_needed - len(current_days)
            planner_input = {
                "destination": destination,
                "days": missing_days,
                "allowed_places": docs,
                "behavior_profile": {},
                "avoid": list(global_used_locations)
            }
            extra_plan = assemble_schedule(planner_input)
            for idx, day_obj in enumerate(extra_plan.get("days", [])):
                day_obj["day"] = len(current_days) + 1 + idx
                current_days.append(day_obj)
            repaired["days"] = current_days
            repaired_days.add(days_needed)

    global_used_locations.clear()
    
    for day in repaired.get("days", []) or []:
        day_number = int(day.get("day", len(repaired_days) + 1))
        day_categories: list[str] = []
        used_locations: set[str] = set()
        for slot in SLOTS:
            fixed_items = []
            for item in day.get(slot, []) or []:
                location = item.get("location", "")
                full_text = " ".join(
                    str(item.get(key, "")) for key in ["activity", "location", "transport", "notes"]
                )
                off_dest_hits = _contains_any(full_text, off_destination_names)
                
                # Grounding checks
                invalid_location = False
                if docs:
                    invalid_location = _norm(location) not in allowed_norm
                    
                # Duplication checks
                duplicate = location.lower() in global_used_locations
                
                # Forbidden template checks
                is_template = False
                for pattern in FORBIDDEN_TEMPLATES:
                    if re.search(pattern, location.lower()):
                        is_template = True
                        break
                        
                if invalid_location or off_dest_hits or duplicate or is_template:
                    reason = []
                    if invalid_location:
                        reason.append("not_in_destination_rag")
                    if off_dest_hits:
                        reason.append("cross_destination_leakage")
                    if duplicate:
                        reason.append("duplicate_activity")
                        duplicate_activities.append({"day": day_number, "slot": slot, "location": location})
                    if is_template:
                        reason.append("template_landmark_fabrication")
                        
                    # Pick unique replacement
                    if docs:
                        replacement_doc = _pick_replacement(docs, global_used_locations)
                        replacement = _replacement_item(replacement_doc, slot, day_number, relaxed)
                        replacement_name = replacement_doc.get("name", "")
                        rep_category = replacement_doc.get("category", "experience")
                    else:
                        from agents.demo_data import GENERIC_CLEAN_ATTRACTIONS
                        replacement_name = "Clean Landmark"
                        for name in GENERIC_CLEAN_ATTRACTIONS:
                            if name.lower() not in global_used_locations:
                                replacement_name = name
                                break
                        replacement = {
                            "time": "09:00" if slot == "morning" else "13:30" if slot == "afternoon" else "18:00",
                            "activity": f"Explore {replacement_name}",
                            "location": replacement_name,
                            "duration": "2 hours",
                            "transport": "Local transport",
                            "notes": "Scenic attraction.",
                        }
                        rep_category = "scenic"
                        
                    fixed_items.append(replacement)
                    used_locations.add(replacement_name)
                    global_used_locations.add(replacement_name.lower())
                    repaired_days.add(day_number)
                    invalid_places.append({
                        "day": day_number,
                        "slot": slot,
                        "value": location or full_text[:80],
                        "reason": ",".join(reason),
                        "replacement": replacement_name,
                    })
                    day_categories.append(rep_category)
                    continue
                fixed_items.append(item)
                used_locations.add(location)
                global_used_locations.add(location.lower())
                doc = next((doc for doc in docs if _norm(doc.get("name", "")) == _norm(location)), None)
                if doc:
                    day_categories.append(doc.get("category", "experience"))
            day[slot] = fixed_items

        day["food_recommendations"] = [
            _sanitize_food(food, destination, off_destination_names)
            for food in day.get("food_recommendations", []) or []
        ]
        if relaxed and "buffer" not in day.get("pacing", "").lower():
            day["pacing"] = "Relaxed pacing with meal windows, transfer buffers, and rest time."
            repaired_days.add(day_number)
        if day_categories:
            category_sequence.extend(day_categories)

    diversity_warnings = []
    for idx in range(0, max(len(category_sequence) - 2, 0)):
        window = category_sequence[idx : idx + 3]
        if len(set(window)) == 1:
            diversity_warnings.append(f"Repeated {window[0]} activities in adjacent slots; validator recommends mixing categories.")
            break
    if diversity_warnings:
        # Repair simple one-note schedules by replacing the first repeated evening with a different category.
        used = set(global_used_locations)
        changed_days_allowed = structured_query.get("_changed_days", [])
        for day in repaired.get("days", []) or []:
            day_number = int(day.get("day", 1))
            if changed_days_allowed and day_number not in changed_days_allowed:
                continue
            evening = day.get("evening", [])
            if not evening:
                continue
            if docs:
                replacement_doc = _pick_replacement(docs, used, preferred_category="culture")
                if replacement_doc.get("name", "").lower() in used:
                    replacement_doc = _pick_replacement(docs, used)
                evening[0] = _replacement_item(replacement_doc, "evening", day_number, relaxed)
            else:
                from agents.demo_data import GENERIC_CLEAN_ATTRACTIONS
                rep_name = "Unique Activity"
                for name in GENERIC_CLEAN_ATTRACTIONS:
                    if name.lower() not in used:
                        rep_name = name
                        break
                evening[0] = {
                    "time": "18:00",
                    "activity": f"Visit {rep_name}",
                    "location": rep_name,
                    "duration": "2 hours",
                    "transport": "Local transport",
                    "notes": "Cultural activity.",
                }
            repaired_days.add(day_number)
            break

    repaired = sanitize_user_plan(repaired, destination, allowed if docs else set())

    report = {
        "is_valid": not invalid_places and not diversity_warnings,
        "destination": destination,
        "allowed_places": sorted(allowed) if docs else [],
        "invalid_places": invalid_places,
        "repaired_days": sorted(repaired_days),
        "duplicate_activities": duplicate_activities,
        "diversity_warnings": diversity_warnings,
    }
    logger.info(f"[Validator Agent] Destination returned: {destination}")
    logger.info("[Validator Agent] Leaving agent")
    return repaired, report
