"""Summary Generation Agent - concise deterministic user summary."""
from __future__ import annotations

from agents.rewards_agent import rewards_to_text

SYSTEM_PROMPT = "Internal only: deterministic summary. No new place generation."

def _fallback_summary(itinerary: dict | str, structured_query: dict, budget: dict, rewards: dict | str) -> str:
    destination = structured_query.get("destination", "your destination")
    days = structured_query.get("days", 3)
    place_names = []
    if isinstance(itinerary, dict):
        for day in itinerary.get("days", []) or []:
            for slot in ["morning", "afternoon", "evening"]:
                for item in day.get(slot, []) or []:
                    if item.get("location") and item["location"] not in place_names:
                        place_names.append(item["location"])
    reward_text = rewards_to_text(rewards) if isinstance(rewards, dict) else rewards
    places = ", ".join(place_names[:6]) if place_names else destination
    return (
        f"Your {days}-day {destination} plan is paced for {structured_query.get('travel_style', 'balanced')} travel "
        f"with {structured_query.get('food_preference', 'local')} food. The core route uses: {places}.\n\n"
        f"Estimated trip cost is ₹{budget.get('grand_total', 'N/A')} with an average of "
        f"₹{budget.get('per_day_average', 'N/A')} per day. Reward estimate: "
        f"{reward_text.splitlines()[-1] if reward_text else 'Use the best cashback card available.'}\n\n"
        "Verify local timings, weather, permits, and live offers before booking."
    )


def run_summary_agent(itinerary: dict | str, structured_query: dict, budget: dict, rewards: dict | str) -> str:
    return _fallback_summary(itinerary, structured_query, budget, rewards)
