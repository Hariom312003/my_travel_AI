"""FastAPI backend for the Multi-Agent AI Travel Planner."""
from __future__ import annotations

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
try:
    import posthog
    posthog.capture = lambda *args, **kwargs: None
except ImportError:
    pass
from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from graph.workflow import travel_graph, refinement_graph, TravelState
from memory.memory_agent import get_all_user_memory, store_behavioral_memory
from rewards.rewards_agent import rewards_to_text
from planner.planner_agent import itinerary_to_text
from validator.validator_agent import clean_itinerary

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
        "agent_metrics": {},
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
        "agent_metrics": result.get("agent_metrics", {}),
    }
    return {
        "status": result.get("status", "success"),
        "destination": destination,
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
        "agent_metrics": result.get("agent_metrics", {}),
    }

@app.get("/")
def root():
    return {"message": "Multi-Agent AI Travel Planner API", "version": "1.0.0"}

@app.get("/health")
def health_check():
    """Health check endpoint to verify API server status."""
    from agents.llm import get_available_provider
    try:
        providers = get_available_provider()
        configured = [p["name"] for p in providers]
    except Exception as e:
        configured = [f"Error: {str(e)}"]
    return {
        "status": "healthy",
        "version": "1.0.0",
        "configured_providers": configured
    }

@app.get("/provider-health")
def provider_health():
    """Retrieve live provider failover and cooldown telemetry metrics."""
    from agents.llm import get_telemetry_health
    try:
        return get_telemetry_health()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch provider health: {str(e)}")

@app.post("/plan")
def plan_trip(req: TripRequest, x_force_unavailable: str | None = Header(default=None)):
    """Generate a structured, validated, and optimized trip plan from a query."""
    if not req.user_id.strip():
        raise HTTPException(status_code=400, detail="user_id cannot be empty")
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query cannot be empty")
    
    # Handle dynamic provider forcing for validation/telemetry tests
    token = None
    if x_force_unavailable:
        from agents.llm import forced_unavailable_providers_var
        forced = [p.strip() for p in x_force_unavailable.split(",")]
        token = forced_unavailable_providers_var.set(forced)
        
    try:
        from graph.workflow import run_downstream_agents_sync
        from agents.common import save_trip_state_to_file
        result = travel_graph.invoke(_initial_state(req.user_id, req.query))
        result = run_downstream_agents_sync(result)
        save_trip_state_to_file(req.user_id, result)
        return _response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Planning failed: {str(e)}")
    finally:
        if token:
            from agents.llm import forced_unavailable_providers_var
            forced_unavailable_providers_var.reset(token)

@app.post("/generate-trip", deprecated=True)
def generate_trip(req: TripRequest):
    return plan_trip(req)

@app.post("/refine")
def refine_trip_endpoint(req: RefineRequest, x_force_unavailable: str | None = Header(default=None)):
    """Apply surgical refinements to an existing trip plan based on user feedback."""
    if not req.user_id.strip():
        raise HTTPException(status_code=400, detail="user_id cannot be empty")
    if not req.feedback.strip():
        raise HTTPException(status_code=400, detail="feedback cannot be empty")
        
    # Handle dynamic provider forcing for validation/telemetry tests
    token = None
    if x_force_unavailable:
        from agents.llm import forced_unavailable_providers_var
        forced = [p.strip() for p in x_force_unavailable.split(",")]
        token = forced_unavailable_providers_var.set(forced)
        
    try:
        from graph.workflow import run_downstream_agents_sync
        from agents.common import save_trip_state_to_file
        state = {
            **_initial_state(req.user_id, req.current_state.get("raw_query", "")),
            **req.current_state,
            "user_id": req.user_id,
            "user_feedback": req.feedback
        }
        result = refinement_graph.invoke(state)
        result = run_downstream_agents_sync(result)
        save_trip_state_to_file(req.user_id, result)
        return _response(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refinement failed: {str(e)}")
    finally:
        if token:
            from agents.llm import forced_unavailable_providers_var
            forced_unavailable_providers_var.reset(token)

@app.post("/refine-trip", deprecated=True)
def refine_trip(req: RefineRequest):
    return refine_trip_endpoint(req)

@app.post("/finalize")
def finalize_trip_endpoint(req: FinalizeRequest):
    """Finalize a trip plan and save the extracted behavioral preferences to memory."""
    if not req.user_id.strip():
        raise HTTPException(status_code=400, detail="user_id cannot be empty")
    try:
        state = req.final_state
        preferences = dict(state.get("structured_query", {}))
        preferences["raw_query"] = state.get("raw_query", "")
        stored = store_behavioral_memory(
            req.user_id,
            preferences,
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
        raise HTTPException(status_code=500, detail=f"Finalization failed: {str(e)}")

@app.post("/finalize-trip", deprecated=True)
def finalize_trip(req: FinalizeRequest):
    return finalize_trip_endpoint(req)

@app.get("/memory/{user_id}")
def get_user_memory_endpoint(user_id: str):
    """Retrieve all stored behavioral memories for a given user."""
    if not user_id.strip():
        raise HTTPException(status_code=400, detail="user_id cannot be empty")
    try:
        memories = get_all_user_memory(user_id)
        return {"user_id": user_id, "memories": memories, "count": len(memories)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve memory: {str(e)}")

@app.post("/get-user-memory", deprecated=True)
def get_memory(req: MemoryRequest):
    return get_user_memory_endpoint(req.user_id)
