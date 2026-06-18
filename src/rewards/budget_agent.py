"""Budget Estimation Agent - realistic Indian travel cost breakdown."""
from __future__ import annotations

from agents.common import invoke_json, safe_int

SYSTEM_PROMPT = """You are an expert at estimating realistic travel budgets.
Estimate a realistic budget for a trip based on destination, duration, target budget, and the itinerary.

Return ONLY valid JSON with this structure:
{
  "hotel_cost": integer (estimated total hotel/accommodation cost in INR),
  "food_cost": integer (estimated total food and dining cost in INR),
  "transport_cost": integer (estimated total local transport cost in INR),
  "activity_cost": integer (estimated total sightseeing entry/activity cost in INR),
  "misc_cost": integer (estimated total miscellaneous/emergency/shopping cost in INR),
  "total_cost": integer (sum of all the costs above in INR),
  "savings_tips": list of strings (exactly 3 practical savings tips)
}

Use realistic prices reflecting the actual destination. Return ONLY JSON."""

def _fallback_budget(structured_query: dict) -> dict:
    days = max(1, safe_int(structured_query.get("days"), 3))
    travellers = max(1, safe_int(structured_query.get("travellers"), 1))
    style = structured_query.get("accommodation", "budget")
    per_night = {"budget": 1800, "mid-range": 3500, "luxury": 8000}.get(style, 2500)
    food_per_day = 900 if structured_query.get("food_preference") == "local" else 1200
    transport_per_day = 1200 if structured_query.get("travel_pace") == "slow" else 1600
    activity_per_day = 1300 if "adventure" in structured_query.get("interests", []) else 800
    
    hotel_cost = per_night * max(days - 1, 1)
    food_cost = food_per_day * days * travellers
    transport_cost = transport_per_day * days
    activity_cost = activity_per_day * days * travellers
    misc_cost = int(days * 500 * travellers)
    total_cost = hotel_cost + food_cost + transport_cost + activity_cost + misc_cost
    
    return {
        "hotel_cost": hotel_cost,
        "food_cost": food_cost,
        "transport_cost": transport_cost,
        "activity_cost": activity_cost,
        "misc_cost": misc_cost,
        "total_cost": total_cost,
        "savings_tips": [
            "Book stays near the main activity cluster to reduce cab costs.",
            "Use local eateries for most meals and reserve cafes for one meal a day.",
            "Pre-book paid activities online only after checking weather and cancellation rules."
        ]
    }

def run_budget_agent(structured_query: dict, itinerary: dict | str) -> dict:
    from monitoring.logger import logger
    dest = structured_query.get("destination", "")
    logger.info("[Budget Agent] Entering agent")
    logger.info(f"[Budget Agent] Destination received: {dest}")
    fallback_data = _fallback_budget(structured_query)
    
    # Check if we are in Mock/Test mode
    from agents.llm import get_llm
    is_mock = False
    try:
        provider, _ = get_llm()
        if provider == "Mock":
            is_mock = True
    except Exception:
        pass

    prompt = f"""
Estimate budget for:
- Destination: {structured_query.get('destination')}
- Days: {structured_query.get('days')}
- Target Budget: ₹{structured_query.get('budget')} INR
- Accommodation Type: {structured_query.get('accommodation', 'budget')}
- Travel Style: {structured_query.get('travel_style')}

Based on this itinerary:
{str(itinerary)[:2500]}

Calculate realistic costs in INR:"""

    try:
        from monitoring.logger import logger
        budget = invoke_json(SYSTEM_PROMPT, prompt, fallback=None, temperature=0.15)
        if not isinstance(budget, dict) or not budget.get("total_cost"):
            logger.warning("LLM returned invalid budget response, using fallback budget.")
            budget = fallback_data
    except Exception as e:
        from monitoring.logger import logger
        if "No AI provider configured" in str(e) or "LLM unavailable" in str(e):
            raise e
        logger.error(f"Budget agent failed: {e}. Using fallback budget.")
        budget = fallback_data
        
    # Mapping to sustain compatibility with the UI and other agents
    days = max(1, safe_int(structured_query.get("days"), 3))
    limit = safe_int(structured_query.get("budget"), 20000)
    
    hotel_cost = budget.get("hotel_cost", fallback_data["hotel_cost"])
    food_cost = budget.get("food_cost", fallback_data["food_cost"])
    transport_cost = budget.get("transport_cost", fallback_data["transport_cost"])
    activity_cost = budget.get("activity_cost", fallback_data["activity_cost"])
    misc_cost = budget.get("misc_cost", fallback_data.get("misc_cost", 0))
    total_cost = budget.get("total_cost", fallback_data["total_cost"])
    
    mapped_budget = {
        "hotel_cost": hotel_cost,
        "food_cost": food_cost,
        "transport_cost": transport_cost,
        "activity_cost": activity_cost,
        "misc_cost": misc_cost,
        "total_cost": total_cost,
        "grand_total": total_cost,
        
        # Compatibility UI fields
        "accommodation": {
            "total": hotel_cost,
            "per_night": int(hotel_cost / max(1, days - 1)),
            "type": structured_query.get("accommodation", "mid-range"),
            "breakdown": f"Hotel stay of {max(1, days - 1)} nights."
        },
        "food": {
            "total": food_cost,
            "per_day": int(food_cost / days),
            "breakdown": "Meals, local food, and cafe visits."
        },
        "transport": {
            "total": transport_cost,
            "breakdown": "Local transit and movement."
        },
        "activities": {
            "total": activity_cost,
            "breakdown": "Sightseeing entry and experiences."
        },
        "misc": {
            "total": misc_cost,
            "breakdown": "Shopping, emergency, and miscellaneous expenses."
        },
        "per_day_average": int(total_cost / days),
        "budget_status": "within_budget" if total_cost <= limit else "over_budget",
        "savings_tips": budget.get("savings_tips", fallback_data["savings_tips"])
    }
    logger.info(f"[Budget Agent] Destination returned: {dest}")
    logger.info("[Budget Agent] Leaving agent")
    return mapped_budget
