"""CLI entry point for a quick full-pipeline test."""
import os
import json
from dotenv import load_dotenv
load_dotenv()

from graph.workflow import travel_graph, TravelState
from agents.rewards_agent import rewards_to_text

def main():
    print("=" * 60)
    print("  Multi-Agent AI Travel Planner — CLI Test")
    print("=" * 60)

    query = input("\nEnter your travel query:\n> ").strip()
    if not query:
        query = "Plan a 3-day Manali trip under 20000 INR. I have SBI card. I like scenic places and local food."

    state: TravelState = {
        "user_id": "test_user_001",
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
        "status": "started"
    }

    print("\nRunning agents...\n")
    result = travel_graph.invoke(state)

    print("\nITINERARY:\n" + "-"*50)
    print(result["itinerary"])

    print("\nSTRUCTURED PLAN JSON:\n" + "-"*50)
    print(json.dumps(result["itinerary_json"], indent=2))

    print("\nBUDGET:\n" + "-"*50)
    print(json.dumps(result["budget"], indent=2))

    print("\nREWARDS:\n" + "-"*50)
    print(rewards_to_text(result["rewards"]))

    print("\nSUMMARY:\n" + "-"*50)
    print(result["summary"])

if __name__ == "__main__":
    main()
