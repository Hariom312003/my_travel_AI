"""Summary Generation Agent - premium user summary travel guide."""
from __future__ import annotations

from agents.common import invoke_text
from rewards.rewards_agent import rewards_to_text

SYSTEM_PROMPT = """You are a professional travel consultant. Your task is to generate a comprehensive, highly authentic travel guide based on the provided itinerary, budget, and cards/rewards.

Your guide must include the following sections exactly:
1. TRIP OVERVIEW: A concise summary of the trip goals, destinations covered, and overall style.
2. DAILY NARRATIVE: A detailed, day-by-day narrative of the itinerary (e.g. Day 1, Day 2). Write in realistic, engaging prose describing the flow and pacing of the day. Do NOT use bullet points for the main itinerary.
3. LOGISTICS ADVICE: Critical transit tips, optimal transport modes, and timing recommendations.
4. BUDGET GUIDANCE: Realistic spending expectations, daily costs, and saving opportunities (including credit card rewards).
5. LOCAL TIPS: Dining recommendations, hidden gems, crowd management, and cultural norms.
6. SAFETY NOTES: Crucial safety guidance, weather considerations, emergency awareness, and packing warnings.

CRITICAL INSTRUCTIONS:
- You must write in an objective, professional consultant tone.
- Do NOT generate marketing fluff.
- Do NOT use any of these prohibited words: "curated", "immersive", "premium", "breathtaking", "magical", "luxury escape", "handcrafted".
- Return your response in clean markdown."""

def _fallback_summary(itinerary: dict | str, structured_query: dict, budget: dict, rewards: dict | str, behavior_profile: dict | None = None) -> str:
    destination = structured_query.get("destination", "your destination")
    days = structured_query.get("days", 3)
    
    # Start building the summary guide with the required sections
    guide = f"# Travel Guide for {destination}\n\n"
    
    guide += "## TRIP OVERVIEW\n"
    guide += f"This is a professional {days}-day itinerary for {destination} tailored to your preferences.\n\n"
    
    guide += "## DAILY NARRATIVE\n"
    if isinstance(itinerary, dict) and "days" in itinerary:
        for day in itinerary.get("days", []):
            day_num = day.get("day", "?")
            theme = day.get("theme", f"Exploring {destination}")
            guide += f"Day {day_num} — {theme}\n"
            
            m_items = day.get("morning", [])
            a_items = day.get("afternoon", [])
            e_items = day.get("evening", [])
            
            m_text = f"explore {m_items[0].get('location')}" if m_items else "start morning exploration"
            a_text = f"visit {a_items[0].get('location')}" if a_items else "sightsee in the afternoon"
            e_text = f"relax at {e_items[0].get('location')}" if e_items else "enjoy the evening views"
            
            narrative = f"Your day begins in the morning as you set out to {m_text}. After sampling some local culinary options for lunch, you will head over to {a_text} for a scenic afternoon. As the sun begins to set, wrap up your day with a visit to {e_text}."
            guide += f"{narrative}\n\n"
    else:
        guide += str(itinerary)
        guide += "\n\n"
        
    guide += "## LOGISTICS ADVICE\n"
    guide += "Plan transit times around traffic peaks. Use local cabs or auto-rickshaws for short distances and metro/trains where available.\n\n"
    
    guide += "## BUDGET GUIDANCE\n"
    avg_spend = budget.get("per_day_average", "N/A")
    total_spend = budget.get("grand_total", "N/A")
    guide += f"* Daily budget average: ₹{avg_spend}\n"
    guide += f"* Grand total: ₹{total_spend}\n"
    reward_text = rewards_to_text(rewards) if isinstance(rewards, dict) else str(rewards)
    if reward_text:
        guide += f"* Rewards tips: {reward_text}\n"
    guide += "\n"
    
    guide += "## LOCAL TIPS\n"
    guide += "Drink bottled water, try local specialties in busy diners, and plan temple/heritage site visits early in the morning.\n\n"
    
    guide += "## SAFETY NOTES\n"
    guide += "Keep copies of credentials, keep cash secure, and pay attention to weather warnings.\n"
    
    if behavior_profile:
        reasons = []
        if behavior_profile.get("pace") == "slow":
            reasons.append("✓ User prefers slow travel")
        if behavior_profile.get("food_style") == "cafes":
            reasons.append("✓ User prefers cafes")
        if reasons:
            guide += "\nPersonalization details:\n" + "\n".join(reasons) + "\n"
            
    return guide


def run_summary_agent(itinerary: dict | str, structured_query: dict, budget: dict, rewards: dict | str, behavior_profile: dict | None = None) -> str:
    from monitoring.logger import logger
    dest = structured_query.get("destination", "your destination")
    logger.info("[Summary Agent] Entering agent")
    logger.info(f"[Summary Agent] Destination received: {dest}")
    days = structured_query.get("days", 3)
    style = structured_query.get("travel_style", "moderate")
    food = structured_query.get("food_preference", "local")
    cards = structured_query.get("cards", [])
    
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
        from monitoring.logger import logger
        summary = invoke_text(SYSTEM_PROMPT, prompt, temperature=0.3)
        if summary and len(summary.strip()) > 100:
            logger.info(f"[Summary Agent] Destination returned: {dest}")
            logger.info("[Summary Agent] Leaving agent")
            return summary
        logger.warning("LLM returned invalid or empty summary response, using fallback summary.")
    except Exception as e:
        from monitoring.logger import logger
        if "No AI provider configured" in str(e) or "LLM unavailable" in str(e):
            raise e
        logger.error(f"Summary agent failed: {e}. Using fallback summary.")
            
    res = _fallback_summary(itinerary, structured_query, budget, rewards, behavior_profile)
    logger.info(f"[Summary Agent] Destination returned: {dest}")
    logger.info("[Summary Agent] Leaving agent")
    return res
