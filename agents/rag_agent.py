"""RAG Agent - retrieves destination knowledge from ChromaDB with advanced metadata fields."""
from __future__ import annotations

import json
import os
import re
from typing import Any

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from agents.constants import (
    VALID_DESTINATIONS,
    allowed_places_for_destination,
    known_place_names,
    known_places_by_destination,
    load_travel_data,
    normalize_destination,
    valid_destinations,
)

DB_PATH = os.path.join(os.path.dirname(__file__), "../memory/chroma_db")
COLLECTION = "travel_knowledge_v3"  # v3 for expanded metadata fields

class SimpleEmbeddingFunction:
    """Small deterministic embedding function for local/dev runs without API keys."""

    def __call__(self, input: list[str]) -> list[list[float]]:
        import hashlib
        vectors = []
        for text in input:
            buckets = [0.0] * 64
            for token in re.findall(r"[a-z0-9]+", text.lower()):
                h_val = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
                buckets[h_val % len(buckets)] += 1.0
            norm = sum(v * v for v in buckets) ** 0.5 or 1.0
            vectors.append([v / norm for v in buckets])
        return vectors

def get_embedding_function():
    if os.getenv("OPENAI_API_KEY"):
        try:
            return embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            )
        except Exception:
            pass
    return SimpleEmbeddingFunction()

def get_client():
    return chromadb.PersistentClient(
        path=DB_PATH,
        settings=Settings(anonymized_telemetry=False),
    )

def _load_data() -> list[dict[str, Any]]:
    return list(load_travel_data())

def ingest_travel_data():
    client = get_client()
    embedding_function = get_embedding_function()
    data = _load_data()
    try:
        col = client.get_collection(COLLECTION, embedding_function=embedding_function)
        if col.count() == len(data):
            return
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    col = client.get_or_create_collection(COLLECTION, embedding_function=embedding_function)
    data = _load_data()
    docs, ids, metas = [], [], []
    for i, item in enumerate(data):
        docs.append(
            f"{item['place']} in {item['location']} ({item.get('type', 'place')}): "
            f"{item['description']} Tags: {', '.join(item.get('tags', []))}"
        )
        ids.append(f"travel_{i}")
        destination = item["location"]
        category = item.get("type", "")
        
        # Ingest all 12 Advanced RAG fields as metadata
        metas.append({
            "place": item["place"],
            "destination": destination,
            "location": destination,
            "category": category,
            "type": category,
            "tags": ",".join(item.get("tags", [])),
            "food": item.get("food", ""),
            "nightlife": item.get("nightlife", ""),
            "culture": item.get("culture", ""),
            "shopping": item.get("shopping", ""),
            "nature": item.get("nature", ""),
            "adventure": item.get("adventure", ""),
            "hidden_gems": item.get("hidden_gems", ""),
            "transport_tips": item.get("transport", "Local transit"),
            "local_tips": item.get("local_tips", ""),
            "recommended_duration": item.get("duration", "2 hours"),
            "best_visiting_time": item.get("best_time", "morning"),
            "budget_category": item.get("pricing", "budget"),
        })
    col.add(documents=docs, ids=ids, metadatas=metas)

def retrieve_travel_documents(destination: str, interests: list, n: int = 8) -> list[dict[str, Any]]:
    destination = normalize_destination(destination)
    data = _load_data()
    dest = (destination or "").lower()
    interest_text = " ".join(interests or []).lower()
    avoid_crowded = "crowd" in interest_text or "hidden" in interest_text or "quiet" in interest_text
    ranked = []
    for item in data:
        haystack = " ".join([
            item.get("place", ""),
            item.get("location", ""),
            item.get("type", ""),
            item.get("description", ""),
            " ".join(item.get("tags", [])),
        ]).lower()
        if dest and item.get("location", "").lower() != dest:
            continue
        score = 5
        score += sum(2 for interest in interests or [] if interest.lower() in haystack)
        score += sum(1 for token in interest_text.split() if token in haystack)
        if avoid_crowded and "crowded" in item.get("tags", []):
            score -= 3
        if score > 0:
            ranked.append((score, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in ranked[:n]]

def place_entity(item: dict[str, Any]) -> dict[str, Any]:
    tags = item.get("tags", []) or []
    category = item.get("type", "place")
    ideal_time = item.get("best_time", "morning")
    
    return {
        "name": item.get("place", ""),
        "destination": item.get("location", ""),
        "category": category,
        "tags": tags,
        "crowd_level": "crowded" if "crowded" in tags else "quiet" if any(tag in tags for tag in ["hidden gem", "relaxed", "calm"]) else "normal",
        "ideal_time": ideal_time,
        "duration_hours": 3 if category in {"adventure", "nature"} else 2,
        
        # Advanced RAG Fields
        "food": item.get("food", ""),
        "nightlife": item.get("nightlife", ""),
        "culture": item.get("culture", ""),
        "shopping": item.get("shopping", ""),
        "nature": item.get("nature", ""),
        "adventure": item.get("adventure", ""),
        "hidden_gems": item.get("hidden_gems", ""),
        "transport_tips": item.get("transport", "Local transit"),
        "local_tips": item.get("local_tips", ""),
        "recommended_duration": item.get("duration", "2 hours"),
        "best_visiting_time": ideal_time,
        "budget_category": item.get("pricing", "budget"),
    }

def retrieve_place_entities(destination: str, interests: list, n: int = 12) -> list[dict[str, Any]]:
    destination = normalize_destination(destination)
    try:
        ingest_travel_data()
        col = get_client().get_or_create_collection(COLLECTION, embedding_function=get_embedding_function())
        query = f"{destination} {' '.join(interests or [])}"
        results = col.query(
            query_texts=[query],
            n_results=n,
            where={"destination": destination},
        )
        metadatas = results.get("metadatas", [[]])[0]
        if metadatas:
            entities = []
            for metadata in metadatas:
                tags = [tag for tag in str(metadata.get("tags", "")).split(",") if tag]
                category = metadata.get("category") or metadata.get("type") or "place"
                entity = place_entity({
                    "place": metadata.get("place", ""),
                    "location": metadata.get("destination", destination),
                    "type": category,
                    "tags": tags,
                    "food": metadata.get("food", ""),
                    "nightlife": metadata.get("nightlife", ""),
                    "culture": metadata.get("culture", ""),
                    "shopping": metadata.get("shopping", ""),
                    "nature": metadata.get("nature", ""),
                    "adventure": metadata.get("adventure", ""),
                    "hidden_gems": metadata.get("hidden_gems", ""),
                    "transport": metadata.get("transport_tips", "Local transit"),
                    "local_tips": metadata.get("local_tips", ""),
                    "duration": metadata.get("recommended_duration", "2 hours"),
                    "best_time": metadata.get("best_visiting_time", "morning"),
                    "pricing": metadata.get("budget_category", "budget"),
                })
                if entity["destination"].lower() == destination.lower():
                    entities.append(entity)
            if entities:
                return entities
    except Exception:
        pass
    return [
        place_entity(item)
        for item in retrieve_travel_documents(destination, interests, n=n)
        if item.get("location", "").lower() == destination.lower()
    ]

def retrieve_travel_context(destination: str, interests: list, n: int = 8) -> str:
    """Legacy compatibility: return compact structured entities, never prose."""
    return json.dumps(retrieve_place_entities(destination, interests, n=n), ensure_ascii=False)
