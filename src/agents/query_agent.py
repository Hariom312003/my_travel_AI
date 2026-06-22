"""Query Structuring Agent - converts natural language into structured travel intent."""
from __future__ import annotations

import re

from agents.common import as_list, first_present, invoke_json, safe_int

SYSTEM_PROMPT = """You are an expert travel query parsing LLM. Your task is to extract structured travel intent from natural language user input.
You must infer sensible default values for any missing details based on the context.

You must return ONLY a valid JSON object with the following keys:
{
  "destination": string (the target destination city/region, e.g. "Bangalore"),
  "duration_days": integer (duration of trip, defaults to 3 if not specified),
  "budget": integer (estimated total budget in INR, e.g. 20000),
  "travel_style": string (balanced, relaxed, fast-paced, budget, luxury),
  "interests": list of strings (e.g. ["scenic", "cafes", "culture"]),
  "constraints": list of strings (things to avoid or limits, e.g. ["avoid adventure", "no crowded areas"]),
  "dietary_preferences": string (local, continental, veg, non-veg, mixed),
  "transport_preferences": string (local transport, private cab, rental bike, flight, etc.)
}

Ensure all fields are filled, inferring them intelligently from the query.
Do not output any explanation or markdown formatting, output ONLY JSON."""


DESTINATIONS = ["Manali", "Goa", "Jaipur", "Kullu", "Udaipur", "Rishikesh", "Shimla", "Kerala", "Mumbai", "Delhi", "Bangalore", "Iceland", "Vietnam", "Peru"]
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
    text = user_query.strip()
    words = text.split()
    
    destination = ""
    clean_text = re.sub(r"[.,\/#!$%\^&\*;:{}=\-_`~()?\"']", " ", user_query)
    
    stopwords = {
        "plan", "book", "need", "a", "an", "the", "day", "days", "trip", "under", "budget", "with", "have", "card", "cards", 
        "i", "want", "to", "visit", "go", "for", "inr", "rs", "travel", "my", "our", "family", "vacation", 
        "holiday", "weekend", "preference", "preferences", "avoid", "likes", "dislikes", "like", "dislike",
        "in", "of", "on", "at", "by", "from", "and", "or", "but", "some", "any", "all", "getaway", "tour",
        "honeymoon", "duration", "under", "below", "above", "around", "near", "about", "days", "day",
        "night", "nights", "people", "person", "budget", "cost", "price", "rupees", "rupee", "k", "lakh", "lakhs", "usd", "euro", "euros",
        "make", "show", "get", "give", "create", "generate", "build", "prepare", "suggest", "find", "search", "provide",
        "itinerary", "destination", "luxury", "moderate", "relaxed", "accommodation", "hotels", "hotel", "stay", "flight", "flights",
        "week", "weeks"
    }

    def validate_candidate(candidate: str) -> str:
        parts = candidate.strip().split()
        valid_parts = []
        for p in parts:
            p_lower = p.lower()
            if p_lower == "of":
                valid_parts.append(p)
                continue
            if p_lower in stopwords:
                break
            if p_lower.isdigit():
                break
            if len(p_lower) <= 1:
                continue
            valid_parts.append(p)
        if valid_parts:
            result_parts = []
            for idx, vp in enumerate(valid_parts):
                if vp.lower() == "of" and idx > 0 and idx < len(valid_parts) - 1:
                    result_parts.append("of")
                else:
                    result_parts.append(vp.title())
            return " ".join(result_parts)
        return ""

    # 1. Match specific travel destination preposition patterns (highest confidence)
    patterns = [
        r"\b(?:trip to|travel to|visit to|go to|plan a trip to|destination is|planning a trip to|vacation to|holiday in|trip in|vacation in|honeymoon in|honeymoon to|trip for|vacation for|plan for|itinerary for|trip plan for|trip planner for|plan a trip for|days trip for|day trip for|days in|day in|days to|day to)\s+([a-zA-Z\s]+)",
        r"\b(?:visit|go|explore|plan)\s+([a-zA-Z\s]+)"
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, clean_text, re.IGNORECASE):
            candidate = match.group(1).strip()
            validated = validate_candidate(candidate)
            if validated:
                destination = validated
                break
        if destination:
            break

    # 2. Match "<destination> trip", "<destination> vacation", "<destination> tour"
    if not destination:
        match = re.search(
            r"([a-zA-Z\s]+?)\s+(?:trip|vacation|tour|holiday|getaway|adventure|photography|food|itinerary|plan|planner)", 
            clean_text, 
            re.IGNORECASE
        )
        if match:
            candidate_words = match.group(1).strip().split()
            dest_parts = []
            for w in reversed(candidate_words):
                w_lower = w.lower()
                if w_lower == "of":
                    dest_parts.insert(0, w)
                    continue
                if w_lower in stopwords or w_lower.isdigit():
                    break
                dest_parts.insert(0, w)
            if dest_parts:
                validated = " ".join(dest_parts)
                # Capitalize nicely
                result_parts = []
                for idx, vp in enumerate(validated.split()):
                    if vp.lower() == "of" and idx > 0 and idx < len(validated.split()) - 1:
                        result_parts.append("of")
                    else:
                        result_parts.append(vp.title())
                destination = " ".join(result_parts)

    # 3. Search in user query for any known destinations
    if not destination:
        for d in DESTINATIONS:
            if d.lower() in clean_text.lower():
                destination = d
                break

    # 4. Last resort: first word that is not a standard query word/number
    if not destination:
        for word in clean_text.split():
            word_clean = re.sub(r"[^a-zA-Z]", "", word)
            if word_clean.lower() not in stopwords and len(word_clean) > 2:
                destination = word_clean.title()
                break
                
    if not destination:
        destination = "Destination"
        
    days_match = re.search(r"(\d+)\s*-?\s*(?:day|days|d)\b", text)
    budget_match = re.search(r"(?:under|below|budget|within|for)?\s*(?:rs\.?|inr|₹)?\s*([0-9][0-9,]{3,})", text)
    cards = [card for card in CARDS if card.lower() in text]
    interests = [
        label
        for label, keywords in INTEREST_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]
    constraints = []
    for pattern in [r"avoid ([^.]+)", r"remove ([^.]+)", r"skip ([^.]+)", r"without ([^.]+)"]:
        match = re.search(pattern, text)
        if match:
            constraints.extend([v.strip() for v in re.split(r",| and ", match.group(1)) if v.strip()])
    relaxed = any(v in text for v in ["relaxed", "slow", "easy", "less hectic", "quiet"])
    fast = any(v in text for v in ["packed", "fast", "cover more", "hectic"])
    accommodation = "luxury" if "luxury" in text else "mid-range" if "mid" in text or "comfortable" in text else "budget"
    return {
        "destination": destination,
        "duration_days": safe_int(days_match.group(1), 3) if days_match else 3,
        "budget": safe_int(budget_match.group(1), 20000) if budget_match else 20000,
        "travel_style": "relaxed" if relaxed else "fast-paced" if fast else "moderate",
        "interests": interests or ["scenic", "local food"],
        "constraints": constraints,
        "dietary_preferences": "local" if any(v in text for v in ["local", "street food", "seafood", "cuisine"]) else "mixed",
        "transport_preferences": "local transport",
        "cards": cards,
        "accommodation": accommodation,
    }


def _normalize(parsed: dict, fallback: dict) -> dict:
    parsed = {**fallback, **(parsed or {})}
    duration_days = max(1, min(safe_int(parsed.get("duration_days") or parsed.get("days"), fallback["duration_days"]), 21))
    budget = max(1000, safe_int(parsed.get("budget"), fallback["budget"]))
    interests = as_list(parsed.get("interests")) or fallback["interests"]
    constraints = as_list(parsed.get("constraints") or parsed.get("avoid") or parsed.get("constraints"))
    dietary_preferences = parsed.get("dietary_preferences") or parsed.get("food_preference") or fallback["dietary_preferences"]
    transport_preferences = parsed.get("transport_preferences") or parsed.get("transport_style") or fallback["transport_preferences"]
    travel_style = parsed.get("travel_style") or fallback["travel_style"]
    
    res = {
        "destination": parsed.get("destination") or fallback["destination"],
        "duration_days": duration_days,
        "budget": budget,
        "travel_style": travel_style,
        "interests": interests,
        "constraints": constraints,
        "dietary_preferences": dietary_preferences,
        "transport_preferences": transport_preferences,
        
        # Legacy/compatibility keys
        "days": duration_days,
        "avoid": constraints,
        "food_preference": dietary_preferences,
        "transport_style": transport_preferences,
        "travel_pace": "slow" if "relaxed" in travel_style.lower() or "slow" in travel_style.lower() else "fast" if "fast" in travel_style.lower() else "medium",
        "accommodation": parsed.get("accommodation") or ("luxury" if "luxury" in travel_style.lower() else "budget" if (budget / duration_days) < 4000 else "mid-range"),
        "travellers": max(1, safe_int(parsed.get("travellers"), 1)),
        "source_city": parsed.get("source_city", None),
        "cards": as_list(parsed.get("cards") or [])
    }
    return res

def run_query_agent(user_query: str) -> dict:
    from monitoring.logger import logger
    logger.info("[Query Agent] Entering agent")
    logger.info("[Query Agent] Destination received: None")
    fallback = _fallback_parse(user_query)
    parsed = invoke_json(SYSTEM_PROMPT, user_query, fallback=fallback, temperature=0)
    result = _normalize(parsed, fallback)
    dest = result.get("destination", "")
    logger.info(f"[Query Agent] Destination returned: {dest}")
    logger.info("[Query Agent] Leaving agent")
    return result
