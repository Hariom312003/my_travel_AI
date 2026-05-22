"""Reward Optimization Agent - suggests best card/wallet usage for a trip."""
from __future__ import annotations

from agents.common import invoke_json

CARD_KNOWLEDGE = """
SBI Cards:
- SBI SimplyCLICK: 10x rewards on online spends (MakeMyTrip, Cleartrip)
- SBI Cashback Card: 5% cashback on online bookings
- SBI IRCTC Card: 10% value back on train bookings

HDFC Cards:
- HDFC Regalia: 4 reward points/₹150, Priority Pass lounge access
- HDFC Millennia: 5% cashback on Amazon, Flipkart, Zomato, Swiggy
- HDFC SmartBuy: Extra 10x rewards when booking via SmartBuy portal
- HDFC MoneyBack+: 2x cashback on Swiggy, BigBasket, Amazon

ICICI Cards:
- ICICI Amazon Pay: 5% cashback at Amazon (Prime), 2% others
- ICICI Coral: Fuel surcharge waiver, dining discounts

UPI/Wallets:
- PhonePe: Scratch cards on every transaction, insurance offers
- Google Pay: Cashback on travel bookings via partner merchants
- Amazon Pay UPI: 1-5% cashback on partner merchants
- Paytm: Travel offers on hotels and bus bookings
"""

SYSTEM_PROMPT = f"""You are a credit card and rewards optimization expert for Indian travellers.

Card Knowledge:
{CARD_KNOWLEDGE}

Analyze the user's trip and cards. Suggest:
1. Which card to use for hotel booking and WHY
2. Which card/UPI for food/restaurants
3. Which card for transport/fuel
4. Which card for activities/adventure booking
5. Which card for shopping
6. Estimated cashback/rewards in INR

Return ONLY valid JSON:
{{
  "recommendations": [{{"category": string, "instrument": string, "reason": string, "estimated_savings": int}}],
  "total_estimated_savings": int,
  "notes": [string]
}}"""

def _fallback_rewards(structured_query: dict, budget_breakdown: dict) -> dict:
    cards = structured_query.get("cards", [])
    card_text = " ".join(cards).lower()
    hotel_card = "HDFC SmartBuy / HDFC card" if "hdfc" in card_text else "SBI Cashback Card" if "sbi" in card_text else "best available hotel portal offer"
    food_card = "HDFC Millennia" if "hdfc" in card_text else "SBI Cashback Card" if "sbi" in card_text else "Amazon Pay UPI"
    transport_card = "SBI IRCTC Card" if "sbi" in card_text else "Amazon Pay UPI"
    accommodation_total = budget_breakdown.get("accommodation", {}).get("total", 0)
    food_total = budget_breakdown.get("food", {}).get("total", 0)
    transport_total = budget_breakdown.get("transport", {}).get("total", 0)
    recommendations = [
        {"category": "Hotel booking", "instrument": hotel_card, "reason": "Use travel portal rewards or direct cashback for the largest fixed spend.", "estimated_savings": int(accommodation_total * 0.05)},
        {"category": "Food and cafes", "instrument": food_card, "reason": "Prioritize dining, Swiggy/Zomato, or online cashback where accepted.", "estimated_savings": int(food_total * 0.03)},
        {"category": "Transport", "instrument": transport_card, "reason": "Use UPI/card offers for cabs, fuel, bus, or train bookings.", "estimated_savings": int(transport_total * 0.02)},
        {"category": "Activities", "instrument": "Wallet or card with live merchant coupon", "reason": "Compare activity platforms before booking adventure slots.", "estimated_savings": 300},
        {"category": "Shopping", "instrument": "UPI with merchant cashback", "reason": "Use small UPI payments where local merchants support cashback campaigns.", "estimated_savings": 150},
    ]
    return {
        "recommendations": recommendations,
        "total_estimated_savings": sum(item["estimated_savings"] for item in recommendations),
        "notes": ["Offers change frequently; verify live card and wallet terms before payment."],
    }


def rewards_to_text(rewards: dict) -> str:
    lines = []
    for idx, item in enumerate(rewards.get("recommendations", []), 1):
        lines.append(
            f"{idx}. {item.get('category')}: Use {item.get('instrument')} - "
            f"{item.get('reason')} Estimated savings: ₹{item.get('estimated_savings', 0)}."
        )
    lines.append(f"Total estimated savings: ₹{rewards.get('total_estimated_savings', 0)}")
    for note in rewards.get("notes", []):
        lines.append(f"Note: {note}")
    return "\n".join(lines)


def run_rewards_agent(structured_query: dict, budget_breakdown: dict) -> dict:
    fallback = _fallback_rewards(structured_query, budget_breakdown)
    cards = structured_query.get("cards", [])
    prompt = f"""
User's Cards: {', '.join(cards) if cards else 'No specific cards mentioned — suggest best common options'}
Destination: {structured_query.get('destination')}
Total Budget: ₹{structured_query.get('budget')} INR
Budget Breakdown: {budget_breakdown}

Provide specific reward optimization recommendations:"""

    rewards = invoke_json(SYSTEM_PROMPT, prompt, fallback=fallback, temperature=0.2)
    return rewards if isinstance(rewards, dict) and rewards.get("recommendations") else fallback
