"""Budget Estimation Agent - realistic Indian travel cost breakdown."""
from __future__ import annotations

from agents.common import invoke_json, safe_int

SYSTEM_PROMPT = """You are an expert at estimating realistic Indian travel budgets.

Return ONLY valid JSON with this structure:
{
  "accommodation": {"total": int, "per_night": int, "type": string},
  "food": {"total": int, "per_day": int, "breakdown": string},
  "transport": {"total": int, "breakdown": string},
  "activities": {"total": int, "breakdown": string},
  "shopping_misc": {"total": int},
  "contingency": {"total": int},
  "grand_total": int,
  "per_day_average": int,
  "budget_status": string (within_budget/over_budget/under_budget),
  "savings_tips": [list of 3 tips]
}

Use realistic 2026 Indian prices. Return ONLY JSON."""

def _fallback_budget(structured_query: dict) -> dict:
    days = max(1, safe_int(structured_query.get("days"), 3))
    travellers = max(1, safe_int(structured_query.get("travellers"), 1))
    style = structured_query.get("accommodation", "budget")
    per_night = {"budget": 1800, "mid-range": 3500, "luxury": 8000}.get(style, 2500)
    food_per_day = 900 if structured_query.get("food_preference") == "local" else 1200
    transport_per_day = 1200 if structured_query.get("travel_pace") == "slow" else 1600
    activity_per_day = 1300 if "adventure" in structured_query.get("interests", []) else 800
    accommodation = per_night * max(days - 1, 1)
    food = food_per_day * days * travellers
    transport = transport_per_day * days
    activities = activity_per_day * days * travellers
    shopping_misc = 1200 * travellers
    contingency = int((accommodation + food + transport + activities + shopping_misc) * 0.1)
    grand_total = accommodation + food + transport + activities + shopping_misc + contingency
    requested = safe_int(structured_query.get("budget"), grand_total)
    return {
        "accommodation": {"total": accommodation, "per_night": per_night, "type": style},
        "food": {"total": food, "per_day": food_per_day * travellers, "breakdown": "Local meals, cafes, snacks, and drinking water."},
        "transport": {"total": transport, "breakdown": "Local cabs/autos, short transfers, and inter-area movement."},
        "activities": {"total": activities, "breakdown": "Entry tickets, guide fees, adventure or cultural activities."},
        "shopping_misc": {"total": shopping_misc},
        "contingency": {"total": contingency},
        "grand_total": grand_total,
        "per_day_average": int(grand_total / days),
        "budget_status": "within_budget" if grand_total <= requested else "over_budget",
        "savings_tips": [
            "Book stays near the main activity cluster to reduce cab costs.",
            "Use local eateries for most meals and reserve cafes for one meal a day.",
            "Pre-book paid activities online only after checking weather and cancellation rules.",
        ],
    }


def run_budget_agent(structured_query: dict, itinerary: dict | str) -> dict:
    fallback = _fallback_budget(structured_query)
    prompt = f"""
Estimate budget for:
- Destination: {structured_query.get('destination')}
- Days: {structured_query.get('days')}
- Total Budget: ₹{structured_query.get('budget')} INR
- Accommodation Type: {structured_query.get('accommodation', 'budget')}
- Travel Style: {structured_query.get('travel_style')}
- Number of travellers: 1

Based on this itinerary:
{str(itinerary)[:2500]}

Calculate realistic costs:"""

    budget = invoke_json(SYSTEM_PROMPT, prompt, fallback=fallback, temperature=0.15)
    return budget if isinstance(budget, dict) and budget.get("grand_total") else fallback
