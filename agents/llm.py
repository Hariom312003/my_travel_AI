"""Unified LLM interface for the Multi-Agent AI Travel Assistant.

Supports:
1. Local Ollama (qwen2.5, llama3.1, mistral)
2. HuggingFace Inference API (Qwen/Qwen2.5-7B-Instruct)
3. Offline rule-engine fallback
"""
from __future__ import annotations

import os
import re
import json
import requests
from typing import Optional

from config import MODEL_NAME, HF_TOKEN, OLLAMA_URL, USE_OLLAMA
from agents.logger import logger

HF_API_URL = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"

def generate(prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.2) -> str:
    """Generate completion using local Ollama, HuggingFace Inference, or offline fallback."""
    
    # Setup messages format
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # 1. Try local Ollama if configured
    if USE_OLLAMA:
        try:
            payload = {
                "model": os.getenv("OLLAMA_MODEL", "qwen2.5"),
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": max(0.01, temperature)
                }
            }
            response = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()["message"]["content"].strip()
        except Exception:
            # Fall through if Ollama fails or is not running
            pass

    # 2. Try Hugging Face Inference API
    if HF_TOKEN:
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        
        # Chat completions standard
        chat_payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "parameters": {
                "temperature": max(0.01, temperature),
                "max_new_tokens": 1024,
            }
        }
        
        try:
            chat_url = "https://api-inference.huggingface.co/v1/chat/completions"
            response = requests.post(chat_url, json=chat_payload, headers=headers, timeout=12)
            if response.status_code == 200:
                res_data = response.json()
                if "choices" in res_data and len(res_data["choices"]) > 0:
                    return res_data["choices"][0]["message"]["content"].strip()
        except Exception:
            pass
            
        # Try direct text generation fallback on HuggingFace
        try:
            fallback_payload = {
                "inputs": f"<|im_start|>system\n{system_prompt or ''}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n",
                "parameters": {
                    "temperature": max(0.01, temperature),
                    "max_new_tokens": 1024,
                }
            }
            response = requests.post(HF_API_URL, json=fallback_payload, headers=headers, timeout=12)
            if response.status_code == 200:
                res_data = response.json()
                if isinstance(res_data, list) and len(res_data) > 0:
                    text = res_data[0].get("generated_text", "")
                    if "<|im_start|>assistant\n" in text:
                        text = text.split("<|im_start|>assistant\n")[-1]
                    return text.strip()
        except Exception:
            pass

    # 3. Local Offline Rule-Based Fallback
    return local_offline_generate(prompt, system_prompt)

def local_offline_generate(prompt: str, system_prompt: Optional[str]) -> str:
    """Local offline intelligent fallback that mimics Qwen responses for different agents."""
    logger.warning("No LLM API keys provided or LLM request failed. Falling back to local offline rule-based generation.")
    sys_lower = (system_prompt or "").lower()
    prompt_lower = prompt.lower()
    
    # Query Parsing Agent Fallback
    if "query parser" in sys_lower:
        destination = "Goa"
        for dest in ["manali", "goa", "jaipur", "kullu", "udaipur", "rishikesh", "shimla"]:
            if dest in prompt_lower:
                destination = dest.title()
                break
                
        days = 3
        days_match = re.search(r"(\d+)\s*(?:day|days|d)\b", prompt_lower)
        if days_match:
            days = int(days_match.group(1))
            
        budget = 20000
        budget_match = re.search(r"(?:under|below|budget|within|for)?\s*(?:rs\.?|inr|₹)?\s*([0-9][0-9,]{3,})", prompt_lower)
        if budget_match:
            budget = int(budget_match.group(1).replace(",", ""))
            
        cards = []
        for card in ["SBI", "HDFC", "ICICI", "Axis", "Amex", "Kotak", "IDFC"]:
            if card.lower() in prompt_lower:
                cards.append(card)
                
        interests = []
        for interest, keywords in {
            "scenic": ["scenic", "view", "views", "mountain", "sunset", "photography", "nature"],
            "local food": ["local food", "street food", "cuisine", "food", "seafood", "cafes", "cafe", "eatery"],
            "hidden gems": ["hidden", "offbeat", "less crowded", "quiet"],
            "adventure": ["adventure", "rafting", "paragliding", "trek", "water sports", "scuba"],
            "culture": ["culture", "heritage", "temple", "fort", "museum", "history"],
            "shopping": ["shopping", "market", "bazaar", "souvenir"],
            "nightlife": ["nightlife", "club", "bar", "party"],
        }.items():
            if any(kw in prompt_lower for kw in keywords):
                interests.append(interest)
        if not interests:
            interests = ["scenic", "local food"]
            
        avoid = []
        for pattern in [r"avoid ([^.]+)", r"remove ([^.]+)", r"skip ([^.]+)", r"without ([^.]+)"]:
            match = re.search(pattern, prompt_lower)
            if match:
                avoid.extend([v.strip() for v in re.split(r",| and | also ", match.group(1)) if v.strip()])
                
        pace = "medium"
        style = "moderate"
        if any(v in prompt_lower for v in ["relaxed", "slow", "easy", "less hectic", "quiet"]):
            pace = "slow"
            style = "relaxed"
        elif any(v in prompt_lower for v in ["packed", "fast", "cover more", "hectic"]):
            pace = "fast"
            style = "fast-paced"
            
        accommodation = "mid-range"
        if "luxury" in prompt_lower:
            accommodation = "luxury"
        elif "budget" in prompt_lower or budget <= 10000:
            accommodation = "budget"
            
        result_json = {
            "destination": destination,
            "days": days,
            "budget": budget,
            "travel_style": style,
            "food_preference": "local" if "local" in prompt_lower or "street" in prompt_lower or "seafood" in prompt_lower else "mixed",
            "cards": cards,
            "interests": interests,
            "accommodation": accommodation,
            "travel_pace": pace,
            "avoid": avoid,
            "travellers": 1,
            "source_city": None
        }
        return json.dumps(result_json)
        
    # Budget Estimation Agent Fallback
    if "estimating realistic indian travel budgets" in sys_lower:
        dest_match = re.search(r"Destination:\s*([^\n]+)", prompt)
        destination = dest_match.group(1).strip() if dest_match else "Goa"
        
        days_match = re.search(r"Days:\s*([0-9]+)", prompt)
        days = int(days_match.group(1)) if days_match else 3
        
        budget_match = re.search(r"Total Budget:\s*₹?([0-9]+)", prompt)
        total_budget = int(budget_match.group(1)) if budget_match else 20000
        
        accom_type_match = re.search(r"Accommodation Type:\s*([^\n]+)", prompt)
        style = accom_type_match.group(1).strip().lower() if accom_type_match else "budget"
        
        per_night = {"budget": 1500, "mid-range": 3200, "luxury": 7500}.get(style, 2200)
        food_per_day = 800 if "local" in prompt_lower else 1100
        transport_per_day = 1000 if "slow" in prompt_lower else 1400
        activity_per_day = 1200 if "adventure" in prompt_lower else 700
        
        accommodation = per_night * max(days - 1, 1)
        food = food_per_day * days
        transport = transport_per_day * days
        activities = activity_per_day * days
        shopping_misc = 1000
        contingency = int((accommodation + food + transport + activities + shopping_misc) * 0.1)
        grand_total = accommodation + food + transport + activities + shopping_misc + contingency
        
        result_json = {
            "accommodation": {"total": accommodation, "per_night": per_night, "type": style},
            "food": {"total": food, "per_day": food_per_day, "breakdown": f"Indian meals and local street snacks in {destination}."},
            "transport": {"total": transport, "breakdown": f"Local transfers, cabs, and transit around {destination}."},
            "activities": {"total": activities, "breakdown": "Entry fees, guide bookings, and sightseeing activities."},
            "shopping_misc": {"total": shopping_misc},
            "contingency": {"total": contingency},
            "grand_total": grand_total,
            "per_day_average": int(grand_total / days),
            "budget_status": "within_budget" if grand_total <= total_budget else "over_budget",
            "savings_tips": [
                f"Opt for homestays in {destination} to lower accommodation cost.",
                "Utilize shared autos or walking for short distance transfers.",
                "Choose local stalls or food markets over fine dining hubs."
            ]
        }
        return json.dumps(result_json)
        
    # Rewards Optimization Agent Fallback
    if "credit card and rewards optimization" in sys_lower:
        cards_match = re.search(r"User's Cards:\s*([^\n]+)", prompt)
        cards_str = cards_match.group(1) if cards_match else ""
        cards = [c.strip() for c in cards_str.split(",") if c.strip() and "no specific" not in c.lower()]
        
        card_text = " ".join(cards).lower()
        hotel_card = "HDFC SmartBuy / Regalia" if "hdfc" in card_text else "SBI SimplyCLICK / Cashback" if "sbi" in card_text else "best wallet offer"
        food_card = "HDFC Millennia" if "hdfc" in card_text else "SBI Cashback Card" if "sbi" in card_text else "UPI/PhonePe"
        transport_card = "SBI IRCTC Card" if "sbi" in card_text else "Amazon Pay UPI"
        
        recommendations = [
            {"category": "Hotel Booking", "instrument": hotel_card, "reason": "Use partner portals for maximum point multipliers or direct cashback.", "estimated_savings": 800},
            {"category": "Food & Cafes", "instrument": food_card, "reason": "Gain 5% cashback on dining portals or UPI spend rewards.", "estimated_savings": 350},
            {"category": "Transport", "instrument": transport_card, "reason": "Save on fuel surcharge or railway transaction charge benefits.", "estimated_savings": 200},
            {"category": "Activities", "instrument": "UPI/Discount vouchers", "reason": "Book through discount aggregators with wallet cashbacks.", "estimated_savings": 150},
            {"category": "Shopping", "instrument": "Cashback Credit Card", "reason": "Use co-branded retail cards to unlock instant discounts.", "estimated_savings": 100}
        ]
        
        result_json = {
            "recommendations": recommendations,
            "total_estimated_savings": sum(item["estimated_savings"] for item in recommendations),
            "notes": ["Check live bank application offers before completing bookings."]
        }
        return json.dumps(result_json)
        
    # Premium Summary/Travel Guide Agent Fallback
    if "summary" in prompt_lower or "travel guide" in prompt_lower or "guide" in prompt_lower:
        dest_match = re.search(r"destination:\s*([^\n]+)", prompt_lower)
        destination = dest_match.group(1).strip().title() if dest_match else "Goa"
        
        days_match = re.search(r"days:\s*([0-9]+)", prompt_lower)
        days = int(days_match.group(1)) if days_match else 3
        
        # Build premium guide
        guide = f"# Travel Guide for {destination}\n\n"
        guide += f"Here is your practical day-by-day guide for a {days}-day trip. "
        guide += "It is designed to suit your travel preferences, offering a balanced schedule with morning, afternoon, and evening activities.\n\n"
        
        # Parse out the itinerary details section from the prompt if present
        itinerary_section = ""
        itinerary_match = re.search(r"Itinerary details:\s*(.*)", prompt, re.DOTALL)
        if itinerary_match:
            itinerary_section = itinerary_match.group(1).strip()
            
        day_blocks = re.split(r"📅\s*Day\s*(\d+)", itinerary_section)
        if len(day_blocks) > 1:
            for idx in range(1, len(day_blocks), 2):
                day_num = day_blocks[idx].strip()
                day_content = day_blocks[idx+1]
                
                # Extract theme
                theme_match = re.search(r"—\s*([^\n]+)", day_content)
                theme = theme_match.group(1).strip() if theme_match else "Exploration Tour"
                
                # Extract activities
                morning_block = re.search(r"Morning Plan:.*?(?:Afternoon Plan:|Evening Plan:|Dinner|$)", day_content, re.DOTALL)
                afternoon_block = re.search(r"Afternoon Plan:.*?(?:Evening Plan:|Dinner|$)", day_content, re.DOTALL)
                evening_block = re.search(r"Evening Plan:.*?(?:Dinner|$)", day_content, re.DOTALL)
                
                morning_acts = re.findall(r"-\s*\*\*([^*]+)\*\*", morning_block.group(0)) if morning_block else []
                afternoon_acts = re.findall(r"-\s*\*\*([^*]+)\*\*", afternoon_block.group(0)) if afternoon_block else []
                evening_acts = re.findall(r"-\s*\*\*([^*]+)\*\*", evening_block.group(0)) if evening_block else []
                
                if not morning_acts and morning_block:
                    morning_acts = re.findall(r"-\s*([^\n(]+)", morning_block.group(0))
                if not afternoon_acts and afternoon_block:
                    afternoon_acts = re.findall(r"-\s*([^\n(]+)", afternoon_block.group(0))
                if not evening_acts and evening_block:
                    evening_acts = re.findall(r"-\s*([^\n(]+)", evening_block.group(0))
                    
                morning_place = morning_acts[0].strip() if morning_acts else "local spots"
                afternoon_place = afternoon_acts[0].strip() if afternoon_acts else "scenic spots"
                evening_place = evening_acts[0].strip() if evening_acts else "evening landmarks"
                
                guide += f"### DAY {day_num}: {theme}\n"
                guide += f"Spend the morning visiting **{morning_place}**. This will take about 2 hours.\n"
                guide += f"In the afternoon, head to **{afternoon_place}** for sightseeing.\n"
                guide += f"Spend the evening at **{evening_place}** to experience the local environment and try dinner.\n\n"
                
                # Dining highlight
                dinner_match = re.search(r"Dinner Recommendation:\s*\n*-\s*([^\n]+)", day_content)
                if dinner_match:
                    guide += f"**Dining Highlight:** For dinner, we recommend: *{dinner_match.group(1).strip()}*.\n\n"
        else:
            # Simple fallback description if itinerary format differs
            guide += "### Day-by-Day Journey Description\n"
            guide += f"Each day is paced to explore the best local landmarks in {destination}, with dedicated morning, afternoon, and evening slots designed to align with your travel style.\n\n"
            
        # Extract per-day average from budget breakdown or default
        per_day_match = re.search(r"'per_day_average':\s*([0-9]+)", prompt_lower) or re.search(r'"per_day_average":\s*([0-9]+)', prompt_lower)
        if per_day_match:
            avg_budget = int(per_day_match.group(1))
            min_b = int(avg_budget * 0.9)
            max_b = int(avg_budget * 1.1)
            guide += "### Estimated Daily Spend\n"
            guide += f"To execute this plan comfortably, we recommend a daily budget of approximately **₹{min_b:,} to ₹{max_b:,}** per person. This covers local transport, dining, and activity entry fees.\n\n"
        else:
            guide += "### Estimated Daily Spend\n"
            guide += "To execute this plan comfortably, we recommend a daily budget of approximately **₹3,200 to ₹4,500** per person. This covers local transport, dining, and activity entry fees.\n\n"
            
        personalization_reasons = []
        if "'pace': 'slow'" in prompt_lower or '"pace": "slow"' in prompt_lower:
            personalization_reasons.append("✓ User prefers slow travel")
        if "'food_style': 'cafes'" in prompt_lower or '"food_style": "cafes"' in prompt_lower:
            personalization_reasons.append("✓ User prefers cafes")
        if "adventure" in prompt_lower and ("avoid_categories" in prompt_lower or "avoid" in prompt_lower):
            if "'adventure'" in prompt_lower or '"adventure"' in prompt_lower:
                personalization_reasons.append("✓ User avoids adventure")
        if ("crowd" in prompt_lower or "quiet" in prompt_lower) and ("avoid_categories" in prompt_lower or "crowd_preference" in prompt_lower):
            personalization_reasons.append("✓ User avoids crowds")
            
        if personalization_reasons:
            guide += "\n\nThis plan was personalized because:\n\n" + "\n\n".join(personalization_reasons) + "\n\n"
            
        guide += "Enjoy your journey, travel responsibly, and let the beauty of the landscape take your breath away!"
        return guide
        
        personalization_reasons = []
        if "'pace': 'slow'" in prompt_lower or '"pace": "slow"' in prompt_lower:
            personalization_reasons.append("✓ User prefers slow travel")
        if "'food_style': 'cafes'" in prompt_lower or '"food_style": "cafes"' in prompt_lower:
            personalization_reasons.append("✓ User prefers cafes")
        if "adventure" in prompt_lower and ("avoid_categories" in prompt_lower or "avoid" in prompt_lower):
            if "'adventure'" in prompt_lower or '"adventure"' in prompt_lower:
                personalization_reasons.append("✓ User avoids adventure")
        if ("crowd" in prompt_lower or "quiet" in prompt_lower) and ("avoid_categories" in prompt_lower or "crowd_preference" in prompt_lower):
            personalization_reasons.append("✓ User avoids crowds")
            
        if personalization_reasons:
            guide += "\n\nThis plan was personalized because:\n\n" + "\n\n".join(personalization_reasons) + "\n\n"
            
        guide += "Enjoy your journey, travel responsibly, and let the beauty of the landscape take your breath away!"
        return guide

    # Generic Fallback
    return f"This is a fallback response for: {prompt[:100]}..."
