"""Shared destination and place registry.

This module is intentionally dependency-free within the agents package. It is
safe for RAG, memory, planner, and validator modules to import from here without
creating circular imports.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

DATA_PATH = os.path.join(os.path.dirname(__file__), "../rag_data/travel_data.json")

DESTINATION_ALIASES = {
    "manali": "Manali",
    "goa": "Goa",
    "jaipur": "Jaipur",
    "kullu": "Kullu",
    "varanasi": "Varanasi",
}


@lru_cache(maxsize=1)
def load_travel_data() -> tuple[dict[str, Any], ...]:
    with open(DATA_PATH, encoding="utf-8") as f:
        return tuple(json.load(f))


def normalize_destination(destination: str) -> str:
    value = (destination or "").strip()
    if not value:
        return ""
    alias = DESTINATION_ALIASES.get(value.lower())
    if alias:
        return alias
    for item in load_travel_data():
        if item.get("location", "").lower() == value.lower():
            return item["location"]
    return value[:1].upper() + value[1:]


def valid_destinations() -> dict[str, list[str]]:
    destinations: dict[str, list[str]] = {}
    for item in load_travel_data():
        destinations.setdefault(item["location"], []).append(item["place"])
    try:
        from agents.demo_data import DEMO_ATTRACTIONS
        for dest, places in DEMO_ATTRACTIONS.items():
            normalized_dest = normalize_destination(dest)
            dest_places = destinations.setdefault(normalized_dest, [])
            for p in places:
                if p not in dest_places:
                    dest_places.append(p)
    except Exception:
        pass
    return {destination: sorted(set(places)) for destination, places in destinations.items()}


VALID_DESTINATIONS = valid_destinations()


def known_places_by_destination() -> dict[str, set[str]]:
    return {destination: set(places) for destination, places in VALID_DESTINATIONS.items()}


def known_place_names(exclude_destination: str | None = None) -> set[str]:
    exclude = normalize_destination(exclude_destination or "").lower()
    names: set[str] = set()
    for destination, places in VALID_DESTINATIONS.items():
        if exclude and destination.lower() == exclude:
            continue
        names.add(destination)
        names.update(places)
    return {name for name in names if name}


def allowed_places_for_destination(destination: str) -> list[str]:
    return list(VALID_DESTINATIONS.get(normalize_destination(destination), []))
