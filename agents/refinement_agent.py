"""Human-in-the-Loop Refinement Agent - structured partial itinerary mutation."""
from __future__ import annotations

import copy
import re
from typing import Any

from agents.constants import normalize_destination
from agents.rag_agent import retrieve_place_entities

SYSTEM_PROMPT = """You are a smart travel itinerary editor. You receive an existing structured itinerary and user feedback.

Your job:
1. Parse the user's modification request carefully
2. Make SURGICAL changes - only modify what the user asked
3. Re-balance the itinerary if needed (timing, pacing)
4. Insert new places in the correct day/time slot
5. Remove requested places cleanly
6. Adjust pacing if user says "too hectic" or "more relaxed"
7. Return the COMPLETE updated plan as valid JSON
8. Preserve unaffected days as much as possible
9. Destination isolation is mandatory: only use attraction names from the current destination RAG list.
10. Behavioral/session feedback changes style or selects among current-destination places; it must not inject old or other-destination places.

Return ONLY valid JSON:
{
  "modification_intent": {"add": [string], "remove": [string], "avoid": [string], "pace": string or null, "food": [string], "shopping": boolean},
  "updated_itinerary": {same itinerary schema as input},
  "changed_days": [integer],
  "refinement_notes": [string]
}"""


def extract_modification_intent(user_feedback: str) -> dict:
    lower = user_feedback.lower()
    add = []
    remove = []
    avoid = []
    for pattern, bucket in [
        (r"add ([^.]+)", add),
        (r"include ([^.]+)", add),
        (r"remove ([^.]+)", remove),
        (r"skip ([^.]+)", remove),
        (r"avoid ([^.]+)", avoid),
    ]:
        match = re.search(pattern, lower)
        if match:
            bucket.extend([v.strip() for v in re.split(r",| and | also ", match.group(1)) if v.strip()])
    return {
        "add": add,
        "remove": remove,
        "avoid": avoid,
        "pace": "slow" if any(v in lower for v in ["relaxed", "less hectic", "slow"]) else "fast" if "more places" in lower else None,
        "food": [v for v in ["cafes", "local food", "street food", "seafood"] if v in lower],
        "shopping": any(v in lower for v in ["shopping", "market", "bazaar"]),
    }


def _fallback_refine(current_plan: dict[str, Any], user_feedback: str, structured_query: dict) -> dict[str, Any]:
    plan = copy.deepcopy(current_plan)
    intent = extract_modification_intent(user_feedback)
    changed_days: set[int] = set()
    destination = normalize_destination(structured_query.get("destination", plan.get("destination", "")))
    avoid_terms = [*intent["remove"], *intent["avoid"], *(structured_query.get("avoid") or [])]
    for day in plan.get("days", []):
        removed = False
        for slot in ["morning", "afternoon", "evening"]:
            kept = []
            for item in day.get(slot, []) or []:
                haystack = f"{item.get('activity', '')} {item.get('location', '')}".lower()
                if any(term and term.lower() in haystack for term in avoid_terms):
                    removed = True
                    continue
                kept.append(item)
            day[slot] = kept
        if removed:
            changed_days.add(day.get("day", 1))
    docs = retrieve_place_entities(destination, structured_query.get("interests", []) + intent["add"] + intent["food"], n=20)
    allowed_places = {doc["name"] for doc in docs}
    additions = intent["add"] + (["local market"] if intent["shopping"] else []) + intent["food"]
    for addition in additions:
        if not plan.get("days"):
            break
        target = next((d for d in docs if addition.lower() in f"{d.get('name', '')} {d.get('destination', '')} {' '.join(d.get('tags', []))}".lower()), None)
        if not target:
            target = next((d for d in docs if "cafe" in " ".join(d.get("tags", [])).lower()), None) if "cafe" in addition.lower() else None
        if not target:
            target = next((d for d in docs if d.get("category") in ("shopping", "cafe/culture", "food")), None) if intent["shopping"] else None
        if not target and docs:
            target = docs[0]
        if not target:
            continue
        place = target["name"]
        location = target.get("destination", destination)
        category = target.get("category", "experience")
        if place not in allowed_places:
            continue
        day = plan["days"][0]
        item = {
            "time": "16:30" if intent["shopping"] or "cafe" in addition.lower() else "13:30",
            "activity": f"Add {place} to the route",
            "location": place,
            "duration": "1.5-2 hours",
            "transport": "Local cab/auto; keep transfer time buffered",
            "notes": f"Selected as a {category} match from the structured {destination} allowed place list.",
        }
        slot = "evening" if intent["shopping"] or "cafe" in addition.lower() else "afternoon"
        day.setdefault(slot, []).append(item)
        changed_days.add(day.get("day", 1))
    if intent["pace"] == "slow":
        for day in plan.get("days", []):
            day["pacing"] = "Relaxed pacing with fewer major stops and longer rest buffers."
            for slot in ["morning", "afternoon", "evening"]:
                if len(day.get(slot, [])) > 1:
                    day[slot] = day[slot][:1]
                    changed_days.add(day.get("day", 1))
    plan["planning_notes"] = []
    return {
        "modification_intent": intent,
        "updated_itinerary": plan,
        "changed_days": sorted(changed_days) or [1],
        "refinement_notes": ["Applied structural itinerary mutation and rebalanced affected day slots."],
    }


def run_refinement_agent(current_plan: dict[str, Any], user_feedback: str, structured_query: dict) -> dict[str, Any]:
    return _fallback_refine(current_plan, user_feedback, structured_query)
