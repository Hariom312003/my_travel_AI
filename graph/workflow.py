"""LangGraph workflow for the multi-agent travel planning pipeline."""
from __future__ import annotations

from typing import Optional, TypedDict

from langgraph.graph import StateGraph, END
from agents.query_agent import run_query_agent
from agents.planner_agent import itinerary_to_text, run_planner_agent
from agents.refinement_agent import run_refinement_agent
from agents.memory_agent import retrieve_behavior_profile, store_behavioral_memory
from agents.constants import allowed_places_for_destination, normalize_destination
from agents.rag_agent import retrieve_place_entities
from agents.validator_agent import clean_itinerary, validate_itinerary
from agents.rewards_agent import run_rewards_agent
from agents.budget_agent import run_budget_agent
from agents.summary_agent import run_summary_agent

class TravelState(TypedDict):
    user_id: str
    raw_query: str
    destination: str
    structured_query: dict
    rag_context: str
    rag_documents: list[dict]
    allowed_places: list[str]
    allowed_place_entities: list[dict]
    itinerary_json: dict
    itinerary: str
    refined_itinerary_json: dict
    refined_itinerary: str
    budget: dict
    rewards: dict
    summary: str
    user_feedback: Optional[str]
    memory_context: str
    behavior_profile: dict
    session_memory: dict
    validation_report: dict
    modification_intent: dict
    changed_days: list[int]
    stored_memories: list[dict]
    status: str

# ── Logger Import ────────────────────────────
from agents.logger import monitor_agent, set_request_id

# ── Node functions ───────────────────────────
def node_parse_query(state: TravelState) -> TravelState:
    set_request_id(f"{state.get('user_id', 'anon')}_{state.get('destination', 'travel')[:4]}")
    with monitor_agent("query_understanding_agent"):
        structured = run_query_agent(state["raw_query"])
    return {**state, "structured_query": structured, "status": "query_parsed"}

def node_isolate_destination(state: TravelState) -> TravelState:
    with monitor_agent("destination_isolation_agent"):
        destination = normalize_destination(state.get("structured_query", {}).get("destination", ""))
        structured = {**state.get("structured_query", {}), "destination": destination}
    return {
        **state,
        "destination": destination,
        "structured_query": structured,
        "allowed_places": allowed_places_for_destination(destination),
        "status": "destination_isolated",
    }

def node_retrieve_memory(state: TravelState) -> TravelState:
    with monitor_agent("memory_retrieval_agent"):
        profile = retrieve_behavior_profile(state["user_id"], state.get("structured_query", {}))
    return {
        **state,
        "behavior_profile": profile,
        "memory_context": "",
        "status": "behavior_profile_retrieved",
    }

def node_retrieve_destination_rag(state: TravelState) -> TravelState:
    with monitor_agent("destination_rag_agent"):
        sq = state.get("structured_query", {})
        place_entities = retrieve_place_entities(state.get("destination", sq.get("destination", "")), sq.get("interests", []), n=20)
    return {
        **state,
        "rag_documents": [],
        "rag_context": "",
        "allowed_place_entities": place_entities,
        "allowed_places": [place.get("name", "") for place in place_entities],
        "status": "structured_destination_places_retrieved",
    }

def node_plan_itinerary(state: TravelState) -> TravelState:
    with monitor_agent("planner_agent"):
        plan = run_planner_agent(
            state["structured_query"],
            state["user_id"],
            behavior_profile=state.get("behavior_profile", {}),
            allowed_places=state.get("allowed_place_entities", []),
        )
        itinerary_text = itinerary_to_text(plan)
    return {
        **state,
        "itinerary_json": plan,
        "itinerary": itinerary_text,
        "refined_itinerary_json": plan,
        "refined_itinerary": itinerary_text,
        "status": "itinerary_generated",
    }

def node_validate_itinerary(state: TravelState) -> TravelState:
    with monitor_agent("validation_agent"):
        sq = {**state.get("structured_query", {}), "_changed_days": state.get("changed_days", [])}
        plan, report = validate_itinerary(
            state.get("refined_itinerary_json") or state.get("itinerary_json", {}),
            sq,
            state.get("allowed_place_entities", []),
        )
        text = itinerary_to_text(plan)
    return {
        **state,
        "itinerary_json": plan if not state.get("user_feedback") else state.get("itinerary_json", plan),
        "itinerary": text if not state.get("user_feedback") else state.get("itinerary", text),
        "refined_itinerary_json": plan,
        "refined_itinerary": text,
        "validation_report": report,
        "changed_days": sorted(set(state.get("changed_days", [])) | set(report.get("repaired_days", []))),
        "status": "itinerary_validated",
    }

def node_refine_itinerary(state: TravelState) -> TravelState:
    if not state.get("user_feedback"):
        return {**state, "status": "refinement_skipped"}
    with monitor_agent("refinement_agent"):
        result = run_refinement_agent(
            state.get("refined_itinerary_json") or state.get("itinerary_json", {}),
            state["user_feedback"],
            state["structured_query"]
        )
        plan = result["updated_itinerary"]
    return {
        **state,
        "session_memory": {
            "feedback": state["user_feedback"],
            "modification_intent": result.get("modification_intent", {}),
        },
        "refined_itinerary_json": plan,
        "refined_itinerary": itinerary_to_text(plan),
        "modification_intent": result.get("modification_intent", {}),
        "changed_days": result.get("changed_days", []),
        "status": "itinerary_refined",
    }

def node_estimate_budget(state: TravelState) -> TravelState:
    with monitor_agent("budget_agent"):
        budget = run_budget_agent(state["structured_query"], state.get("refined_itinerary_json") or state.get("itinerary_json", {}))
    return {**state, "budget": budget, "status": "budget_estimated"}

def node_optimize_rewards(state: TravelState) -> TravelState:
    with monitor_agent("rewards_agent"):
        rewards = run_rewards_agent(state["structured_query"], state.get("budget", {}))
    return {**state, "rewards": rewards, "status": "rewards_optimized"}

def node_store_memory(state: TravelState) -> TravelState:
    with monitor_agent("memory_store_agent"):
        preferences = dict(state.get("structured_query", {}))
        preferences["raw_query"] = state.get("raw_query", "")
        stored = store_behavioral_memory(
            state["user_id"],
            preferences,
            feedback=state.get("user_feedback"),
        )
    return {**state, "stored_memories": stored, "status": "memory_stored"}

def node_generate_summary(state: TravelState) -> TravelState:
    with monitor_agent("summary_agent"):
        clean_plan = clean_itinerary(
            state.get("refined_itinerary_json") or state.get("itinerary_json", {}),
            state.get("destination") or state.get("structured_query", {}).get("destination", ""),
        )
        summary = run_summary_agent(
            clean_plan,
            state["structured_query"],
            state.get("budget", {}),
            state.get("rewards", ""),
            behavior_profile=state.get("behavior_profile")
        )
    return {
        **state,
        "refined_itinerary_json": clean_plan,
        "refined_itinerary": itinerary_to_text(clean_plan),
        "summary": summary,
        "status": "completed",
    }

# ── Build graph ──────────────────────────────
def build_travel_graph():
    g = StateGraph(TravelState)
    g.add_node("parse_query", node_parse_query)
    g.add_node("isolate_destination", node_isolate_destination)
    g.add_node("retrieve_memory", node_retrieve_memory)
    g.add_node("retrieve_destination_rag", node_retrieve_destination_rag)
    g.add_node("plan_itinerary", node_plan_itinerary)
    g.add_node("validate_itinerary", node_validate_itinerary)
    g.add_node("estimate_budget", node_estimate_budget)
    g.add_node("optimize_rewards", node_optimize_rewards)
    g.add_node("store_memory", node_store_memory)
    g.add_node("generate_summary", node_generate_summary)

    g.set_entry_point("parse_query")
    g.add_edge("parse_query", "isolate_destination")
    g.add_edge("isolate_destination", "retrieve_memory")
    g.add_edge("retrieve_memory", "retrieve_destination_rag")
    g.add_edge("retrieve_destination_rag", "plan_itinerary")
    g.add_edge("plan_itinerary", "validate_itinerary")
    g.add_edge("validate_itinerary", "estimate_budget")
    g.add_edge("estimate_budget", "optimize_rewards")
    g.add_edge("optimize_rewards", "store_memory")
    g.add_edge("store_memory", "generate_summary")
    g.add_edge("generate_summary", END)
    return g.compile()

def build_refinement_graph():
    g = StateGraph(TravelState)
    g.add_node("refine_itinerary", node_refine_itinerary)
    g.add_node("retrieve_destination_rag", node_retrieve_destination_rag)
    g.add_node("validate_itinerary", node_validate_itinerary)
    g.add_node("estimate_budget", node_estimate_budget)
    g.add_node("optimize_rewards", node_optimize_rewards)
    g.add_node("store_memory", node_store_memory)
    g.add_node("generate_summary", node_generate_summary)

    g.set_entry_point("refine_itinerary")
    g.add_edge("refine_itinerary", "retrieve_destination_rag")
    g.add_edge("retrieve_destination_rag", "validate_itinerary")
    g.add_edge("validate_itinerary", "estimate_budget")
    g.add_edge("estimate_budget", "optimize_rewards")
    g.add_edge("optimize_rewards", "store_memory")
    g.add_edge("store_memory", "generate_summary")
    g.add_edge("generate_summary", END)
    return g.compile()

travel_graph = build_travel_graph()
refinement_graph = build_refinement_graph()
