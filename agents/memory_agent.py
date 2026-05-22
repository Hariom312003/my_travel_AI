"""Behavioral Memory Agent - per-user ChromaDB memory with behavioral filtering."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from agents.common import slug
from agents.constants import known_place_names
from agents.rag_agent import get_client, get_embedding_function

DB_PATH = os.path.join(os.path.dirname(__file__), "../memory/chroma_db")
MEMORY_TYPES = {
    "travel_style",
    "food_preference",
    "travel_pace",
    "budget_behavior",
    "crowd_preference",
    "refinement_pattern",
}
BEHAVIORAL_TYPES = MEMORY_TYPES

def _get_user_collection(user_id: str):
    client = get_client()
    col_name = f"user_{slug(user_id)}_memory"
    return client.get_or_create_collection(col_name, embedding_function=get_embedding_function())

def extract_behavioral_memories(preferences: dict, feedback: str | None = None) -> list[dict]:
    """Keep only durable style preferences, never places, destinations, or raw plans."""
    memories: list[dict] = []
    if preferences.get("travel_style"):
        memories.append({"type": "travel_style", "text": f"prefers {preferences['travel_style']} travel"})
    if preferences.get("travel_pace"):
        memories.append({"type": "travel_pace", "text": f"prefers {preferences['travel_pace']} paced itineraries"})
    if preferences.get("food_preference"):
        memories.append({"type": "food_preference", "text": f"prefers {preferences['food_preference']} food experiences"})
    preference_text = " ".join(
        strip_place_names(str(value))
        for value in [
            *(preferences.get("interests", []) or []),
            *(preferences.get("avoid", []) or []),
        ]
    ).lower()
    if any(token in preference_text for token in ["quiet", "hidden", "less crowded", "avoid crowd", "crowd"]):
        memories.append({"type": "crowd_preference", "text": "prefers less crowded places"})
    if any(token in preference_text for token in ["cafe", "cafes"]):
        memories.append({"type": "food_preference", "text": "prefers cafe-style food stops"})
    budget = preferences.get("budget")
    days = preferences.get("days") or 1
    if budget:
        per_day = int(budget / max(days, 1))
        if per_day <= 5000:
            memories.append({"type": "budget_behavior", "text": "prefers budget-conscious travel planning"})
        elif per_day >= 12000:
            memories.append({"type": "budget_behavior", "text": "is comfortable with premium travel choices"})
    if feedback:
        lower = feedback.lower()
        patterns = [
            ("refinement_pattern", "prefers less crowded places", ["avoid crowd", "less crowded", "quiet"]),
            ("refinement_pattern", "prefers more relaxed travel after review", ["relaxed", "less hectic", "slow"]),
            ("food_preference", "prefers cafe-style food stops", ["cafe", "cafes"]),
            ("refinement_pattern", "removes over-touristy attractions when refining", ["remove", "skip", "avoid"]),
        ]
        for memory_type, text, needles in patterns:
            if any(needle in lower for needle in needles):
                memories.append({"type": memory_type, "text": text})
    seen = set()
    unique = []
    for item in memories:
        key = (item["type"], item["text"].lower())
        if key not in seen:
            unique.append(item)
            seen.add(key)
    return unique


def _contains_blocked_place(text: str) -> bool:
    lower = text.lower()
    return any(place.lower() in lower for place in known_place_names())


def strip_place_names(text: str) -> str:
    """Remove known destination/place entities from memory text before profiling."""
    cleaned = text
    for place in sorted(known_place_names(), key=len, reverse=True):
        cleaned = cleaned.replace(place, "")
        cleaned = cleaned.replace(place.lower(), "")
        cleaned = cleaned.replace(place.upper(), "")
    return " ".join(cleaned.split())


def clean_behavioral_memory(memories: list[dict] | list[str], destination: str | None = None) -> list[dict]:
    """Allow only behavior records and drop old attraction/destination leakage."""
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
        if not text:
            continue
        if memory_type not in BEHAVIORAL_TYPES and memory_type != "behavior":
            continue
        text = strip_place_names(text)
        if not text or _contains_blocked_place(text):
            continue
        key = text.lower()
        if key in seen:
            continue
        cleaned.append({"text": text, "metadata": {**metadata, "type": memory_type or "behavior"}})
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

    pace = structured_query.get("travel_pace") or "medium"
    if any(token in lower for token in ["slow", "relaxed", "less hectic", "easy"]):
        pace = "slow"
    elif any(token in lower for token in ["fast", "packed", "cover more"]):
        pace = "fast"

    food_style = structured_query.get("food_preference") or "mixed"
    if "local" in lower or "street food" in lower:
        food_style = "local"
    elif "cafe" in lower:
        food_style = "cafes"

    crowd_preference = "avoid_crowds" if any(token in lower for token in ["crowd", "quiet", "hidden", "less crowded"]) else "neutral"
    budget = structured_query.get("budget")
    days = max(int(structured_query.get("days") or 1), 1)
    budget_style = "budget" if budget and int(budget) / days <= 5000 else "premium" if budget and int(budget) / days >= 12000 else "balanced"

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

    avoid_categories = []
    if crowd_preference == "avoid_crowds":
        avoid_categories.append("crowded")

    return {
        "pace": pace,
        "food_style": food_style,
        "travel_style": structured_query.get("travel_style") or "moderate",
        "budget_style": budget_style,
        "crowd_preference": crowd_preference,
        "activity_style": sorted(set(activity_style or structured_query.get("interests", []) or [])),
        "avoid_categories": avoid_categories,
        "accommodation": structured_query.get("accommodation") or "budget",
    }


def store_behavioral_memory(user_id: str, preferences: dict, feedback: str | None = None) -> list[dict]:
    """Store durable behavioral preferences for exactly one user collection."""
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
    memories = retrieve_behavioral_memory(
        user_id,
        query="travel behavior pacing food crowd budget activity style",
        n=n,
        destination=structured_query.get("destination"),
    )
    return build_behavior_profile(structured_query, memories)

def get_all_user_memory(user_id: str) -> list:
    col = _get_user_collection(user_id)
    if col.count() == 0:
        return []
    results = col.get(where={"user_id": user_id})
    docs = results.get("documents", [])
    metas = results.get("metadatas", [])
    return clean_behavioral_memory([{"text": doc, "metadata": meta} for doc, meta in zip(docs, metas)])
