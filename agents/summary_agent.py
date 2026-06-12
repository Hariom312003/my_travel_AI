"""Summary Generation Agent - premium user summary travel guide."""
from __future__ import annotations

from agents.common import invoke_text
from agents.rewards_agent import rewards_to_text

SYSTEM_PROMPT = """You are a practical travel guide assistant.
Generate a clear, day-by-day travel guide summary from the provided itinerary, budget, and card rewards.
Follow these guidelines strictly:
1. Do NOT output JSON, debug logs, or internal technical reasoning.
2. Structure the guide day-by-day (e.g., DAY 1, DAY 2, etc.).
3. Keep descriptions simple, direct, and practical. Use simple English and short sentences. Avoid flowery, commercial, or tourism blog-like adjectives (do NOT write phrases like "enchanting cedar forests", "breathtaking journey", or "evocative paragraphs").
4. State exactly what to visit, when to visit, and how long to spend there. (e.g., "Visit Hadimba Temple in the morning and spend about 2 hours exploring the area.")
5. Include a clear 'Estimated daily spend' section at the end of each day or at the end of the guide.
6. Provide a summary of how to optimize credit card rewards (e.g., using specific cards for hotel/food spends).
7. Target word count is 200 to 400 words. Keep it highly readable for normal users, international travelers, and recruiters."""

def _fallback_summary(itinerary: dict | str, structured_query: dict, budget: dict, rewards: dict | str, behavior_profile: dict | None = None) -> str:
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
    
    summary_text = (
        f"Your {days}-day {destination} plan is paced for {structured_query.get('travel_style', 'balanced')} travel "
        f"with {structured_query.get('food_preference', 'local')} food. The core route uses: {places}.\n\n"
        f"Estimated trip cost is ₹{budget.get('grand_total', 'N/A')} with an average of "
        f"₹{budget.get('per_day_average', 'N/A')} per day. Reward estimate: "
        f"{reward_text.splitlines()[-1] if reward_text else 'Use the best cashback card available.'}\n\n"
        "Verify local timings, weather, permits, and live offers before booking."
    )
    
    if behavior_profile:
        reasons = []
        if behavior_profile.get("pace") == "slow":
            reasons.append("✓ User prefers slow travel")
        if behavior_profile.get("food_style") == "cafes":
            reasons.append("✓ User prefers cafes")
        if "adventure" in behavior_profile.get("avoid_categories", []):
            reasons.append("✓ User avoids adventure")
        if "crowded" in behavior_profile.get("avoid_categories", []) or behavior_profile.get("crowd_preference") == "avoid_crowds":
            reasons.append("✓ User avoids crowds")
        if reasons:
            summary_text += "\n\nThis plan was personalized because:\n\n" + "\n\n".join(reasons)
            
    return summary_text


def run_summary_agent(itinerary: dict | str, structured_query: dict, budget: dict, rewards: dict | str, behavior_profile: dict | None = None) -> str:
    dest = structured_query.get("destination", "your destination")
    days = structured_query.get("days", 3)
    style = structured_query.get("travel_style", "moderate")
    food = structured_query.get("food_preference", "local")
    cards = structured_query.get("cards", [])
    
    prompt = f"""
Destination: {dest}
Days: {days}
Travel Style: {style}
Food Preference: {food}
User's Cards: {cards}
Budget breakdown: {budget}
Rewards analysis: {rewards}
Behavior Profile: {behavior_profile or {}}

Itinerary details:
{itinerary}
"""
    try:
        summary = invoke_text(SYSTEM_PROMPT, prompt, temperature=0.3)
        if summary and len(summary.strip()) > 100:
            return summary
    except Exception:
        pass
    return _fallback_summary(itinerary, structured_query, budget, rewards, behavior_profile)
