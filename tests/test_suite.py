"""Comprehensive Test Suite for Multi-Agent AI Travel Assistant.

Verifies:
1. Compilation & Imports
2. FastAPI endpoints via TestClient (API Startup & Schema checks)
3. Destination contamination protection (Manali vs Goa vs Jaipur)
4. Behavior learning & transferability (Memory persistence & style transfer)
"""
from __future__ import annotations

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
try:
    import posthog
    posthog.capture = lambda *args, **kwargs: None
except ImportError:
    pass
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.app import app
from graph.workflow import travel_graph, refinement_graph
from memory.memory_agent import get_all_user_memory, _get_user_collection, retrieve_behavior_profile
from agents.constants import valid_destinations, known_place_names

class TestTravelPlanner(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Ensure ChromaDB collections are pre-ingested
        from rag.rag_agent import ingest_travel_data
        ingest_travel_data()
        
    def test_1_imports_and_compilation(self):
        """Test that all key agent and graph modules import successfully."""
        print("\n=== Running Import & Compilation Tests ===")
        modules = [
            "agents.common", "agents.constants", "agents.llm", 
            "agents.query_agent", "memory.memory_agent", "rag.rag_agent", 
            "planner.planner_agent", "rewards.budget_agent", "rewards.rewards_agent", 
            "validator.validator_agent", "agents.refinement_agent", "agents.summary_agent",
            "graph.workflow", "api.app", "app"
        ]
        for mod in modules:
            try:
                __import__(mod)
                print(f"  [OK] Imported {mod}")
            except Exception as e:
                self.fail(f"Failed to import {mod}: {e}")

    def test_2_api_endpoints(self):
        """Test all required API endpoints using FastAPI TestClient."""
        print("\n=== Running API Startup & Endpoint Tests ===")
        
        # 1. Health Endpoint
        r_health = self.client.get("/health")
        self.assertEqual(r_health.status_code, 200)
        self.assertEqual(r_health.json()["status"], "healthy")
        print("  [OK] GET /health passed")

        # 2. Plan Endpoint
        payload_plan = {
            "user_id": "test_user_api",
            "query": "Plan a 3-day Manali trip under ₹20,000. Have SBI card. Like local food."
        }
        r_plan = self.client.post("/plan", json=payload_plan)
        self.assertEqual(r_plan.status_code, 200)
        plan_data = r_plan.json()
        self.assertIn("current_state", plan_data)
        self.assertEqual(plan_data["current_state"]["destination"], "Manali")
        print("  [OK] POST /plan passed")

        # 3. Refine Endpoint
        current_state = plan_data["current_state"]
        payload_refine = {
            "user_id": "test_user_api",
            "current_state": current_state,
            "feedback": "Add cafes to Day 2"
        }
        r_refine = self.client.post("/refine", json=payload_refine)
        self.assertEqual(r_refine.status_code, 200)
        refine_data = r_refine.json()
        self.assertIn("current_state", refine_data)
        self.assertIn(2, refine_data["changed_days"])
        print("  [OK] POST /refine passed")

        # 4. Finalize Endpoint
        payload_finalize = {
            "user_id": "test_user_api",
            "final_state": refine_data["current_state"],
            "feedback": "Add cafes to Day 2"
        }
        r_finalize = self.client.post("/finalize", json=payload_finalize)
        self.assertEqual(r_finalize.status_code, 200)
        self.assertEqual(r_finalize.json()["status"], "finalized")
        print("  [OK] POST /finalize passed")

        # 5. Memory Endpoint
        r_mem = self.client.get("/memory/test_user_api")
        self.assertEqual(r_mem.status_code, 200)
        mem_data = r_mem.json()
        self.assertEqual(mem_data["user_id"], "test_user_api")
        self.assertTrue(mem_data["count"] > 0)
        print("  [OK] GET /memory/{user_id} passed")

    def test_3_destination_contamination(self):
        """Verify that a Manali query does not leak any Goa or Jaipur details."""
        print("\n=== Running Destination Contamination Tests ===")
        
        # Invoke a Manali request
        state = {
            "user_id": "test_contamination_user",
            "raw_query": "Plan a 3-day Manali trip. I want scenic views.",
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
            "status": "started"
        }
        result = travel_graph.invoke(state)
        
        # Verify result contains Manali and NO other city elements
        itinerary_text = result["refined_itinerary"].lower()
        
        # Prohibited places for a Manali trip
        prohibited = ["goa", "jaipur", "baga beach", "fontainhas", "hawa mahal", "chokhi dhani"]
        
        for p in prohibited:
            self.assertNotIn(p, itinerary_text, f"Contamination error: Found '{p}' in Manali itinerary!")
            
        print("  [OK] Contamination test passed: Manali plan contains no Goa or Jaipur traces.")

    def test_4_behavioral_learning_and_transfer(self):
        """Test that style preferences (e.g. avoiding adventure) persist and transfer to new destinations."""
        print("\n=== Running Behavioral Learning & Preference Transfer Tests ===")
        user_id = "test_learning_user_99"
        
        # Clear memory collection for this user to start fresh
        try:
            col = _get_user_collection(user_id)
            if col.count():
                col.delete(where={"user_id": user_id})
        except Exception:
            pass

        # Trip 1: Manali Trip with feedback to avoid adventure
        print("  Simulating Trip 1 (Manali) with feedback: 'avoid adventure activities'")
        
        # Step 1.1: Generate initial plan
        state_1 = {
            "user_id": user_id,
            "raw_query": "Plan a 3-day Manali trip under ₹20,000. I have SBI card.",
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
            "status": "started"
        }
        res_1 = travel_graph.invoke(state_1)
        
        # Step 1.2: Apply feedback 'avoid adventure'
        res_1["user_feedback"] = "Avoid adventure activities"
        refined_res_1 = refinement_graph.invoke(res_1)
        
        # Step 1.3: Finalize (which commits behavior to user memory)
        self.client.post("/finalize", json={
            "user_id": user_id,
            "final_state": refined_res_1,
            "feedback": refined_res_1.get("user_feedback")
        })
        
        # Step 2: Query for a different destination (Goa) and verify preference transfer
        print("  Simulating Trip 2 (Goa) - checking if 'avoid adventure' transfers automatically...")
        state_2 = {
            "user_id": user_id,
            "raw_query": "Plan a 3-day Goa trip.",
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
            "status": "started"
        }
        res_2 = travel_graph.invoke(state_2)
        
        # Verify the behavior profile loaded during Trip 2 planning contains 'avoid_categories' or memory traces
        profile = res_2.get("behavior_profile", {})
        self.assertIn("adventure", profile.get("avoid_categories", []), "Wait, did avoided categories load?")
        
        # Check that memory database actually returned the correct preferences
        memories = get_all_user_memory(user_id)
        m_texts = [m["text"].lower() for m in memories]
        
        # Check if the memory text contains the behavior pattern (without destination names!)
        has_avoid_pattern = any("avoid" in t or "less crowded" in t for t in m_texts)
        self.assertTrue(has_avoid_pattern, "Durable behavioral preference was not committed to user memory!")
        
        # Check destination isolation: no "Manali" should leak into Goa's memories
        for m in memories:
            self.assertNotIn("manali", m["text"].lower(), "Contamination Error: Destination leaked into behavioral memory!")
            
        print("  [OK] Behavioral learning passed: Preferences successfully transferred to Goa without destination leakage.")

    def test_5_partial_replanning(self):
        """Test that partial replanning surgically mutates only the targeted day."""
        print("\n=== Running Partial Replanning Surgical Verification Tests ===")
        user_id = "test_replanning_user"
        
        # 1. Generate baseline itinerary (3 days in Manali)
        state = {
            "user_id": user_id,
            "raw_query": "Plan a 3-day Manali trip. Have SBI card.",
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
            "status": "started"
        }
        res_initial = travel_graph.invoke(state)
        init_days = res_initial["refined_itinerary_json"]["days"]
        
        # Keep track of baseline places for Day 1, 2, and 3
        d1_init = [item["location"] for slot in ["morning", "afternoon", "evening"] for item in init_days[0][slot]]
        d2_init = [item["location"] for slot in ["morning", "afternoon", "evening"] for item in init_days[1][slot]]
        d3_init = [item["location"] for slot in ["morning", "afternoon", "evening"] for item in init_days[2][slot]]
        
        # 2. Apply surgical feedback specifically to Day 2
        feedback_state = {
            **res_initial,
            "user_feedback": "Replace Day 2 with cultural activities"
        }
        res_refined = refinement_graph.invoke(feedback_state)
        refined_days = res_refined["refined_itinerary_json"]["days"]
        
        d1_refined = [item["location"] for slot in ["morning", "afternoon", "evening"] for item in refined_days[0][slot]]
        d2_refined = [item["location"] for slot in ["morning", "afternoon", "evening"] for item in refined_days[1][slot]]
        d3_refined = [item["location"] for slot in ["morning", "afternoon", "evening"] for item in refined_days[2][slot]]
        
        # 3. Assertions: Day 1 and 3 MUST remain identical. Day 2 MUST have changed!
        self.assertEqual(d1_init, d1_refined, "Surgical failure: Day 1 changed during Day 2 replanning!")
        self.assertEqual(d3_init, d3_refined, "Surgical failure: Day 3 changed during Day 2 replanning!")
        self.assertNotEqual(d2_init, d2_refined, "Replanning failure: Day 2 did not change after refinement!")
        
        print("  [OK] Day-locking verified: Day 1 and Day 3 remained completely untouched.")
        print("  [OK] Day 2 mutated successfully from:", d2_init, "to:", d2_refined)

if __name__ == "__main__":
    unittest.main()
