"""Shared utilities for model calls, JSON handling, and deterministic fallbacks."""
from __future__ import annotations

import json
import os
import re
from typing import Any, Iterable

from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def llm_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def get_llm(temperature: float = 0.2) -> ChatOpenAI | None:
    if not llm_available():
        return None
    try:
        return ChatOpenAI(model=DEFAULT_MODEL, temperature=temperature, timeout=60, max_retries=2)
    except Exception:
        return None


def strip_json_markdown(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"(\{.*\}|\[.*\])", text, flags=re.DOTALL)
    return match.group(1).strip() if match else text


def invoke_text(system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str | None:
    llm = get_llm(temperature=temperature)
    if not llm:
        return None
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    return response.content


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
