"""Behavioral Memory Agent - user-specific behavioral memory with strict place filters."""
from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from agents.common import slug
from agents.constants import known_place_names
from rag.rag_agent import get_client, get_embedding_function

DB_PATH = os.path.join(os.path.dirname(__file__), "../memory/chroma_db")

# Strict 8 Behavioral Preference Types
BEHAVIORAL_TYPES = {
    "pace_preference",
    "food_preference",
    "crowd_preference",
    "activity_preference",
    "budget_preference",
    "comfort_preference",
    "walking_preference",
    "transport_preference",
}

def _get_user_collection(user_id: str):
    client = get_client()
    col_name = f"user_{slug(user_id)}_memory"
    return client.get_or_create_collection(col_name, embedding_function=get_embedding_function())

def _contains_blocked_place(text: str) -> bool:
    """Return True if the text contains any known physical place or destination names."""
    lower = text.lower()
    return any(place.lower() in lower for place in known_place_names())

def strip_place_names(text: str) -> str:
    """Remove known destination/place entities from memory text to maintain behavioral focus."""
    cleaned = text
    for place in sorted(known_place_names(), key=len, reverse=True):
        cleaned = re.sub(r'\b' + re.escape(place) + r'\b', "", cleaned, flags=re.IGNORECASE)
    return " ".join(cleaned.split())

def extract_behavioral_memories(preferences: dict, feedback: str | None = None) -> list[dict]:
    """Extract only durable style preferences, never places, destinations, or raw plans."""
    memories: list[dict] = []
    
    # Identify explicit dislikes/avoid items
    avoid_list = [a.lower() for a in preferences.get("avoid", [])]
    
    # 2. Parse from feedback & raw query (natural language)
    text_to_scan = ""
    if feedback:
        text_to_scan += " " + feedback.lower()
    if preferences.get("raw_query"):
        text_to_scan += " " + preferences.get("raw_query", "").lower()
    if preferences.get("avoid"):
        # Add raw avoids plus prefix to match "avoid <category>" pattern
        text_to_scan += " " + " ".join(avoid_list)
        for item in avoid_list:
            text_to_scan += f" avoid {item}"
            
    # Detect hard avoids from text scanning or explicit avoid list
    has_avoid_adventure = any("adventure" in a for a in avoid_list) or any(w in text_to_scan for w in ["avoid adventure", "no adventure", "skip adventure", "without adventure", "dislike adventure", "dislikes adventure", "avoiding adventure", "avoid water sports", "avoid parasailing", "avoid jet ski"])
    has_avoid_crowds = any("crowd" in a or "crowded" in a for a in avoid_list) or any(w in text_to_scan for w in ["avoid crowd", "less crowd", "quiet", "hidden gem", "offbeat", "peaceful", "avoiding crowd", "no crowd", "avoid crowded"])
    has_avoid_walking = any("walk" in a or "walking" in a for a in avoid_list) or any(w in text_to_scan for w in ["reduce walking", "less walking", "low walking", "avoid walking", "minimal walking"])
    
    # 1. Parse from structured preferences (query)
    pace = preferences.get("travel_pace") or preferences.get("travel_style")
    if pace in ["slow", "relaxed"]:
        memories.append({"type": "pace_preference", "text": "prefers slow and relaxed pacing"})
    elif pace in ["fast", "fast-paced", "hectic"]:
        memories.append({"type": "pace_preference", "text": "prefers fast-paced and packed schedules"})
        
    food = preferences.get("food_preference")
    if food == "local":
        memories.append({"type": "food_preference", "text": "prefers local and traditional food experiences"})
    elif food == "cafes":
        memories.append({"type": "food_preference", "text": "prefers cafe-style food stops"})
        
    budget = preferences.get("budget")
    days = max(1, preferences.get("days", 1))
    if budget:
        per_day = int(budget) / days
        if per_day <= 5000:
            memories.append({"type": "budget_preference", "text": "prefers budget-conscious travel planning"})
        elif per_day >= 12000:
            memories.append({"type": "budget_preference", "text": "prefers premium travel choices"})
            
    for interest in preferences.get("interests", []):
        interest_lower = interest.lower()
        if "scenic" in interest_lower or "view" in interest_lower:
            memories.append({"type": "activity_preference", "text": "prefers scenic and nature views"})
        elif "culture" in interest_lower or "history" in interest_lower:
            memories.append({"type": "activity_preference", "text": "prefers cultural and heritage visits"})
        elif "adventure" in interest_lower:
            if not has_avoid_adventure:
                memories.append({"type": "activity_preference", "text": "prefers adventure activities"})
        elif "shopping" in interest_lower:
            memories.append({"type": "activity_preference", "text": "prefers local bazaar and shopping walks"})
        elif "nightlife" in interest_lower:
            memories.append({"type": "activity_preference", "text": "prefers evening nightlife and lounges"})
            
    if text_to_scan:
        # Pace
        if any(w in text_to_scan for w in ["relaxed", "slow", "less hectic", "easy", "more rest", "leisure", "slow travel"]):
            memories.append({"type": "pace_preference", "text": "prefers slow and relaxed pacing"})
        if any(w in text_to_scan for w in ["fast", "packed", "cover more", "hectic"]):
            memories.append({"type": "pace_preference", "text": "prefers fast-paced and packed schedules"})
            
        # Food
        if "cafe" in text_to_scan:
            memories.append({"type": "food_preference", "text": "prefers cafe-style food stops"})
        if any(w in text_to_scan for w in ["local food", "street food", "traditional food", "local cuisine", "seafood"]):
            memories.append({"type": "food_preference", "text": "prefers local and traditional food experiences"})
            
        # Crowd
        if has_avoid_crowds:
            memories.append({"type": "crowd_preference", "text": "prefers avoiding crowded places"})
            
        # Activity
        if has_avoid_adventure:
            memories.append({"type": "activity_preference", "text": "avoids adventure activities"})
        if "shopping" in text_to_scan or "market" in text_to_scan or "bazaar" in text_to_scan:
            memories.append({"type": "activity_preference", "text": "prefers local bazaar and shopping walks"})
        if any(w in text_to_scan for w in ["nightlife", "lounge", "club", "bar", "party"]):
            memories.append({"type": "activity_preference", "text": "prefers evening nightlife and lounges"})
        if any(w in text_to_scan for w in ["scenic", "view", "sunset", "landscape", "nature views"]):
            memories.append({"type": "activity_preference", "text": "prefers scenic and nature views"})
        if "adventure" in text_to_scan and not has_avoid_adventure:
            if any(w in text_to_scan for w in ["like adventure", "prefer adventure", "love adventure", "adventure sports"]):
                memories.append({"type": "activity_preference", "text": "prefers adventure activities"})
            
        # Walking
        if has_avoid_walking:
            memories.append({"type": "walking_preference", "text": "prefers low walking routes"})
        elif any(w in text_to_scan for w in ["hiking", "trekking", "walk more"]):
            memories.append({"type": "walking_preference", "text": "prefers hiking and walking tolerance"})
            
        # Comfort
        if any(w in text_to_scan for w in ["increase comfort", "luxury", "comfort stay", "better hotel", "premium lodging", "luxury stay", "luxury hotel", "luxury accommodation", "premium hotel"]):
            memories.append({"type": "comfort_preference", "text": "prefers luxury and high comfort accommodation"})
        elif "homestay" in text_to_scan:
            memories.append({"type": "comfort_preference", "text": "prefers homestay comfort style"})
            
        # Transport
        if any(w in text_to_scan for w in ["cab", "taxi", "private transport", "private driver", "chauffeur"]):
            memories.append({"type": "transport_preference", "text": "prefers private transport"})
        elif any(w in text_to_scan for w in ["metro", "bus", "train", "public transit"]):
            memories.append({"type": "transport_preference", "text": "prefers public transit"})
            
    # Sanitize and remove duplicates
    unique_memories = []
    seen = set()
    for m in memories:
        text = strip_place_names(m["text"])
        if not text or _contains_blocked_place(text):
            continue
        key = (m["type"], text.lower())
        if key not in seen:
            unique_memories.append({"type": m["type"], "text": text})
            seen.add(key)
            
    return unique_memories

def clean_behavioral_memory(memories: list[dict] | list[str], destination: str | None = None) -> list[dict]:
    """Filter out non-behavior records and drop any accidental destination leakage."""
    cleaned: list[dict] = []
    seen = set()
    for memory in memories:
        if isinstance(memory, str):
            item = {"text": memory.strip("- ").strip(), "metadata": {"type": "behavior"}}
        else:
            item = memory
            
        text = (item.get("text") or "").strip()
        metadata = item.get("metadata") or {}
        memory_type = metadata.get("type") or item.get("type")
        
        if not text or memory_type not in BEHAVIORAL_TYPES:
            continue
            
        text = strip_place_names(text)
        if not text or _contains_blocked_place(text):
            continue
            
        key = text.lower()
        if key in seen:
            continue
            
        cleaned.append({"text": text, "metadata": {**metadata, "type": memory_type}})
        seen.add(key)
    return cleaned

def behavioral_memory_to_text(memories: list[dict]) -> str:
    if not memories:
        return "No previous behavioral memory found for this user."
    return "\n".join(f"- {memory['text']}" for memory in memories)

def build_behavior_profile(
    structured_query: dict,
    memories: list[dict] | None = None,
    feedback: str | None = None,
) -> dict:
    """Distill query + behavioral memories into a place-free profile for planning."""
    memories = memories or []
    text = " ".join(strip_place_names(memory.get("text", "")) for memory in memories)
    if feedback:
        text = f"{text} {strip_place_names(feedback)}"
    lower = text.lower()

    # Pacing Preference
    pace = structured_query.get("travel_pace") or "medium"
    if any(token in lower for token in ["slow", "relaxed", "less hectic", "easy"]):
        pace = "slow"
    elif any(token in lower for token in ["fast", "packed", "cover more", "hectic"]):
        pace = "fast"

    # Food Style Preference
    food_style = structured_query.get("food_preference") or "mixed"
    if "local" in lower or "street food" in lower or "traditional food" in lower:
        food_style = "local"
    elif "cafe" in lower:
        food_style = "cafes"

    # Crowd Preference
    crowd_preference = "avoid_crowds" if any(token in lower for token in ["crowd", "quiet", "hidden", "less crowded", "avoiding crowded"]) else "neutral"
    
    # Budget Tier
    budget = structured_query.get("budget")
    days = max(int(structured_query.get("days") or 1), 1)
    budget_style = "budget" if budget and int(budget) / days <= 5000 else "premium" if budget and int(budget) / days >= 12000 else "balanced"
    
    # Walking Tolerance
    walking_tolerance = "moderate"
    if "low walking" in lower or "reduce walking" in lower or "less walking" in lower or "minimal walking" in lower:
        walking_tolerance = "low"
    elif "hiking" in lower or "trekking" in lower or "walk more" in lower:
        walking_tolerance = "high"

    # Comfort Preference
    comfort_preference = "standard"
    if "high comfort" in lower or "luxury" in lower or "better hotel" in lower or "premium lodging" in lower or "premium hotel" in lower:
        comfort_preference = "high"
    elif "homestay" in lower:
        comfort_preference = "homestay"

    # Transport Style Preference
    transport_style = structured_query.get("transport_preference") or "local transport"
    if "private transport" in lower or "taxi" in lower or "cab" in lower:
        transport_style = "private transport"
    elif "public transit" in lower or "metro" in lower or "bus" in lower:
        transport_style = "public transit"

    # Activity Style Preferred
    activity_style = []
    for label, tokens in {
        "scenic": ["scenic", "view", "sunset", "photography"],
        "cafes": ["cafe", "cafes"],
        "culture": ["culture", "heritage", "temple", "fort", "history"],
        "adventure": ["adventure", "rafting", "paragliding", "trek", "water sports"],
        "shopping": ["shopping", "market", "bazaar"],
        "nature": ["nature", "beach", "forest", "waterfall"],
    }.items():
        if label in structured_query.get("interests", []) or any(token in lower for token in tokens):
            activity_style.append(label)

    # Avoid Categories
    avoid_categories = []
    if crowd_preference == "avoid_crowds":
        avoid_categories.append("crowded")
    if "avoid adventure" in lower or "avoids adventure" in lower:
        avoid_categories.append("adventure")

    activity_style = sorted(set(activity_style or structured_query.get("interests", []) or []))
    activity_style = [act for act in activity_style if act not in avoid_categories]

    # Calculate Confidence Scores
    counts = {}
    for m in memories:
        m_type = m.get("metadata", {}).get("type") or m.get("type")
        if m_type:
            counts[m_type] = counts.get(m_type, 0) + 1

    confidence = {
        "pace_preference": min(95, 50 + counts.get("pace_preference", 0) * 15) if pace != "medium" else 50,
        "food_preference": min(95, 50 + counts.get("food_preference", 0) * 15) if food_style != "mixed" else 50,
        "crowd_preference": min(95, 50 + counts.get("crowd_preference", 0) * 15) if crowd_preference != "neutral" else 50,
        "activity_preference": min(95, 50 + counts.get("activity_preference", 0) * 10) if activity_style else 50,
        "budget_preference": min(95, 50 + counts.get("budget_preference", 0) * 15) if budget_style != "balanced" else 50,
        "comfort_preference": min(95, 50 + counts.get("comfort_preference", 0) * 15) if comfort_preference != "standard" else 50,
        "walking_preference": min(95, 50 + counts.get("walking_preference", 0) * 15) if walking_tolerance != "moderate" else 50,
        "transport_preference": min(95, 50 + counts.get("transport_preference", 0) * 15) if transport_style != "local transport" else 50,
    }

    return {
        "pace": pace,
        "food_style": food_style,
        "travel_style": structured_query.get("travel_style") or "moderate",
        "budget_style": budget_style,
        "crowd_preference": crowd_preference,
        "activity_style": activity_style,
        "avoid_categories": avoid_categories,
        "accommodation": structured_query.get("accommodation") or "budget",
        "walking_tolerance": walking_tolerance,
        "comfort_preference": comfort_preference,
        "transport_style": transport_style,
        "confidence": confidence,
    }

def store_behavioral_memory(user_id: str, preferences: dict, feedback: str | None = None) -> list[dict]:
    """Store durable place-free behavioral preferences for a specific user collection."""
    from monitoring.logger import logger
    dest = preferences.get("destination", "")
    logger.info("[Memory Agent - Store] Entering agent")
    logger.info(f"[Memory Agent - Store] Destination received: {dest}")
    col = _get_user_collection(user_id)
    existing = set((col.get().get("documents") or [])) if col.count() else set()
    docs, ids, metas, stored = [], [], [], []
    ts = datetime.now(timezone.utc).isoformat()
    for item in extract_behavioral_memories(preferences, feedback):
        doc = item["text"]
        if doc in existing:
            continue
        docs.append(doc)
        ids.append(f"{slug(user_id)}_{uuid.uuid4().hex[:12]}")
        metas.append({"user_id": user_id, "timestamp": ts, "type": item["type"]})
        stored.append(item)
    if docs:
        col.add(documents=docs, ids=ids, metadatas=metas)
    logger.info(f"[Memory Agent - Store] Destination returned: {dest}")
    logger.info("[Memory Agent - Store] Leaving agent")
    return stored

def retrieve_user_memory(user_id: str, query: str = "travel preferences pacing food style budget behavior", n=10) -> str:
    return behavioral_memory_to_text(retrieve_behavioral_memory(user_id, query=query, n=n))

def retrieve_behavioral_memory(
    user_id: str,
    query: str = "travel preferences pacing food style budget behavior",
    n: int = 10,
    destination: str | None = None,
) -> list[dict]:
    col = _get_user_collection(user_id)
    if col.count() == 0:
        return []
    try:
        results = col.query(
            query_texts=[query],
            n_results=min(n * 2, col.count()),
            where={"user_id": user_id},
        )
        docs = results["documents"][0] if results.get("documents") else []
        metas = results["metadatas"][0] if results.get("metadatas") else [{} for _ in docs]
    except Exception:
        raw = col.get(where={"user_id": user_id})
        docs = raw.get("documents", [])[: n * 2]
        metas = raw.get("metadatas", [])[: n * 2]
    return clean_behavioral_memory(
        [{"text": doc, "metadata": meta} for doc, meta in zip(docs, metas)],
        destination=destination,
    )[:n]

def retrieve_behavior_profile(user_id: str, structured_query: dict, n: int = 10) -> dict:
    from monitoring.logger import logger
    dest = structured_query.get("destination", "")
    logger.info("[Memory Agent] Entering agent")
    logger.info(f"[Memory Agent] Destination received: {dest}")
    memories = retrieve_behavioral_memory(
        user_id,
        query="travel behavior pacing food crowd budget activity comfort walking style",
        n=n,
        destination=structured_query.get("destination"),
    )
    
    # Calculate confidence based on historical frequency (baseline 50% + 15% per matching memory, max 95%)
    counts = {}
    for m in memories:
        m_type = m.get("metadata", {}).get("type") or m.get("type")
        counts[m_type] = counts.get(m_type, 0) + 1
        
    confidences = {}
    for t in BEHAVIORAL_TYPES:
        cnt = counts.get(t, 0)
        confidences[t] = min(95, 50 + cnt * 15)
        
    profile = build_behavior_profile(structured_query, memories)
    profile["confidence"] = confidences
    logger.info(f"[Memory Agent] Destination returned: {dest}")
    logger.info("[Memory Agent] Leaving agent")
    return profile

def get_all_user_memory(user_id: str) -> list:
    col = _get_user_collection(user_id)
    if col.count() == 0:
        return []
    results = col.get(where={"user_id": user_id})
    docs = results.get("documents", [])
    metas = results.get("metadatas", [])
    return clean_behavioral_memory([{"text": doc, "metadata": meta} for doc, meta in zip(docs, metas)])
