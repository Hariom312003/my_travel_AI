"""FastAPI backend for the Multi-Agent AI Travel Planner."""
from __future__ import annotations

import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from graph.workflow import travel_graph, refinement_graph, TravelState
from agents.memory_agent import get_all_user_memory, store_behavioral_memory
from agents.rewards_agent import rewards_to_text
from agents.planner_agent import itinerary_to_text
from agents.validator_agent import clean_itinerary

app = FastAPI(title="Multi-Agent AI Travel Planner", version="1.0.0")

class TripRequest(BaseModel):
    user_id: str
    query: str

class RefineRequest(BaseModel):
    user_id: str
    current_state: dict
    feedback: str

class FinalizeRequest(BaseModel):
    user_id: str
    final_state: dict
    feedback: str | None = None

class MemoryRequest(BaseModel):
    user_id: str


def _initial_state(user_id: str, query: str) -> TravelState:
    return {
        "user_id": user_id,
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
    }


def _response(result: dict) -> dict:
    destination = result.get("destination") or result.get("structured_query", {}).get("destination", "")
    clean_plan = clean_itinerary(
        result.get("refined_itinerary_json") or result.get("itinerary_json", {}),
        destination,
    )
    clean_text = itinerary_to_text(clean_plan)
    current_state = {
        "user_id": result.get("user_id", ""),
        "raw_query": result.get("raw_query", ""),
        "destination": result.get("destination", ""),
        "structured_query": result.get("structured_query", {}),
        "itinerary_json": clean_plan,
        "itinerary": clean_text,
        "refined_itinerary_json": clean_plan,
        "refined_itinerary": clean_text,
        "budget": result.get("budget", {}),
        "rewards": result.get("rewards", {}),
        "summary": result.get("summary", ""),
        "modification_intent": result.get("modification_intent", {}),
        "changed_days": result.get("changed_days", []),
        "status": result.get("status", ""),
    }
    return {
        "status": result.get("status", "success"),
        "current_state": current_state,
        "structured_query": result.get("structured_query", {}),
        "itinerary": clean_text,
        "itinerary_json": clean_plan,
        "refined_itinerary": clean_text,
        "refined_itinerary_json": clean_plan,
        "budget": result.get("budget", {}),
        "rewards": result.get("rewards", {}),
        "rewards_text": rewards_to_text(result.get("rewards", {})) if isinstance(result.get("rewards"), dict) else result.get("rewards", ""),
        "summary": result.get("summary", ""),
        "changed_days": result.get("changed_days", []),
        "modification_intent": result.get("modification_intent", {}),
    }

@app.get("/")
def root():
    return {"message": "Multi-Agent AI Travel Planner API", "version": "1.0.0"}

@app.post("/generate-trip")
def generate_trip(req: TripRequest):
    try:
        result = travel_graph.invoke(_initial_state(req.user_id, req.query))
        return _response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/refine-trip")
def refine_trip(req: RefineRequest):
    try:
        state = {**_initial_state(req.user_id, req.current_state.get("raw_query", "")), **req.current_state, "user_id": req.user_id, "user_feedback": req.feedback}
        result = refinement_graph.invoke(state)
        return _response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/finalize-trip")
def finalize_trip(req: FinalizeRequest):
    try:
        state = req.final_state
        stored = store_behavioral_memory(
            req.user_id,
            state.get("structured_query", {}),
            feedback=req.feedback or state.get("user_feedback"),
        )
        return {
            "status": "finalized",
            "user_id": req.user_id,
            "stored_memories": stored,
            "final_plan": {
                "structured_query": state.get("structured_query", {}),
                "itinerary": state.get("refined_itinerary") or state.get("itinerary", ""),
                "itinerary_json": state.get("refined_itinerary_json") or state.get("itinerary_json", {}),
                "budget": state.get("budget", {}),
                "rewards": state.get("rewards", {}),
                "summary": state.get("summary", ""),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-user-memory")
def get_memory(req: MemoryRequest):
    memories = get_all_user_memory(req.user_id)
    return {"user_id": req.user_id, "memories": memories, "count": len(memories)}
