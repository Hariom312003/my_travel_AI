"""LangGraph workflow for the multi-agent travel planning pipeline."""
from __future__ import annotations

from typing import Optional, TypedDict

from langgraph.graph import StateGraph, END
from agents.query_agent import run_query_agent
from planner.planner_agent import itinerary_to_text, run_planner_agent
from agents.refinement_agent import run_refinement_agent
from memory.memory_agent import retrieve_behavior_profile, store_behavioral_memory
from agents.constants import allowed_places_for_destination, normalize_destination
import time
from agents.llm import llm_trace_var
from rag.rag_agent import retrieve_place_entities, run_destination_agent
from validator.validator_agent import clean_itinerary, validate_itinerary
from rewards.rewards_agent import run_rewards_agent
from rewards.budget_agent import run_budget_agent
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
    agent_metrics: dict

# ── Logger Import ────────────────────────────
from monitoring.logger import monitor_agent, set_request_id

# ── Node functions ───────────────────────────
def node_parse_query(state: TravelState) -> TravelState:
    set_request_id(f"{state.get('user_id', 'anon')}_{state.get('destination', 'travel')[:4]}")
    t_start = time.time()
    llm_trace_var.set([])
    
    with monitor_agent("query_understanding_agent"):
        structured = run_query_agent(state["raw_query"])
        
    t_end = time.time()
    latency = t_end - t_start
    
    traces = llm_trace_var.get() or []
    llm_info = traces[0] if traces else {"provider": "Mock", "model": "mock-model", "prompt_size": len(state.get("raw_query", "")), "response_size": 250}
    
    metrics = {
        "start_time": t_start,
        "end_time": t_end,
        "latency": round(latency, 2),
        "provider": llm_info.get("provider", "Mock"),
        "model": llm_info.get("model", "mock-model"),
        "prompt_size": llm_info.get("prompt_size", 0),
        "response_size": llm_info.get("response_size", 0)
    }
    
    agent_metrics = dict(state.get("agent_metrics", {}))
    agent_metrics["Query Agent"] = metrics
    
    dest_extracted = structured.get("destination", "")
    print("\n" + "="*40, flush=True)
    print("--------------------------------", flush=True)
    print("USER INPUT", flush=True)
    print("--------------------------------", flush=True)
    print(state["raw_query"], flush=True)
    print("\n--------------------------------", flush=True)
    print("QUERY PARSER", flush=True)
    print("--------------------------------", flush=True)
    print(dest_extracted, flush=True)
    print("\n--------------------------------", flush=True)
    print("QUERY AGENT", flush=True)
    print("--------------------------------", flush=True)
    print("input destination: None", flush=True)
    print(f"output destination: {dest_extracted}", flush=True)
    print("="*40 + "\n", flush=True)
    
    return {**state, "structured_query": structured, "agent_metrics": agent_metrics, "status": "query_parsed"}

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
    set_request_id(f"{state.get('user_id', 'anon')}_{state.get('destination', 'travel')[:4]}")
    t_start = time.time()
    
    with monitor_agent("memory_retrieval_agent"):
        profile = retrieve_behavior_profile(state["user_id"], state.get("structured_query", {}))
        
    t_end = time.time()
    latency = t_end - t_start
    
    # Merge preferences back to structured_query
    sq = dict(state.get("structured_query", {}))
    if profile.get("comfort_preference") == "high":
        sq["accommodation"] = "luxury"
    elif profile.get("comfort_preference") == "homestay":
        sq["accommodation"] = "budget"
        
    if profile.get("pace") in ["slow", "fast"]:
        sq["travel_pace"] = profile["pace"]
        sq["travel_style"] = "relaxed" if profile["pace"] == "slow" else "fast-paced"
        
    if profile.get("food_style") in ["local", "cafes"]:
        sq["food_preference"] = profile["food_style"]
        
    if profile.get("transport_style") in ["private transport", "public transit"]:
        sq["transport_preference"] = profile["transport_style"]
        
    # Record memory retrieval agent metrics
    metrics = {
        "start_time": t_start,
        "end_time": t_end,
        "latency": round(latency, 2),
        "provider": "Mock" if llm_trace_var.get() else "ChromaDB",
        "model": "local-embedding-v3",
        "prompt_size": len(state.get("raw_query", ""))
    }
    agent_metrics = dict(state.get("agent_metrics", {}))
    agent_metrics["Memory Agent"] = metrics
    
    dest_in = state.get("destination") or state.get("structured_query", {}).get("destination", "")
    dest_out = sq.get("destination", "")
    print("\n" + "="*40, flush=True)
    print("--------------------------------", flush=True)
    print("MEMORY AGENT", flush=True)
    print("--------------------------------", flush=True)
    print(f"input destination: {dest_in}", flush=True)
    print(f"output destination: {dest_out}", flush=True)
    print("="*40 + "\n", flush=True)
    
    return {
        **state,
        "behavior_profile": profile,
        "structured_query": sq,
        "memory_context": "",
        "agent_metrics": agent_metrics,
        "status": "behavior_profile_retrieved",
    }

def node_retrieve_destination_rag(state: TravelState) -> TravelState:
    set_request_id(f"{state.get('user_id', 'anon')}_{state.get('destination', 'travel')[:4]}")
    t_start = time.time()
    llm_trace_var.set([])
    
    destination = state.get("destination") or state.get("structured_query", {}).get("destination", "")
    interests = state.get("structured_query", {}).get("interests", [])
    
    days = int(state.get("structured_query", {}).get("days") or 3)
    needed = max(20, days * 3 + 10)
    with monitor_agent("destination_rag_agent"):
        # Retrieve places from ChromaDB RAG
        place_entities = retrieve_place_entities(destination, interests, n=needed)
        # Query LLM Destination Guide dynamically
        dest_guide = run_destination_agent(destination, interests)
        
    t_end = time.time()
    latency = t_end - t_start
    
    traces = llm_trace_var.get() or []
    llm_info = traces[0] if traces else {"provider": "Mock", "model": "mock-model", "prompt_size": len(destination), "response_size": 1500}
    
    metrics = {
        "start_time": t_start,
        "end_time": t_end,
        "latency": round(latency, 2),
        "provider": llm_info.get("provider", "Mock"),
        "model": llm_info.get("model", "mock-model"),
        "prompt_size": llm_info.get("prompt_size", 0),
        "response_size": llm_info.get("response_size", 0)
    }
    
    agent_metrics = dict(state.get("agent_metrics", {}))
    agent_metrics["Destination Agent"] = metrics
    
    dest_in = destination
    dest_out = destination
    print("\n" + "="*40, flush=True)
    print("--------------------------------", flush=True)
    print("RAG AGENT", flush=True)
    print("--------------------------------", flush=True)
    print(f"input destination: {dest_in}", flush=True)
    print(f"output destination: {dest_out}", flush=True)
    print("="*40 + "\n", flush=True)
    
    return {
        **state,
        "rag_documents": [],
        "rag_context": dest_guide,
        "allowed_place_entities": place_entities,
        "allowed_places": [place.get("name", "") for place in place_entities],
        "agent_metrics": agent_metrics,
        "status": "structured_destination_places_retrieved",
    }

def node_plan_itinerary(state: TravelState) -> TravelState:
    set_request_id(f"{state.get('user_id', 'anon')}_{state.get('destination', 'travel')[:4]}")
    t_start = time.time()
    llm_trace_var.set([])
    
    with monitor_agent("planner_agent"):
        plan = run_planner_agent(
            state["structured_query"],
            state["user_id"],
            behavior_profile=state.get("behavior_profile", {}),
            allowed_places=state.get("allowed_place_entities", []),
            destination_guide=state.get("rag_context", ""),
        )
        itinerary_text = itinerary_to_text(plan)
        
    t_end = time.time()
    latency = t_end - t_start
    
    traces = llm_trace_var.get() or []
    llm_info = traces[0] if traces else {"provider": "Mock", "model": "mock-model", "prompt_size": 2500, "response_size": 3000}
    
    metrics = {
        "start_time": t_start,
        "end_time": t_end,
        "latency": round(latency, 2),
        "provider": llm_info.get("provider", "Mock"),
        "model": llm_info.get("model", "mock-model"),
        "prompt_size": llm_info.get("prompt_size", 0),
        "response_size": llm_info.get("response_size", 0)
    }
    
    agent_metrics = dict(state.get("agent_metrics", {}))
    agent_metrics["Planner Agent"] = metrics
    
    dest_in = state.get("destination") or state.get("structured_query", {}).get("destination", "")
    dest_out = plan.get("destination", dest_in)
    print("\n" + "="*40, flush=True)
    print("--------------------------------", flush=True)
    print("PLANNER AGENT", flush=True)
    print("--------------------------------", flush=True)
    print(f"input destination: {dest_in}", flush=True)
    print(f"output destination: {dest_out}", flush=True)
    print("="*40 + "\n", flush=True)
    
    return {
        **state,
        "itinerary_json": plan,
        "itinerary": itinerary_text,
        "refined_itinerary_json": plan,
        "refined_itinerary": itinerary_text,
        "agent_metrics": agent_metrics,
        "status": "itinerary_generated",
    }

def node_validate_itinerary(state: TravelState) -> TravelState:
    t_start = time.time()
    with monitor_agent("validation_agent"):
        sq = {**state.get("structured_query", {}), "_changed_days": state.get("changed_days", [])}
        plan, report = validate_itinerary(
            state.get("refined_itinerary_json") or state.get("itinerary_json", {}),
            sq,
            state.get("allowed_place_entities", []),
        )
        text = itinerary_to_text(plan)
    t_end = time.time()
    latency = t_end - t_start
    
    metrics = {
        "start_time": t_start,
        "end_time": t_end,
        "latency": round(latency, 2),
        "provider": "Deterministic",
        "model": "grounding-rules",
        "prompt_size": len(text)
    }
    agent_metrics = dict(state.get("agent_metrics", {}))
    agent_metrics["Validator Agent"] = metrics
    
    # Track validation retry count
    retry_count = agent_metrics.get("validation_retry_count", 0)
    if not report.get("is_valid", True):
        agent_metrics["validation_retry_count"] = retry_count + 1
    
    dest_in = state.get("destination") or state.get("structured_query", {}).get("destination", "")
    dest_out = plan.get("destination") or dest_in
    print("\n" + "="*40, flush=True)
    print("--------------------------------", flush=True)
    print("VALIDATOR AGENT", flush=True)
    print("--------------------------------", flush=True)
    print(f"input destination: {dest_in}", flush=True)
    print(f"output destination: {dest_out}", flush=True)
    print("="*40 + "\n", flush=True)
    
    return {
        **state,
        "itinerary_json": plan if not state.get("user_feedback") else state.get("itinerary_json", plan),
        "itinerary": text if not state.get("user_feedback") else state.get("itinerary", text),
        "refined_itinerary_json": plan,
        "refined_itinerary": text,
        "validation_report": report,
        "changed_days": sorted(set(state.get("changed_days", [])) | set(report.get("repaired_days", []))),
        "agent_metrics": agent_metrics,
        "status": "itinerary_validated",
    }

def node_refine_itinerary(state: TravelState) -> TravelState:
    if not state.get("user_feedback"):
        return {**state, "status": "refinement_skipped"}
    set_request_id(f"{state.get('user_id', 'anon')}_{state.get('destination', 'travel')[:4]}")
    t_start = time.time()
    llm_trace_var.set([])
    
    with monitor_agent("refinement_agent"):
        result = run_refinement_agent(
            state.get("refined_itinerary_json") or state.get("itinerary_json", {}),
            state["user_feedback"],
            state["structured_query"]
        )
        plan = result["updated_itinerary"]
        
    t_end = time.time()
    latency = t_end - t_start
    
    traces = llm_trace_var.get() or []
    llm_info = traces[0] if traces else {"provider": "Mock", "model": "mock-model", "prompt_size": 3000, "response_size": 2500}
    
    metrics = {
        "start_time": t_start,
        "end_time": t_end,
        "latency": round(latency, 2),
        "provider": llm_info.get("provider", "Mock"),
        "model": llm_info.get("model", "mock-model"),
        "prompt_size": llm_info.get("prompt_size", 0),
        "response_size": llm_info.get("response_size", 0)
    }
    agent_metrics = dict(state.get("agent_metrics", {}))
    agent_metrics["Refinement Agent"] = metrics
    
    dest_in = state.get("destination") or state.get("structured_query", {}).get("destination", "")
    dest_out = plan.get("destination") or dest_in
    print("\n" + "="*40, flush=True)
    print("--------------------------------", flush=True)
    print("REFINEMENT AGENT", flush=True)
    print("--------------------------------", flush=True)
    print(f"input destination: {dest_in}", flush=True)
    print(f"output destination: {dest_out}", flush=True)
    print("="*40 + "\n", flush=True)
    
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
        "agent_metrics": agent_metrics,
        "status": "itinerary_refined",
    }

def node_estimate_budget(state: TravelState) -> TravelState:
    set_request_id(f"{state.get('user_id', 'anon')}_{state.get('destination', 'travel')[:4]}")
    t_start = time.time()
    llm_trace_var.set([])
    
    with monitor_agent("budget_agent"):
        budget = run_budget_agent(state["structured_query"], state.get("refined_itinerary_json") or state.get("itinerary_json", {}))
        
    t_end = time.time()
    latency = t_end - t_start
    
    traces = llm_trace_var.get() or []
    llm_info = traces[0] if traces else {"provider": "Mock", "model": "mock-model", "prompt_size": 1200, "response_size": 400}
    
    metrics = {
        "start_time": t_start,
        "end_time": t_end,
        "latency": round(latency, 2),
        "provider": llm_info.get("provider", "Mock"),
        "model": llm_info.get("model", "mock-model"),
        "prompt_size": llm_info.get("prompt_size", 0),
        "response_size": llm_info.get("response_size", 0)
    }
    
    agent_metrics = dict(state.get("agent_metrics", {}))
    agent_metrics["Budget Agent"] = metrics
    
    dest_in = state.get("destination") or state.get("structured_query", {}).get("destination", "")
    dest_out = dest_in
    print("\n" + "="*40, flush=True)
    print("--------------------------------", flush=True)
    print("BUDGET AGENT", flush=True)
    print("--------------------------------", flush=True)
    print(f"input destination: {dest_in}", flush=True)
    print(f"output destination: {dest_out}", flush=True)
    print("="*40 + "\n", flush=True)
    
    return {**state, "budget": budget, "agent_metrics": agent_metrics, "status": "budget_estimated"}

def node_optimize_rewards(state: TravelState) -> TravelState:
    set_request_id(f"{state.get('user_id', 'anon')}_{state.get('destination', 'travel')[:4]}")
    t_start = time.time()
    llm_trace_var.set([])
    
    with monitor_agent("rewards_agent"):
        rewards = run_rewards_agent(state["structured_query"], state.get("budget", {}))
        
    t_end = time.time()
    latency = t_end - t_start
    
    traces = llm_trace_var.get() or []
    llm_info = traces[0] if traces else {"provider": "Mock", "model": "mock-model", "prompt_size": 1000, "response_size": 800}
    
    metrics = {
        "start_time": t_start,
        "end_time": t_end,
        "latency": round(latency, 2),
        "provider": llm_info.get("provider", "Mock"),
        "model": llm_info.get("model", "mock-model"),
        "prompt_size": llm_info.get("prompt_size", 0),
        "response_size": llm_info.get("response_size", 0)
    }
    agent_metrics = dict(state.get("agent_metrics", {}))
    agent_metrics["Rewards Agent"] = metrics
    
    dest_in = state.get("destination") or state.get("structured_query", {}).get("destination", "")
    dest_out = dest_in
    print("\n" + "="*40, flush=True)
    print("--------------------------------", flush=True)
    print("REWARDS AGENT", flush=True)
    print("--------------------------------", flush=True)
    print(f"input destination: {dest_in}", flush=True)
    print(f"output destination: {dest_out}", flush=True)
    print("="*40 + "\n", flush=True)
    
    return {**state, "rewards": rewards, "agent_metrics": agent_metrics, "status": "rewards_optimized"}

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
    set_request_id(f"{state.get('user_id', 'anon')}_{state.get('destination', 'travel')[:4]}")
    t_start = time.time()
    llm_trace_var.set([])
    
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
        
    t_end = time.time()
    latency = t_end - t_start
    
    traces = llm_trace_var.get() or []
    llm_info = traces[0] if traces else {"provider": "Mock", "model": "mock-model", "prompt_size": 3000, "response_size": 2000}
    
    metrics = {
        "start_time": t_start,
        "end_time": t_end,
        "latency": round(latency, 2),
        "provider": llm_info.get("provider", "Mock"),
        "model": llm_info.get("model", "mock-model"),
        "prompt_size": llm_info.get("prompt_size", 0),
        "response_size": llm_info.get("response_size", 0)
    }
    
    agent_metrics = dict(state.get("agent_metrics", {}))
    agent_metrics["Summary Agent"] = metrics
    
    dest_in = state.get("destination") or state.get("structured_query", {}).get("destination", "")
    dest_out = dest_in
    print("\n" + "="*40, flush=True)
    print("--------------------------------", flush=True)
    print("SUMMARY AGENT", flush=True)
    print("--------------------------------", flush=True)
    print(f"input destination: {dest_in}", flush=True)
    print(f"output destination: {dest_out}", flush=True)
    print("="*40 + "\n", flush=True)
    
    return {
        **state,
        "refined_itinerary_json": clean_plan,
        "refined_itinerary": itinerary_to_text(clean_plan),
        "summary": summary,
        "agent_metrics": agent_metrics,
        "status": "completed",
    }

# ── Build graph ──────────────────────────────
def route_travel_validation(state: TravelState):
    report = state.get("validation_report", {})
    retry_count = state.get("agent_metrics", {}).get("validation_retry_count", 0)
    if not report.get("is_valid", True) and retry_count < 2:
        print(f"\n[Workflow] Validation failed! Routing back to plan_itinerary (Retry {retry_count}/2)...", flush=True)
        return "plan_itinerary"
    return END

def route_refinement_validation(state: TravelState):
    report = state.get("validation_report", {})
    retry_count = state.get("agent_metrics", {}).get("validation_retry_count", 0)
    if not report.get("is_valid", True) and retry_count < 2:
        print(f"\n[Workflow] Validation failed! Routing back to refine_itinerary (Retry {retry_count}/2)...", flush=True)
        return "refine_itinerary"
    return END

def build_travel_graph():
    g = StateGraph(TravelState)
    g.add_node("parse_query", node_parse_query)
    g.add_node("isolate_destination", node_isolate_destination)
    g.add_node("retrieve_memory", node_retrieve_memory)
    g.add_node("retrieve_destination_rag", node_retrieve_destination_rag)
    g.add_node("plan_itinerary", node_plan_itinerary)
    g.add_node("validate_itinerary", node_validate_itinerary)

    g.set_entry_point("parse_query")
    g.add_edge("parse_query", "isolate_destination")
    g.add_edge("isolate_destination", "retrieve_memory")
    g.add_edge("retrieve_memory", "retrieve_destination_rag")
    g.add_edge("retrieve_destination_rag", "plan_itinerary")
    g.add_edge("plan_itinerary", "validate_itinerary")
    
    g.add_conditional_edges(
        "validate_itinerary",
        route_travel_validation,
        {
            "plan_itinerary": "plan_itinerary",
            END: END
        }
    )
    return g.compile()

def build_refinement_graph():
    g = StateGraph(TravelState)
    g.add_node("refine_itinerary", node_refine_itinerary)
    g.add_node("retrieve_destination_rag", node_retrieve_destination_rag)
    g.add_node("validate_itinerary", node_validate_itinerary)

    g.set_entry_point("refine_itinerary")
    g.add_edge("refine_itinerary", "retrieve_destination_rag")
    g.add_edge("retrieve_destination_rag", "validate_itinerary")
    
    g.add_conditional_edges(
        "validate_itinerary",
        route_refinement_validation,
        {
            "refine_itinerary": "refine_itinerary",
            END: END
        }
    )
    return g.compile()

travel_graph = build_travel_graph()
refinement_graph = build_refinement_graph()

def run_downstream_agents_bg(state: TravelState):
    """Executes the downstream steps (budget, rewards, memory, summary) in a background thread."""
    import threading
    from agents.common import save_trip_state_to_file
    from monitoring.logger import logger
    
    def worker():
        try:
            logger.info("Starting background downstream agents execution...")
            # 1. Budget
            logger.info("Downstream BG: Estimating budget...")
            s_budget = node_estimate_budget(state)
            save_trip_state_to_file(s_budget["user_id"], s_budget)
            
            # 2. Rewards
            logger.info("Downstream BG: Optimizing rewards...")
            s_rewards = node_optimize_rewards(s_budget)
            save_trip_state_to_file(s_rewards["user_id"], s_rewards)
            
            # 3. Store Memory
            logger.info("Downstream BG: Storing memory...")
            s_memory = node_store_memory(s_rewards)
            save_trip_state_to_file(s_memory["user_id"], s_memory)
            
            # 4. Generate Summary
            logger.info("Downstream BG: Generating summary...")
            s_summary = node_generate_summary(s_memory)
            
            # Save final completed state
            s_summary["status"] = "completed"
            save_trip_state_to_file(s_summary["user_id"], s_summary)
            logger.info("Background downstream agents execution completed successfully.")
        except Exception as e:
            logger.error(f"Error in background downstream execution: {e}")
            
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
