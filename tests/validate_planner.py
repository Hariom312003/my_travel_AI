#!/usr/bin/env python3
"""Automated Validation Suite for Strict Itinerary Uniqueness and Landmark Quality.

Tests:
- Bangkok (5, 10, 15 days)
- Tokyo (5, 10, 15 days)
- Paris (5, 10, 15 days)

Verifies:
- 0 Duplicate attractions scheduled across the entire itinerary.
- 0 Forbidden generic/template landmarks in the output.
- Day count matches the requested duration (5, 10, 15 days).
- 100% Relevance (Destination matches, no cross-city leakage).
"""

import os
import sys
import json
import re
import unittest

# Ensure the root directory is in python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

# Force mock key for validation if no real keys exist in env
if not any(os.environ.get(k) for k in ["GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "CLAUDE_API_KEY", "OPENAI_API_KEY"]):
    print("No API keys found. Running validator in sandbox/mock mode.")
    os.environ["CLAUDE_API_KEY"] = "mock_test_key"
else:
    print("API keys found. Running validator in live production mode.")

from graph.workflow import (
    travel_graph,
    node_estimate_budget,
    node_optimize_rewards,
    node_generate_summary
)

class TestItineraryUniquenessAndQuality(unittest.TestCase):

    def run_trip_pipeline(self, dest: str, days: int) -> dict:
        query = f"Plan a {days} day trip to {dest} under 150000 INR. I have SBI card. Focus on sights and local food."
        state = {
            "user_id": "strict_uniqueness_test_user",
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
        res_graph = travel_graph.invoke(state)
        res_budget = node_estimate_budget(res_graph)
        res_rewards = node_optimize_rewards(res_budget)
        res_final = node_generate_summary(res_rewards)
        return res_final

    def check_uniqueness_and_relevance(self, dest_name: str, days: int):
        print(f"\n[TEST] Verifying {dest_name} for {days} days...")
        res = self.run_trip_pipeline(dest_name, days)
        
        # 1. Verify destination is preserved
        self.assertEqual(res["destination"].lower(), dest_name.lower())
        
        itinerary_json = res.get("refined_itinerary_json", {})
        day_plans = itinerary_json.get("days", [])
        
        # 2. Verify day count matches
        self.assertEqual(len(day_plans), days, f"Expected {days} days, got {len(day_plans)}")
        
        # 3. Verify 0 duplicate attractions
        scheduled_places = []
        for day in day_plans:
            for slot in ["morning", "afternoon", "evening"]:
                for item in day.get(slot, []):
                    loc = item.get("location", "").strip()
                    self.assertTrue(loc, f"Empty location found in Day {day.get('day')} {slot}")
                    scheduled_places.append(loc.lower())
                    
        duplicates = [p for p in set(scheduled_places) if scheduled_places.count(p) > 1]
        self.assertFalse(
            duplicates, 
            f"Duplicate attractions detected in {dest_name} {days}-day itinerary: {duplicates}"
        )
        
        # 4. Verify 0 forbidden generic template landmarks
        forbidden_regexes = [
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
        
        for loc in scheduled_places:
            for pattern in forbidden_regexes:
                self.assertFalse(
                    re.search(pattern, loc),
                    f"Forbidden template landmark '{loc}' matches pattern '{pattern}' in {dest_name} trip!"
                )
                
        # 5. Verify no cross-city leakage
        itinerary_text = res.get("refined_itinerary", "").lower()
        prohibited = ["goa", "manali", "jaipur", "baga beach", "rohtang pass", "hawa mahal"]
        prohibited = [p for p in prohibited if p != dest_name.lower()]
        
        for p in prohibited:
            self.assertNotIn(
                p, itinerary_text, 
                f"Contamination error: Found '{p}' in {dest_name} {days}-day itinerary!"
            )
            
        print(f"  [PASS] {dest_name} {days} days: 0 duplicates, 0 templates, 0 leakage. Verified successfully.")

    # --- Bangkok Tests ---
    def test_bangkok_05_days(self):
        self.check_uniqueness_and_relevance("Bangkok", 5)

    def test_bangkok_10_days(self):
        self.check_uniqueness_and_relevance("Bangkok", 10)

    def test_bangkok_15_days(self):
        self.check_uniqueness_and_relevance("Bangkok", 15)

    # --- Tokyo Tests ---
    def test_tokyo_05_days(self):
        self.check_uniqueness_and_relevance("Tokyo", 5)

    def test_tokyo_10_days(self):
        self.check_uniqueness_and_relevance("Tokyo", 10)

    def test_tokyo_15_days(self):
        self.check_uniqueness_and_relevance("Tokyo", 15)

    # --- Paris Tests ---
    def test_paris_05_days(self):
        self.check_uniqueness_and_relevance("Paris", 5)

    def test_paris_10_days(self):
        self.check_uniqueness_and_relevance("Paris", 10)

    def test_paris_15_days(self):
        self.check_uniqueness_and_relevance("Paris", 15)

if __name__ == "__main__":
    sys.exit(unittest.main())
