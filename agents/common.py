"""Shared utilities for model calls, JSON handling, and deterministic fallbacks."""
from __future__ import annotations

import json
import os
import re
from typing import Any, Iterable

from agents.llm import generate


def strip_json_markdown(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"(\{.*\}|\[.*\])", text, flags=re.DOTALL)
    return match.group(1).strip() if match else text


def invoke_text(system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str | None:
    try:
        return generate(user_prompt, system_prompt=system_prompt, temperature=temperature)
    except Exception:
        return None


def invoke_json(system_prompt: str, user_prompt: str, fallback: Any, temperature: float = 0.1) -> Any:
    text = invoke_text(system_prompt, user_prompt, temperature=temperature)
    if not text:
        return fallback
    try:
        return json.loads(strip_json_markdown(text))
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
