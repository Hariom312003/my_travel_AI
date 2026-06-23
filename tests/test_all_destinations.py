#!/usr/bin/env python3
"""Verification suite to test all 100 destinations on the Travel AI App.

Generates a 3-day itinerary for each place and validates:
1. The destination is extracted correctly.
2. The day count is exactly 3.
3. There are zero duplicate attractions.
4. There are zero forbidden template landmarks.
5. No cross-destination leakage exists.
"""

import os
import sys
import json
import re
import traceback

# Setup PYTHONPATH to import from src
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

# Force mock key to bypass API rate limits for bulk verification
os.environ["GEMINI_API_KEY"] = "mock_test_key"

from graph.workflow import (
    travel_graph,
    node_estimate_budget,
    node_optimize_rewards,
    node_generate_summary
)
from agents.constants import VALID_DESTINATIONS, known_place_names

# The list of 100 destinations requested by the user
DESTINATIONS = [
    "Goa", "Jaipur", "Udaipur", "Jodhpur", "Jaisalmer", "Mount Abu", "Pushkar", "Ranthambore",
    "Delhi", "Agra", "Varanasi", "Ayodhya", "Prayagraj", "Mathura", "Vrindavan", "Rishikesh",
    "Haridwar", "Mussoorie", "Nainital", "Auli", "Dehradun", "Kedarnath", "Badrinath",
    "Valley of Flowers", "Jim Corbett", "Shimla", "Manali", "Kasol", "Dharamshala",
    "McLeod Ganj", "Spiti Valley", "Kullu", "Dalhousie", "Khajjiar", "Leh", "Nubra Valley",
    "Pangong Lake", "Tso Moriri", "Srinagar", "Gulmarg", "Pahalgam", "Sonmarg", "Amritsar",
    "Chandigarh", "Mumbai", "Pune", "Lonavala", "Mahabaleshwar", "Nashik", "Ajanta Caves",
    "Ellora Caves", "Aurangabad", "Alibaug", "Matheran", "Bengaluru", "Mysuru", "Coorg",
    "Chikmagalur", "Hampi", "Gokarna", "Udupi", "Mangaluru", "Hyderabad", "Warangal",
    "Chennai", "Ooty", "Kodaikanal", "Madurai", "Rameswaram", "Kanyakumari", "Pondicherry",
    "Kochi", "Munnar", "Alleppey", "Wayanad", "Thekkady", "Kovalam", "Varkala",
    "Thiruvananthapuram", "Kolkata", "Darjeeling", "Kalimpong", "Gangtok", "Pelling",
    "Lachung", "Shillong", "Cherrapunji", "Dawki", "Kaziranga", "Guwahati", "Tawang",
    "Ziro Valley", "Kohima", "Aizawl", "Port Blair", "Havelock Island", "Neil Island",
    "Diu", "Bhuj", "Rann of Kutch"
]

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

def run_trip_pipeline(dest: str, days: int = 3) -> dict:
    query = f"Plan a {days} day trip to {dest} under 100000 INR. I have SBI card. Focus on sightseeing and local food."
    state = {
        "user_id": "bulk_test_user",
        "raw_query": query,
        "destination": "",
        "structured_query": {},
        "rag_context": "",
        "rag_documents": [],
        "allowed_places": [],
        "allowed_place_entities": [],
        "itinerary_json": {},
        "itinerary": "",
        "refined_itinerary_json": {},
        "refined_itinerary": "",
        "budget": {},
        "rewards": {},
        "summary": "",
        "user_feedback": None,
        "memory_context": "",
        "behavior_profile": {},
        "session_memory": {},
        "validation_report": {},
        "modification_intent": {},
        "changed_days": [],
        "stored_memories": [],
        "status": "started",
        "agent_metrics": {}
    }
    
    # Run the swarm graph
    res_graph = travel_graph.invoke(state)
    res_budget = node_estimate_budget(res_graph)
    res_rewards = node_optimize_rewards(res_budget)
    res_final = node_generate_summary(res_rewards)
    return res_final

def verify_destination_plan(dest: str, res: dict) -> dict:
    errors = []
    warnings = []
    
    # 1. Verify destination resolved matches requested destination
    resolved_dest = res.get("destination", "")
    if resolved_dest.lower() != dest.lower():
        errors.append(f"Destination mismatch: requested '{dest}', resolved '{resolved_dest}'")
        
    itinerary_json = res.get("refined_itinerary_json", {})
    day_plans = itinerary_json.get("days", [])
    
    # 2. Verify day count
    if len(day_plans) != 3:
        errors.append(f"Day count mismatch: expected 3 days, got {len(day_plans)}")
        
    # 3. Verify slots and look for duplicates, forbidden templates, and leakage
    scheduled_places = []
    allowed_list = VALID_DESTINATIONS.get(dest, [])
    allowed_lower = [ap.lower() for ap in allowed_list]
    
    for day in day_plans:
        day_num = day.get("day", 0)
        for slot in ["morning", "afternoon", "evening"]:
            items = day.get(slot, [])
            if not items:
                errors.append(f"Empty slot found: Day {day_num} {slot}")
            for item in items:
                loc = item.get("location", "").strip()
                if not loc:
                    errors.append(f"Empty location name: Day {day_num} {slot}")
                    continue
                scheduled_places.append(loc)
                
                # Check templates ONLY if location is not in allowed places list
                is_allowed = False
                for allowed_p in allowed_lower:
                    if loc.lower() == allowed_p or loc.lower().startswith(allowed_p) or allowed_p.startswith(loc.lower()):
                        is_allowed = True
                        break
                
                if not is_allowed:
                    for pattern in FORBIDDEN_TEMPLATES:
                        if re.search(pattern, loc.lower()):
                            errors.append(f"Forbidden template attraction '{loc}' on Day {day_num} {slot}")
                        
    # Check duplicate attractions
    seen = set()
    duplicates = []
    for loc in scheduled_places:
        loc_lower = loc.lower()
        if loc_lower in seen:
            duplicates.append(loc)
        seen.add(loc_lower)
        
    if duplicates:
        errors.append(f"Duplicate attractions found: {list(set(duplicates))}")
        
    # Check cross-destination contamination
    off_destination_names = known_place_names(exclude_destination=dest)
    itinerary_text = res.get("refined_itinerary", "").lower()
    leakage = []
    for p in off_destination_names:
        # Check if the exact off-destination name is present in the schedule
        # To avoid substring collisions, we only search if p is NOT part of the destination name.
        if len(p) > 4 and p.lower() in itinerary_text and p.lower() not in dest.lower():
            # If the place is in the scheduled places, it's leakage unless it is explicitly allowed in the target city
            for sp in scheduled_places:
                if p.lower() in sp.lower():
                    is_allowed = False
                    for allowed_p in allowed_lower:
                        if sp.lower() == allowed_p or allowed_p in sp.lower() or sp.lower() in allowed_p:
                            is_allowed = True
                            break
                    if not is_allowed:
                        leakage.append(p)
            
    if leakage:
        errors.append(f"Cross-destination leakage (found off-destination place names): {list(set(leakage))}")
        
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "attractions": scheduled_places,
        "resolved_dest": resolved_dest
    }

def main():
    print(f"Starting bulk verification of {len(DESTINATIONS)} destinations...")
    results = {}
    passed_count = 0
    failed_count = 0
    
    for idx, dest in enumerate(DESTINATIONS, 1):
        print(f"[{idx}/{len(DESTINATIONS)}] Testing {dest}...")
        try:
            res = run_trip_pipeline(dest, days=3)
            report = verify_destination_plan(dest, res)
            results[dest] = report
            if report["status"] == "PASS":
                passed_count += 1
                print(f"  [PASS] {dest}")
            else:
                failed_count += 1
                print(f"  [FAIL] {dest}: {report['errors']}")
        except Exception as e:
            failed_count += 1
            print(f"  [ERROR] {dest} failed to run: {str(e)}")
            traceback.print_exc()
            results[dest] = {
                "status": "FAIL",
                "errors": [f"Pipeline exception: {str(e)}"],
                "warnings": [],
                "attractions": [],
                "resolved_dest": dest
            }
            
    # Output markdown report
    conv_id = os.getenv("ANTIGRAVITY_CONVERSATION_ID", "cd529a44-5651-4ad6-b223-4a7097cd0693")
    output_path = f"/home/hariom/.gemini/antigravity-cli/brain/{conv_id}/verification_results.md"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 🗺️ Bulk Destination Verification Report\n\n")
        f.write("## Swarm Travel Planner Verification Summary\n\n")
        f.write(f"- **Total Destinations Tested:** {len(DESTINATIONS)}\n")
        f.write(f"- **Passed:** {passed_count} ✅\n")
        f.write(f"- **Failed:** {failed_count} ❌\n\n")
        
        f.write("### Verification Results Table\n\n")
        f.write("| # | Destination | Resolved As | Status | Errors / Warnings |\n")
        f.write("|---|-------------|-------------|--------|------------------|\n")
        for i, dest in enumerate(DESTINATIONS, 1):
            rep = results.get(dest, {"status": "FAIL", "resolved_dest": dest, "errors": ["No result data"]})
            status_emoji = "✅ PASS" if rep["status"] == "PASS" else "❌ FAIL"
            errs_warns = []
            if rep.get("errors"):
                errs_warns.append("**Errors:** " + "; ".join(rep["errors"]))
            if rep.get("warnings"):
                errs_warns.append("**Warnings:** " + "; ".join(rep["warnings"]))
            err_text = "<br>".join(errs_warns) if errs_warns else "None"
            f.write(f"| {i} | {dest} | {rep['resolved_dest']} | {status_emoji} | {err_text} |\n")
            
        f.write("\n\n### Detailed Itineraries Snapshot\n\n")
        for dest in DESTINATIONS:
            rep = results.get(dest)
            if rep and rep.get("attractions"):
                f.write(f"#### {dest} (Resolved as: {rep['resolved_dest']})\n")
                f.write("**Scheduled Attractions:**\n")
                for att in rep["attractions"]:
                    f.write(f"- {att}\n")
                f.write("\n")
                
    print(f"\nBulk verification complete. Results written to: {output_path}")

if __name__ == "__main__":
    main()
