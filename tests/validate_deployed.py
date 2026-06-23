#!/usr/bin/env python3
"""Programmatic validation script for the deployed travel planner app.

Tests 16 destinations against the FastAPI backend, verifying:
- Itinerary, budget, rewards, travel guide, route visualization, monitoring metrics
- Destination preservation
- Cross-destination contamination (Goa/Jaipur/Manali leakage)
- Daily attraction uniqueness
"""

import os
import sys
import time
import json
import re
import subprocess
import requests
import traceback

# Setup python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from agents.constants import VALID_DESTINATIONS, known_place_names

DESTINATIONS = [
    "Bangkok", "Tokyo", "Singapore", "Paris", "Rome", "London", "Dubai", "New York",
    "Sydney", "Iceland", "Peru", "Cape Town", "Mumbai", "Chennai", "Goa", "Jaipur"
]

def start_api_server():
    print("Starting FastAPI Backend Server on port 8000...")
    cmd = [sys.executable, "-m", "uvicorn", "src.api.app:app", "--host", "127.0.0.1", "--port", "8000"]
    # Run in workspace root
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc

def wait_for_server(timeout=30):
    url = "http://127.0.0.1:8000/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                print("FastAPI Backend Server is online and healthy!")
                return True
        except:
            pass
        time.sleep(0.5)
    return False

def verify_trip(dest: str, res: dict) -> dict:
    errors = []
    warnings = []
    
    # 1. Resolved destination matches requested destination
    resolved_dest = res.get("destination", "")
    if resolved_dest.lower() != dest.lower():
        errors.append(f"Destination mismatch: requested '{dest}', resolved '{resolved_dest}'")
        
    itinerary_json = res.get("itinerary_json", {})
    day_plans = itinerary_json.get("days", [])
    
    # 2. Itinerary generated
    if not day_plans:
        errors.append("Itinerary JSON is empty or missing days")
    elif len(day_plans) != 3:
        errors.append(f"Expected 3 days, got {len(day_plans)}")
        
    # 3. Budget generated
    budget = res.get("budget", {})
    if not budget or not budget.get("total_cost"):
        errors.append("Budget is empty or missing total_cost")
        
    # 4. Rewards generated
    rewards = res.get("rewards", {})
    if not rewards:
        errors.append("Rewards recommendations are empty")
        
    # 5. Travel guide generated
    summary = res.get("summary", "")
    if not summary:
        errors.append("Travel guide narrative summary is empty")
        
    # 6. Route visualization populated
    route_populated = True
    scheduled_places = []
    day_place_sets = []
    
    for day in day_plans:
        day_num = day.get("day", 0)
        day_places = []
        for slot in ["morning", "afternoon", "evening"]:
            items = day.get(slot, [])
            if not items:
                route_populated = False
                errors.append(f"Missing items for route visualization on Day {day_num} {slot}")
            for item in items:
                loc = item.get("location", "").strip()
                trans = item.get("transport", "").strip()
                dur = item.get("duration", "").strip()
                
                if not loc or not trans or not dur:
                    route_populated = False
                    errors.append(f"Incomplete transit visualization fields on Day {day_num} {slot}")
                if loc:
                    scheduled_places.append(loc)
                    day_places.append(loc.lower())
        day_place_sets.append(set(day_places))
        
    # 7. Monitoring data present
    metrics = res.get("agent_metrics", {})
    if not metrics or "Query Agent" not in metrics:
        errors.append("Monitoring agent performance metrics are missing")
        
    # 8. Contamination checks (Bangkok, Paris, Iceland outputs must not contain Goa/Jaipur/Manali)
    contamination = []
    if dest.lower() in ["bangkok", "paris", "iceland"]:
        itinerary_text = (res.get("itinerary", "") + " " + json.dumps(itinerary_json)).lower()
        for p in ["goa", "jaipur", "manali"]:
            if p in itinerary_text:
                # Double check: make sure it's not a false positive substring
                for sp in scheduled_places:
                    if p in sp.lower():
                        contamination.append(sp)
        if contamination:
            errors.append(f"Contamination check failed: Found off-destination attractions {contamination}")
            
    # 9. Attraction uniqueness checks
    # Every day contains unique attractions (no duplicate across the whole 3 days)
    seen = set()
    duplicates = []
    for loc in scheduled_places:
        loc_lower = loc.lower()
        if loc_lower in seen:
            duplicates.append(loc)
        seen.add(loc_lower)
    if duplicates:
        errors.append(f"Duplicate attractions found: {list(set(duplicates))}")
        
    # Day 1 != Day 2 != Day 3 (verify distinct sets of places)
    if len(day_place_sets) == 3:
        d1, d2, d3 = day_place_sets[0], day_place_sets[1], day_place_sets[2]
        if d1 & d2:
            errors.append(f"Overlap between Day 1 and Day 2: {list(d1 & d2)}")
        if d2 & d3:
            errors.append(f"Overlap between Day 2 and Day 3: {list(d2 & d3)}")
        if d1 & d3:
            errors.append(f"Overlap between Day 1 and Day 3: {list(d1 & d3)}")
            
    # Get model and provider details from monitoring metrics
    provider = "Mock"
    model = "mock-model"
    gen_time = 0.0
    
    if metrics:
        planner_metrics = metrics.get("Planner Agent", {})
        provider = planner_metrics.get("provider", "Gemini")
        model = planner_metrics.get("model", "gemini-2.5-flash")
        # Total latency is sum of all node latencies
        gen_time = sum(m.get("latency", 0.0) for m in metrics.values())
        
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "provider": provider,
        "model": model,
        "gen_time": round(gen_time, 2),
        "places": scheduled_places,
        "duplicates": duplicates,
        "contamination": contamination
    }

def main():
    proc = start_api_server()
    try:
        if not wait_for_server():
            print("Failed to start FastAPI server. Exiting.")
            sys.exit(1)
            
        print("\nStarting live verification of deployed production app...")
        results = {}
        passed_count = 0
        failed_count = 0
        
        # We query the local REST API running in production mode
        url = "http://127.0.0.1:8000/plan"
        
        for idx, dest in enumerate(DESTINATIONS, 1):
            print(f"\n[{idx}/{len(DESTINATIONS)}] Testing live API for {dest}...")
            payload = {
                "user_id": f"live_val_user_{dest.lower()}",
                "query": f"Plan a 3-day trip to {dest} under 150000 INR. I have SBI card. Focus on local sightseeing and food."
            }
            
            # Send API request
            start_t = time.time()
            try:
                r = requests.post(url, json=payload, timeout=240)
                if r.status_code != 200:
                    raise Exception(f"HTTP {r.status_code}: {r.text}")
                res_data = r.json()
                # Verify
                report = verify_trip(dest, res_data)
                results[dest] = report
                if report["status"] == "PASS":
                    passed_count += 1
                    print(f"  [PASS] {dest} in {report['gen_time']}s using {report['provider']} {report['model']}")
                else:
                    failed_count += 1
                    print(f"  [FAIL] {dest}: {report['errors']}")
            except Exception as e:
                failed_count += 1
                print(f"  [ERROR] {dest} pipeline call failed: {str(e)}")
                results[dest] = {
                    "status": "FAIL",
                    "errors": [f"API exception: {str(e)}"],
                    "warnings": [],
                    "provider": "Gemini",
                    "model": "gemini-2.5-flash",
                    "gen_time": round(time.time() - start_t, 2),
                    "places": [],
                    "duplicates": [],
                    "contamination": []
                }
                
        conv_id = os.getenv("ANTIGRAVITY_CONVERSATION_ID", "cd529a44-5651-4ad6-b223-4a7097cd0693")
        output_path = f"/home/hariom/.gemini/antigravity-cli/brain/{conv_id}/deployed_validation_report.md"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# 🔬 Live Deployed Application Validation Report\n\n")
            f.write("## Swarm Deployment Production Verification Summary\n\n")
            f.write(f"- **Total Destinations Tested:** {len(DESTINATIONS)}\n")
            f.write(f"- **Passed:** {passed_count} ✅\n")
            f.write(f"- **Failed:** {failed_count} ❌\n\n")
            
            f.write("### Deployed Verification Table\n\n")
            f.write("| Destination | Provider | Model | Generation Time | Places Generated | Duplicates | Contamination | Status |\n")
            f.write("|-------------|----------|-------|-----------------|------------------|------------|---------------|--------|\n")
            for dest in DESTINATIONS:
                rep = results.get(dest)
                status_emoji = "✅ PASS" if rep["status"] == "PASS" else "❌ FAIL"
                places_txt = ", ".join(rep["places"][:4]) + "..." if rep["places"] else "None"
                dup_txt = ", ".join(rep["duplicates"]) if rep["duplicates"] else "None"
                cont_txt = ", ".join(rep["contamination"]) if rep["contamination"] else "None"
                f.write(f"| {dest} | {rep['provider']} | {rep['model']} | {rep['gen_time']}s | {places_txt} | {dup_txt} | {cont_txt} | {status_emoji} |\n")
                
            if failed_count > 0:
                f.write("\n### Failure Investigation Details\n\n")
                for dest in DESTINATIONS:
                    rep = results.get(dest)
                    if rep["status"] == "FAIL":
                        f.write(f"#### ❌ {dest} Failures\n")
                        for err in rep["errors"]:
                            f.write(f"- {err}\n")
                        f.write("\n")
                        
        print(f"\nLive validation complete. Report written to: {output_path}")
        if failed_count > 0:
            print(f"FAILED: {failed_count} destinations failed checks!")
            sys.exit(1)
        else:
            print("ALL LIVE DESTINATIONS PASSED SUCCESSFULLY!")
            sys.exit(0)
            
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    main()
