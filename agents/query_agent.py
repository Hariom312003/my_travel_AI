"""Query Structuring Agent - converts natural language into structured travel intent."""
from __future__ import annotations

import re

from agents.common import as_list, first_present, invoke_json, safe_int

SYSTEM_PROMPT = """You are a travel query parser. Extract structured travel intent from user input.
Return ONLY valid JSON with these keys:
{
  "destination": string,
  "days": integer,
  "budget": integer (INR),
  "travel_style": string (relaxed/moderate/fast-paced),
  "food_preference": string (local/continental/veg/non-veg/mixed),
  "cards": [list of card names],
  "interests": [list of interests],
  "accommodation": string (budget/mid-range/luxury),
  "travel_pace": string (slow/medium/fast),
  "avoid": [things to avoid if mentioned],
  "travellers": integer,
  "source_city": string or null
}
If a value is not mentioned, use sensible defaults. Normalize vague preferences into durable travel behavior.
Return ONLY JSON, no explanation."""


DESTINATIONS = ["Manali", "Goa", "Jaipur", "Kullu", "Udaipur", "Rishikesh", "Shimla", "Kerala", "Mumbai", "Delhi"]
CARDS = ["SBI", "HDFC", "ICICI", "Axis", "Amex", "Kotak", "IDFC", "Amazon Pay", "Millennia", "Regalia", "SmartBuy"]
INTEREST_KEYWORDS = {
    "scenic": ["scenic", "view", "views", "mountain", "sunset", "photography"],
    "local food": ["local food", "street food", "cuisine", "food", "seafood", "cafes", "cafe"],
    "hidden gems": ["hidden", "offbeat", "less crowded", "quiet"],
    "adventure": ["adventure", "rafting", "paragliding", "trek", "water sports", "scuba"],
    "culture": ["culture", "heritage", "temple", "fort", "museum", "history"],
    "shopping": ["shopping", "market", "bazaar", "souvenir"],
    "nightlife": ["nightlife", "club", "bar", "party"],
    "nature": ["nature", "wildlife", "waterfall", "forest", "beach"],
}


def _fallback_parse(user_query: str) -> dict:
    text = user_query.lower()
    destination = first_present(DESTINATIONS, user_query) or "Goa"
    days_match = re.search(r"(\d+)\s*(?:day|days|d)\b", text)
    budget_match = re.search(r"(?:under|below|budget|within|for)?\s*(?:rs\.?|inr|₹)?\s*([0-9][0-9,]{3,})", text)
    cards = [card for card in CARDS if card.lower() in text]
    interests = [
        label
        for label, keywords in INTEREST_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]
    avoid = []
    for pattern in [r"avoid ([^.]+)", r"remove ([^.]+)", r"skip ([^.]+)", r"without ([^.]+)"]:
        match = re.search(pattern, text)
        if match:
            avoid.extend([v.strip() for v in re.split(r",| and ", match.group(1)) if v.strip()])
    relaxed = any(v in text for v in ["relaxed", "slow", "easy", "less hectic", "quiet"])
    fast = any(v in text for v in ["packed", "fast", "cover more", "hectic"])
    accommodation = "luxury" if "luxury" in text else "mid-range" if "mid" in text or "comfortable" in text else "budget"
    return {
        "destination": destination,
        "days": safe_int(days_match.group(1), 3) if days_match else 3,
        "budget": safe_int(budget_match.group(1), 20000) if budget_match else 20000,
        "travel_style": "relaxed" if relaxed else "fast-paced" if fast else "moderate",
        "food_preference": "local" if any(v in text for v in ["local", "street food", "seafood", "cuisine"]) else "mixed",
        "cards": cards,
        "interests": interests or ["scenic", "local food"],
        "accommodation": accommodation,
        "travel_pace": "slow" if relaxed else "fast" if fast else "medium",
        "avoid": avoid,
        "travellers": 1,
        "source_city": None,
    }


def _normalize(parsed: dict, fallback: dict) -> dict:
    parsed = {**fallback, **(parsed or {})}
    parsed["days"] = max(1, min(safe_int(parsed.get("days"), fallback["days"]), 21))
    parsed["budget"] = max(1000, safe_int(parsed.get("budget"), fallback["budget"]))
    parsed["cards"] = as_list(parsed.get("cards"))
    parsed["interests"] = as_list(parsed.get("interests")) or fallback["interests"]
    parsed["avoid"] = as_list(parsed.get("avoid"))
    parsed["travellers"] = max(1, safe_int(parsed.get("travellers"), 1))
    parsed["travel_style"] = parsed.get("travel_style") or fallback["travel_style"]
    parsed["travel_pace"] = parsed.get("travel_pace") or fallback["travel_pace"]
    parsed["food_preference"] = parsed.get("food_preference") or fallback["food_preference"]
    parsed["accommodation"] = parsed.get("accommodation") or fallback["accommodation"]
    return parsed

def run_query_agent(user_query: str) -> dict:
    fallback = _fallback_parse(user_query)
    parsed = invoke_json(SYSTEM_PROMPT, user_query, fallback=fallback, temperature=0)
    return _normalize(parsed, fallback)
