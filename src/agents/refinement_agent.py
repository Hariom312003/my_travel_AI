"""Human-in-the-Loop Refinement Agent - structured partial itinerary mutation."""
from __future__ import annotations

import json
import copy
import re
from typing import Any

from agents.constants import normalize_destination
from rag.rag_agent import retrieve_place_entities

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


def detect_explicit_category(feedback: str) -> str | None:
    fb_lower = feedback.lower()
    if "adventure" in fb_lower:
        return "adventure"
    if any(k in fb_lower for k in ["museum", "temple", "culture", "cultural", "heritage", "historic", "historical"]):
        return "culture"
    if "cafe" in fb_lower:
        return "cafe/culture"
    if "nightlife" in fb_lower or "night life" in fb_lower:
        return "nightlife"
    if "beach" in fb_lower or "beaches" in fb_lower:
        return "beach"
    if "nature" in fb_lower:
        return "nature"
    if any(k in fb_lower for k in ["scenic", "view", "scenery"]):
        return "scenic"
    if any(k in fb_lower for k in ["shopping", "market", "bazaar"]):
        return "shopping"
    if any(k in fb_lower for k in ["food", "restaurant", "dining"]):
        return "food"
    return None


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
    refinement_notes = []
    changed_days: set[int] = set()
    destination = normalize_destination(structured_query.get("destination", plan.get("destination", "")))
    
    # 1. Swap Logic
    # Example: "Swap Day 1 afternoon with Day 2 evening"
    swap_match = re.search(
        r"swap\s*day\s*(\d+)\s*([a-zA-Z]+)\s*(?:with|and)\s*day\s*(\d+)\s*([a-zA-Z]+)", 
        user_feedback.lower()
    )
    if swap_match:
        day_a = int(swap_match.group(1))
        slot_a_raw = swap_match.group(2).strip().lower()
        day_b = int(swap_match.group(3))
        slot_b_raw = swap_match.group(4).strip().lower()
        
        slot_map = {"morning": "morning", "afternoon": "afternoon", "evening": "evening"}
        slot_a = slot_map.get(slot_a_raw)
        slot_b = slot_map.get(slot_b_raw)
        
        day_obj_a = next((d for d in plan.get("days", []) if int(d.get("day", 1)) == day_a), None)
        day_obj_b = next((d for d in plan.get("days", []) if int(d.get("day", 1)) == day_b), None)
        
        if day_obj_a and day_obj_b and slot_a and slot_b:
            temp = day_obj_a.get(slot_a, [])
            day_obj_a[slot_a] = day_obj_b.get(slot_b, [])
            day_obj_b[slot_b] = temp
            changed_days.add(day_a)
            changed_days.add(day_b)
            refinement_notes.append(f"Preference extraction: Swapped Day {day_a} {slot_a} with Day {day_b} {slot_b}.")
            plan["planning_notes"] = []
            
            audit_msg = f"Rule validation: Refinement parsed for days {sorted(changed_days)}. Changed days: {sorted(changed_days)}."
            refinement_notes.insert(0, audit_msg)
            
            return {
                "modification_intent": {"swap": [day_a, day_b], "slots": [slot_a, slot_b]},
                "updated_itinerary": plan,
                "changed_days": sorted(changed_days),
                "refinement_notes": refinement_notes
            }

    # 2. Category replacement logic (existing check)
    replace_match = re.search(
        r"replace day\s*(\d+)\s*with\s*([a-zA-Z\s/]+?)(?:\s*(?:activities|stops|places|spots))?$", 
        user_feedback.lower().strip()
    )
    if not replace_match:
        replace_match = re.search(
            r"replace day\s*(\d+)\s*with\s*([a-zA-Z\s/]+)", 
            user_feedback.lower()
        )
    if replace_match:
        target_day = int(replace_match.group(1))
        category_raw = replace_match.group(2).strip()
        
        target_cat = detect_explicit_category(user_feedback)
        if not target_cat:
            cat_map = {
                "cultural": "culture", "culture": "culture", "heritage": "culture", "historic": "culture", "historical": "culture",
                "scenic": "scenic", "views": "scenic", "nature": "nature", "scenery": "scenic", "beach": "beach", "beaches": "beach",
                "adventure": "adventure", "shopping": "shopping", "market": "shopping", "bazaar": "shopping",
                "food": "food", "cafes": "cafe/culture", "cafe": "cafe/culture", "nightlife": "nightlife",
                "museums": "culture", "museum": "culture", "temples": "culture", "temple": "culture"
            }
            target_cat = cat_map.get(category_raw)
        if not target_cat:
            target_cat = category_raw
            
        docs = retrieve_place_entities(destination, [target_cat], n=12)
        matching_places = [d for d in docs if d.get("category") == target_cat] or docs
        
        day = next((d for d in plan.get("days", []) if int(d.get("day", 1)) == target_day), None)
        if day:
            already_scheduled = set()
            for d in plan.get("days", []) or []:
                if int(d.get("day", 1)) != target_day:
                    for slot in ["morning", "afternoon", "evening"]:
                        for item in d.get(slot, []) or []:
                            loc = item.get("location")
                            if loc:
                                already_scheduled.add(loc.lower())
            day["morning"] = []
            day["afternoon"] = []
            day["evening"] = []
            selected = []
            for p in matching_places:
                p_name_lower = p["name"].lower()
                if p_name_lower not in already_scheduled and p["name"] not in [s["name"] for s in selected]:
                    selected.append(p)
                if len(selected) >= 3:
                    break
            if len(selected) < 3 and docs:
                for p in docs:
                    p_name_lower = p["name"].lower()
                    if p_name_lower not in already_scheduled and p["name"] not in [s["name"] for s in selected]:
                        selected.append(p)
                    if len(selected) >= 3:
                        break
            slots = ["morning", "afternoon", "evening"]
            times = {"morning": "09:00", "afternoon": "13:30", "evening": "18:00"}
            for i, slot in enumerate(slots):
                if i < len(selected):
                    place = selected[i]
                    day[slot] = [{
                        "time": times[slot],
                        "activity": f"{place['name']} — {place.get('category', 'experience').title()}",
                        "location": place["name"],
                        "duration": place.get("recommended_duration", "2 hours"),
                        "transport": place.get("transport_tips", "Local transit"),
                        "notes": f"Preference extraction: Replaced Day {target_day} with matching {target_cat} activities.",
                        "expected_cost": place.get("budget_category", "Free entry")
                    }]
            day["theme"] = f"{target_cat.title()} Spotlight"
            changed_days.add(target_day)
            refinement_notes.append(f"Preference extraction: Replaced Day {target_day} schedule with {target_cat} activities.")
            plan["planning_notes"] = []
            
            audit_msg = f"Rule validation: Refinement parsed for days {[target_day]}. Changed days: {sorted(changed_days)}."
            refinement_notes.insert(0, audit_msg)
            
            return {
                "modification_intent": {"replace_day": target_day, "category": target_cat},
                "updated_itinerary": plan,
                "changed_days": sorted(changed_days),
                "refinement_notes": refinement_notes
            }

    # 3. Standard Multi-day Refinement
    # Extract targeted days
    target_days = set()
    for match in re.finditer(r"day\s*(\d+)", user_feedback.lower()):
        target_days.add(int(match.group(1)))
    # Match patterns like "days 2 and 3"
    for match in re.finditer(r"days\s*(\d+)\s*(?:and|,|to)\s*(\d+)", user_feedback.lower()):
        target_days.add(int(match.group(1)))
        target_days.add(int(match.group(2)))
        
    intent = extract_modification_intent(user_feedback)
    avoid_terms = [*intent["remove"], *intent["avoid"], *(structured_query.get("avoid") or [])]
    
    # Check day-specific instructions: e.g. "remove X from Day 1", "add Y to Day 3"
    # Map additions: {day_num: [place_names]}
    targeted_additions = {}
    add_matches = re.finditer(r"(?:add|include)\s+([^.]+?)\s+(?:to|in)\s+day\s+(\d+)", user_feedback.lower())
    for m in add_matches:
        place_name = m.group(1).strip()
        day_num = int(m.group(2))
        targeted_additions.setdefault(day_num, []).append(place_name)
        target_days.add(day_num)
        
    # Map removals: {day_num: [place_names]}
    targeted_removals = {}
    remove_matches = re.finditer(r"(?:remove|skip|avoid)\s+([^.]+?)\s+(?:from|on)\s+day\s+(\d+)", user_feedback.lower())
    for m in remove_matches:
        place_name = m.group(1).strip()
        day_num = int(m.group(2))
        targeted_removals.setdefault(day_num, []).append(place_name)
        target_days.add(day_num)
        
    # Process removals/avoids day by day
    for day in plan.get("days", []):
        day_num = int(day.get("day", 1))
        # If specific target days are extracted, restrict mutation to those days
        if target_days and day_num not in target_days:
            continue
            
        day_removals = avoid_terms + targeted_removals.get(day_num, [])
        removed = False
        for slot in ["morning", "afternoon", "evening"]:
            kept = []
            for item in day.get(slot, []) or []:
                haystack = f"{item.get('activity', '')} {item.get('location', '')}".lower()
                if any(term and term.lower() in haystack for term in day_removals):
                    removed = True
                    refinement_notes.append(f"Decision trace: Removed {item.get('location')} from Day {day_num} slot {slot}.")
                    continue
                kept.append(item)
            day[slot] = kept
        if removed:
            changed_days.add(day_num)

    # Process additions
    docs = retrieve_place_entities(destination, structured_query.get("interests", []) + intent["add"] + intent["food"], n=20)
    allowed_places = {doc["name"].lower(): doc for doc in docs}
    
    # Process targeted additions first
    for d_num, additions_list in targeted_additions.items():
        day_obj = next((d for d in plan.get("days", []) if int(d.get("day", 1)) == d_num), None)
        if not day_obj:
            continue
        for addition in additions_list:
            target = None
            for name_lower, doc in allowed_places.items():
                if addition.lower() in name_lower or name_lower in addition.lower():
                    target = doc
                    break
            if not target and docs:
                target = docs[0]
            if not target:
                continue
            
            place = target["name"]
            category = target.get("category", "experience")
            slot = "evening" if "cafe" in addition.lower() or target.get("category") == "shopping" else "afternoon"
            
            item = {
                "time": "16:30" if slot == "evening" else "13:30",
                "activity": f"Add {place} to the route",
                "location": place,
                "duration": "1.5-2 hours",
                "transport": "Local cab/auto with buffer",
                "notes": f"Preference extraction: Selected as a {category} match.",
                "expected_cost": target.get("budget_category", "Free entry")
            }
            day_obj.setdefault(slot, []).append(item)
            changed_days.add(d_num)
            refinement_notes.append(f"Decision trace: Added {place} to Day {d_num} slot {slot}.")

    # Process general additions (without specific day tag)
    general_additions = [add for add in intent["add"] if not any(add in add_list for add_list in targeted_additions.values())]
    if intent["shopping"]:
        general_additions.append("local market")
    for food_pref in intent["food"]:
        general_additions.append(food_pref)
        
    for addition in general_additions:
        target = None
        for name_lower, doc in allowed_places.items():
            if addition.lower() in name_lower or name_lower in addition.lower():
                target = doc
                break
        if not target:
            target = next((d for d in docs if "cafe" in " ".join(d.get("tags", [])).lower()), None) if "cafe" in addition.lower() else None
        if not target and docs:
            target = docs[0]
        if not target:
            continue
            
        place = target["name"]
        category = target.get("category", "experience")
        
        if target_days:
            target_day_num = sorted(target_days)[0]
        else:
            target_day_num = 1
            
        day_obj = next((d for d in plan.get("days", []) if int(d.get("day", 1)) == target_day_num), None)
        if not day_obj:
            continue
            
        slot = "evening" if "cafe" in addition.lower() or category == "shopping" else "afternoon"
        item = {
            "time": "16:30" if slot == "evening" else "13:30",
            "activity": f"Add {place} to the route",
            "location": place,
            "duration": "1.5-2 hours",
            "transport": "Local cab/auto with buffer",
            "notes": f"Preference extraction: Selected as a {category} match.",
            "expected_cost": target.get("budget_category", "Free entry")
        }
        day_obj.setdefault(slot, []).append(item)
        changed_days.add(target_day_num)
        refinement_notes.append(f"Decision trace: Added {place} to Day {target_day_num} slot {slot}.")

    # Process pacing updates
    if intent["pace"] == "slow":
        for day in plan.get("days", []):
            day_num = int(day.get("day", 1))
            if target_days and day_num not in target_days:
                continue
            day["pacing"] = "Relaxed pacing with fewer major stops and longer rest buffers."
            for slot in ["morning", "afternoon", "evening"]:
                if len(day.get(slot, [])) > 1:
                    day[slot] = day[slot][:1]
                    changed_days.add(day_num)
                    refinement_notes.append(f"Decision trace: Reduced slots to single activity for Day {day_num} pacing.")

    plan["planning_notes"] = []
    
    # Audit log entry for refinement notes
    audit_msg = f"Rule validation: Refinement parsed for days {sorted(target_days or {1})}. Changed days: {sorted(changed_days or {1})}."
    refinement_notes.insert(0, audit_msg)
    
    return {
        "modification_intent": intent,
        "updated_itinerary": plan,
        "changed_days": sorted(changed_days) or sorted(target_days or {1}),
        "refinement_notes": refinement_notes,
    }


def run_refinement_agent(current_plan: dict[str, Any], user_feedback: str, structured_query: dict) -> dict[str, Any]:
    from monitoring.logger import logger
    import copy
    destination = structured_query.get("destination", "")
    logger.info("[Refinement Agent] Entering agent")
    logger.info(f"[Refinement Agent] Destination received: {destination}")
    
    # Safely detect explicit category from user feedback
    explicit_cat = detect_explicit_category(user_feedback)
    
    # If the user explicitly specifies a category, override interests in structured_query
    # to avoid falling back to previous preferences
    modified_query = copy.deepcopy(structured_query)
    if explicit_cat:
        modified_query["interests"] = [explicit_cat]
        print(f"DEBUG: Explicit category '{explicit_cat}' detected. Overriding query interests to avoid previous preferences.", flush=True)
    
    fallback = _fallback_refine(current_plan, user_feedback, modified_query)
    
    result = None
    planner_prompt = "N/A (Fallback Used)"
    planner_output = "N/A"
    
    # Priority 2: LLM-powered refinement with fallback
    destination = modified_query.get("destination", "")
    interests = modified_query.get("interests", [])
    allowed = retrieve_place_entities(destination, interests, n=20)
    
    prompt = f"""
Current Plan:
{json.dumps(current_plan, indent=2)}

User Feedback:
{user_feedback}

Structured Query Context:
{json.dumps(modified_query, indent=2)}

Allowed Places:
{json.dumps(allowed, indent=2)}
"""
    planner_prompt = prompt
    try:
        from agents.common import invoke_json
        res_llm = invoke_json(SYSTEM_PROMPT, prompt, fallback=None, temperature=0.1)
        if isinstance(res_llm, dict) and "updated_itinerary" in res_llm:
            upd = res_llm["updated_itinerary"]
            if isinstance(upd, dict) and "days" in upd:
                if "refinement_notes" not in res_llm:
                    res_llm["refinement_notes"] = []
                res_llm["refinement_notes"].append("LLM-powered refinement applied successfully.")
                result = res_llm
                planner_output = json.dumps(res_llm, indent=2)
    except Exception as e:
        print(f"DEBUG: LLM refinement failed: {e}", flush=True)
        
    if not result:
        result = fallback
        
    # After obtaining result (either from LLM or fallback), prepare detailed pipeline audit trail logging
    changed_days = result.get("changed_days", [])
    all_days = [int(d.get("day", 1)) for d in current_plan.get("days", [])]
    locked_days = [d for d in all_days if d not in changed_days]
    
    intent = result.get("modification_intent", {})
    detected_cat = explicit_cat or intent.get("category", "N/A")
    
    final_itinerary = result.get("updated_itinerary", {})
    final_days_summary = []
    for day in final_itinerary.get("days", []):
        day_num = day.get("day")
        places = []
        for slot in ["morning", "afternoon", "evening"]:
            for item in day.get(slot, []):
                places.append(f"{item.get('location')} ({slot})")
        final_days_summary.append(f"  Day {day_num}: {', '.join(places)}")
        
    print("\n" + "="*50, flush=True)
    print("REFINEMENT PIPELINE AUDIT TRAIL:", flush=True)
    print(f"Input:\n{user_feedback}", flush=True)
    print("↓", flush=True)
    print(f"Parsed intent:\n{json.dumps(intent, indent=2)}", flush=True)
    print("↓", flush=True)
    print(f"Detected category:\n{detected_cat}", flush=True)
    print("↓", flush=True)
    print(f"Locked days:\n{locked_days}", flush=True)
    print("↓", flush=True)
    print(f"Mutation request:\nReplace Day {changed_days} with category {detected_cat}", flush=True)
    print("↓", flush=True)
    print(f"Planner prompt:\n{planner_prompt}", flush=True)
    print("↓", flush=True)
    print(f"Planner output:\n{planner_output if result != fallback else 'N/A (Fallback Used)'}", flush=True)
    print("↓", flush=True)
    print("Final itinerary:\n" + "\n".join(final_days_summary), flush=True)
    print("="*50 + "\n", flush=True)
    
    logger.info(f"[Refinement Agent] Destination returned: {destination}")
    logger.info("[Refinement Agent] Leaving agent")
    return result
