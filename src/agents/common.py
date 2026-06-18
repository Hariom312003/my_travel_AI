"""Shared utilities for model calls, JSON handling, and deterministic fallbacks."""
from __future__ import annotations

import json
import os
import re
from typing import Any, Iterable

from agents.llm import generate


def strip_json_markdown(text: str) -> str:
    text = text.strip()
    # Remove markdown code block markers
    text = re.sub(r"^```(?:json)?\n", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n```$", "", text)
    text = re.sub(r"```$", "", text)
    text = text.strip()
    
    # Find JSON block
    match = re.search(r"(\{.*\}|\[.*\])", text, flags=re.DOTALL)
    if match:
        text = match.group(1).strip()
        
    # Repair trailing commas before closing braces/brackets
    text = re.sub(r",\s*([\]}])", r"\1", text)
    return text


def invoke_text(system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
    return generate(user_prompt, system_prompt=system_prompt, temperature=temperature)


def invoke_json(system_prompt: str, user_prompt: str, fallback: Any, temperature: float = 0.1) -> Any:
    try:
        text = invoke_text(system_prompt, user_prompt, temperature=temperature)
    except Exception as e:
        # Propagate configuration errors immediately
        if "No AI provider configured" in str(e) or "LLM unavailable" in str(e):
            raise e
        return fallback
        
    if not text:
        return fallback
    
    cleaned = strip_json_markdown(text)
    try:
        return json.loads(cleaned)
    except Exception:
        try:
            # Try parsing with single quote replaced by double quote
            repaired = re.sub(r"\'", '"', cleaned)
            return json.loads(repaired)
        except Exception:
            return fallback


def as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v not in ("", None)]
    if isinstance(value, str):
        return [v.strip() for v in re.split(r",|/| and ", value) if v.strip()]
    return [value]


def safe_int(value: Any, default: int) -> int:
    try:
        return int(float(str(value).replace(",", "").replace("₹", "").strip()))
    except Exception:
        return default


def slug(value: str, max_len: int = 48) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip())[:max_len].strip("_")
    return clean or "anonymous"


def first_present(values: Iterable[str], text: str) -> str | None:
    lower = text.lower()
    for value in values:
        if value.lower() in lower:
            return value
    return None


def save_trip_state_to_file(user_id: str, state: dict):
    try:
        import json
        import os
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        scratch_dir = os.path.join(root_dir, "scratch")
        os.makedirs(scratch_dir, exist_ok=True)
        path = os.path.join(scratch_dir, f"trip_state_{user_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Error saving trip state to file: {e}")


def load_trip_state_from_file(user_id: str) -> dict | None:
    try:
        import json
        import os
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(root_dir, "scratch", f"trip_state_{user_id}.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading trip state from file: {e}")
    return None

