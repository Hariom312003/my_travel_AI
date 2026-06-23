"""Unified LLM interface for the Multi-Agent AI Travel Assistant.

Supports:
1. Claude (Priority 1) via Anthropic API
2. OpenAI GPT (Priority 2) via OpenAI API
3. Gemini (Priority 3) via Google AI API
4. Mock LLM for offline unit testing
"""
from __future__ import annotations

import os
import re
import json
import time
import requests
import contextvars
from typing import Optional, Any

from monitoring.logger import logger
from agents.demo_data import DEMO_ATTRACTIONS, DEMO_FOOD

# Thread/Async-safe context variable to store LLM traces
llm_trace_var = contextvars.ContextVar("llm_trace", default=None)

def get_available_provider() -> list[dict[str, Any]]:
    """Get all configured LLM providers in target priority order."""
    providers = []

    # 1. Gemini Free
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key and gemini_key.strip():
        providers.append({"name": "Gemini", "model": "gemini-2.5-flash-lite", "api_key": gemini_key})

    # 2. Groq Free
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key and groq_key.strip():
        providers.append({"name": "Groq", "model": "llama-3.3-70b-versatile", "api_key": groq_key})

    # 3. OpenRouter Free
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key and openrouter_key.strip():
        providers.append({"name": "OpenRouter", "model": "meta-llama/llama-3.3-70b-instruct:free", "api_key": openrouter_key})

    # 4. Claude
    claude_key = os.getenv("CLAUDE_API_KEY") or os.getenv("CLAUDE_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if claude_key and claude_key.strip():
        providers.append({"name": "Claude", "model": "claude-3-5-sonnet-20241022", "api_key": claude_key})

    # 5. OpenAI GPT
    openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
    if openai_key and openai_key.strip():
        providers.append({"name": "GPT", "model": "gpt-4o", "api_key": openai_key})

    # 6. Gemini Backup Key
    gemini_backup = os.getenv("GEMINI_API_KEY_BACKUP")
    if gemini_backup and gemini_backup.strip():
        providers.append({"name": "GeminiBackup", "model": "gemini-2.5-flash-lite", "api_key": gemini_backup})

    # 7. Groq Backup Key
    groq_backup = os.getenv("GROQ_API_KEY_BACKUP")
    if groq_backup and groq_backup.strip():
        providers.append({"name": "GroqBackup", "model": "llama-3.3-70b-versatile", "api_key": groq_backup})

    # 8. OpenRouter Backup Key
    openrouter_backup = os.getenv("OPENROUTER_API_KEY_BACKUP")
    if openrouter_backup and openrouter_backup.strip():
        providers.append({"name": "OpenRouterBackup", "model": "meta-llama/llama-3.3-70b-instruct:free", "api_key": openrouter_backup})

    return providers

def get_available_providers() -> list[tuple[str, str]]:
    """Legacy compatibility wrapper for get_available_provider()."""
    provs = get_available_provider()
    res = []
    for p in provs:
        name = p["name"]
        if name == "GeminiBackup":
            name = "Gemini"
        elif name == "GroqBackup":
            name = "Groq"
        elif name == "OpenRouterBackup":
            name = "OpenRouter"
        elif name == "GPT":
            name = "OpenAI"
        res.append((name, p["model"]))
    return res

def get_llm() -> tuple[str, str]:
    """Select the primary active LLM provider and model."""
    providers = get_available_providers()
    if not providers:
        raise Exception(
            "No AI provider configured.\n\n"
            "Add one of:\n\n"
            "GEMINI_API_KEY\n"
            "GROQ_API_KEY\n"
            "OPENROUTER_API_KEY"
        )
    return providers[0]

def provider_health_check(provider: dict) -> bool:
    """Statically verify if the provider configuration is present and non-empty."""
    name = provider.get("name")
    api_key = provider.get("api_key")
    
    if name == "Ollama":
        return True
        
    return bool(api_key and len(api_key.strip()) > 5)
        
    return bool(api_key and len(api_key.strip()) > 5)

def provider_retry(provider_func):
    """Retry a specific provider call on transient errors before failing over."""
    import time
    delays = [2.0, 4.0, 8.0]
    last_exception = None
    
    for attempt in range(len(delays) + 1):
        try:
            result = provider_func()
            if not result or not result.strip():
                raise Exception("Empty response received from LLM")
            return result, attempt
        except Exception as e:
            last_exception = e
            err_msg = str(e).lower()
            
            # Check for transient failure signatures
            is_transient = False
            for code in ["429", "500", "502", "503", "504", "rate limit", "quota", "exhausted", "timeout", "connection", "unavailable"]:
                if code in err_msg:
                    is_transient = True
                    break
                    
            if not is_transient:
                logger.warning(f"Non-transient SRE error encountered: {e}. Failing over immediately.")
                raise e
                
            if attempt == len(delays):
                break
                
            delay = delays[attempt]
            logger.warning(f"Transient SRE error ({e}) on attempt {attempt + 1}. Retrying in {delay}s...")
            time.sleep(delay)
            
    raise last_exception

def provider_metrics(provider_name: str, model_name: str, latency: float, retries: int, failover_count: int, success: bool) -> dict:
    """Log and return formatted provider telemetry metrics for APM logging."""
    status = "Success" if success else "Failed"
    logger.info(
        f"[LLM SRE Telemetry] Provider: {provider_name} | Model: {model_name} | "
        f"Latency: {latency:.2f}s | Retries: {retries} | "
        f"Failovers: {failover_count} | Status: {status}"
    )
    return {
        "provider": provider_name,
        "model": model_name,
        "latency": round(latency, 2),
        "retries": retries,
        "failover_count": failover_count,
        "success_status": status
    }

def call_with_failover(prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.2) -> str:
    """Execute LLM generation with automatic provider failover and transient retry logic."""
    providers = get_available_provider()
    if not providers:
        raise Exception(
            "No AI provider configured.\n\n"
            "Add one of:\n\n"
            "GEMINI_API_KEY\n"
            "GROQ_API_KEY\n"
            "OPENROUTER_API_KEY\n"
            "CLAUDE_API_KEY\n"
            "OPENAI_API_KEY"
        )

    last_error = None
    failover_count = 0
    providers_attempted = []
    
    for provider in providers:
        provider_name = provider["name"]
        model_name = provider["model"]
        api_key = provider["api_key"]
        
        # Verify provider health status
        if not provider_health_check(provider):
            logger.warning(f"Provider {provider_name} failed SRE health check. Skipping.")
            continue
            
        providers_attempted.append(provider_name)
        start_time = time.time()
        
        # Setup specific SRE generator call wrapper
        def execute_call():
            if provider_name == "Mock":
                return mock_generate(prompt, system_prompt, temperature)
            elif provider_name == "Ollama":
                return generate_ollama(model_name, prompt, system_prompt, temperature)
            elif provider_name == "Gemini":
                return generate_gemini(model_name, prompt, system_prompt, temperature, api_key=api_key)
            elif provider_name == "GeminiBackup":
                return generate_gemini(model_name, prompt, system_prompt, temperature, api_key=api_key)
            elif provider_name == "Groq":
                return generate_groq(model_name, prompt, system_prompt, temperature, api_key=api_key)
            elif provider_name == "GroqBackup":
                return generate_groq(model_name, prompt, system_prompt, temperature, api_key=api_key)
            elif provider_name == "OpenRouter":
                return generate_openrouter(model_name, prompt, system_prompt, temperature, api_key=api_key)
            elif provider_name == "OpenRouterBackup":
                return generate_openrouter(model_name, prompt, system_prompt, temperature, api_key=api_key)
            elif provider_name == "Claude":
                return generate_claude(prompt, system_prompt, temperature, api_key=api_key)
            elif provider_name == "GPT":
                return generate_openai(prompt, system_prompt, temperature, api_key=api_key)
            else:
                raise Exception(f"Unsupported provider: {provider_name}")

        try:
            # Execute the call with transient SRE retry logic
            result, retries = provider_retry(execute_call)
            
            latency = time.time() - start_time
            
            # Record SRE success telemetry metrics
            trace_provider_name = provider_name
            if provider_name == "GeminiBackup":
                trace_provider_name = "Gemini (Backup)"
            elif provider_name == "GroqBackup":
                trace_provider_name = "Groq (Backup)"
            elif provider_name == "OpenRouterBackup":
                trace_provider_name = "OpenRouter (Backup)"
            elif provider_name == "GPT":
                trace_provider_name = "OpenAI"
                
            trace = provider_metrics(
                provider_name=trace_provider_name,
                model_name=model_name,
                latency=latency,
                retries=retries,
                failover_count=failover_count,
                success=True
            )
            
            # Update prompt trace size information
            prompt_size = len(prompt) + (len(system_prompt) if system_prompt else 0)
            trace.update({
                "prompt_size": prompt_size,
                "response_size": len(result),
                "providers_attempted": providers_attempted
            })
            
            # Store in thread-safe context variable
            trace_list = llm_trace_var.get()
            if trace_list is not None:
                trace_list.append(trace)
                
            return result
            
        except Exception as e:
            latency = time.time() - start_time
            trace_provider_name = provider_name
            if provider_name == "GeminiBackup":
                trace_provider_name = "Gemini (Backup)"
            elif provider_name == "GroqBackup":
                trace_provider_name = "Groq (Backup)"
            elif provider_name == "OpenRouterBackup":
                trace_provider_name = "OpenRouter (Backup)"
            elif provider_name == "GPT":
                trace_provider_name = "OpenAI"
                
            # Record failover metrics
            provider_metrics(
                provider_name=trace_provider_name,
                model_name=model_name,
                latency=latency,
                retries=3, # all retries exhausted
                failover_count=failover_count,
                success=False
            )
            logger.warning(
                f"LLM Generation failed on provider {provider_name} ({model_name}) after SRE retries: {e}. "
                f"SRE triggering failover to next provider..."
            )
            last_error = e
            failover_count += 1
            continue

    # All providers exhausted
    logger.error(f"SRE CRITICAL: All LLM providers exhausted. Last error: {last_error}")
    # Return user-friendly clean exception containing a friendly error message
    raise Exception(
        "All AI search engines are busy due to extremely high public traffic. "
        "The system has automatically activated its offline safety fallback engine to build your itinerary. "
        "Please try again in a few moments."
    )

def generate(prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.2) -> str:
    """Generate completion using call_with_failover SRE mechanism."""
    return call_with_failover(prompt, system_prompt, temperature)

def robust_post(url: str, json_data: dict, headers: dict, timeout: int = 120, max_retries: int = 5) -> requests.Response:
    import time
    import re
    delay = 1.0
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=json_data, headers=headers, timeout=timeout)
            if response.status_code in (429, 500, 502, 503, 504):
                sleep_time = delay
                if response.status_code == 429:
                    try:
                        err_json = response.json()
                        details = err_json.get("error", {}).get("details", [])
                        for detail in details:
                            if detail.get("@type") == "type.googleapis.com/google.rpc.RetryInfo":
                                retry_delay_str = detail.get("retryDelay", "")
                                match = re.match(r"([\d\.]+)\s*s", retry_delay_str)
                                if match:
                                    sleep_time = float(match.group(1)) + 0.5
                                    break
                    except Exception:
                        pass
                
                if attempt == max_retries - 1:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
                logger.warning(f"HTTP {response.status_code} on attempt {attempt+1} for {url}. Retrying in {sleep_time:.2f}s...")
                time.sleep(sleep_time)
                delay = max(delay * 2, sleep_time)
                continue
            return response
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            logger.warning(f"Timeout/ConnectionError on attempt {attempt+1} for {url}: {str(e)}.")
            if attempt == max_retries - 1:
                raise e
            time.sleep(delay)
            delay *= 2
    return requests.post(url, json=json_data, headers=headers, timeout=timeout)


def generate_claude(prompt: str, system_prompt: Optional[str], temperature: float, api_key: Optional[str] = None) -> str:
    key = api_key or os.getenv("CLAUDE_API_KEY") or os.getenv("CLAUDE_KEY") or os.getenv("ANTHROPIC_API_KEY")
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4096,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}]
    }
    if system_prompt:
        payload["system"] = system_prompt
        
    response = robust_post("https://api.anthropic.com/v1/messages", payload, headers, max_retries=1)
    if response.status_code == 200:
        return response.json()["content"][0]["text"].strip()
    else:
        raise Exception(f"Claude API failed: {response.text}")

def generate_openai(prompt: str, system_prompt: Optional[str], temperature: float, api_key: Optional[str] = None) -> str:
    key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
    headers = {
        "Authorization": f"Bearer {key}",
        "content-type": "application/json"
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": "gpt-4o",
        "messages": messages,
        "temperature": temperature
    }
    response = robust_post("https://api.openai.com/v1/chat/completions", payload, headers, max_retries=1)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"].strip()
    else:
        raise Exception(f"OpenAI API failed: {response.text}")

def generate_gemini(model: str, prompt: str, system_prompt: Optional[str], temperature: float, api_key: Optional[str] = None) -> str:
    key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY") or os.getenv("GOOGLE_API_KEY")
    if key and "mock" in key.lower():
        logger.info("Gemini: mock key detected, calling mock_generate")
        return mock_generate(prompt, system_prompt, temperature)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    headers = {"content-type": "application/json"}
    
    contents = [{"parts": [{"text": prompt}]}]
    payload = {
        "contents": contents,
        "generationConfig": {"temperature": temperature}
    }
    if system_prompt:
        payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        
    response = robust_post(url, payload, headers, max_retries=1)
    if response.status_code == 200:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    else:
        raise Exception(f"Gemini API failed: {response.text}")

def generate_groq(model: str, prompt: str, system_prompt: Optional[str], temperature: float, api_key: Optional[str] = None) -> str:
    key = api_key or os.getenv("GROQ_API_KEY")
    if key and "mock" in key.lower():
        logger.info("Groq: mock key detected, calling mock_generate")
        return mock_generate(prompt, system_prompt, temperature)
    headers = {
        "Authorization": f"Bearer {key}",
        "content-type": "application/json"
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }
    response = robust_post("https://api.groq.com/openai/v1/chat/completions", payload, headers, max_retries=1)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"].strip()
    else:
        raise Exception(f"Groq API failed: {response.text}")

def generate_openrouter(model: str, prompt: str, system_prompt: Optional[str], temperature: float, api_key: Optional[str] = None) -> str:
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if key and "mock" in key.lower():
        logger.info("OpenRouter: mock key detected, calling mock_generate")
        return mock_generate(prompt, system_prompt, temperature)
    headers = {
        "Authorization": f"Bearer {key}",
        "content-type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "Voyage AI"
    }
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }
    response = robust_post("https://openrouter.ai/api/v1/chat/completions", payload, headers, max_retries=1)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"].strip()
    else:
        raise Exception(f"OpenRouter API failed: {response.text}")

def mock_generate(prompt: str, system_prompt: Optional[str], temperature: float) -> str:
    """Mock generator that dynamically simulates LLM behavior for agents in offline tests."""
    sys_lower = (system_prompt or "").lower()
    prompt_lower = prompt.lower()
    
    # 1. Query Parsing Agent
    if "query parser" in sys_lower or "query parsing" in sys_lower:
        from agents.query_agent import _fallback_parse
        result_dict = _fallback_parse(prompt)
        return json.dumps(result_dict)
        
    # 2. Planner Agent (mock dynamic itinerary generator)
    elif "travel planner" in sys_lower or "travel consultant" in sys_lower or "itinerary" in sys_lower or "trip plan" in prompt_lower:
        dest_match = re.search(r'"destination":\s*"([^"]+)"', prompt_lower) or re.search(r"destination:\s*([^\n]+)", prompt_lower)
        destination = dest_match.group(1).strip().title() if dest_match else "Destination"
        
        days_match = re.search(r'"days":\s*(\d+)', prompt_lower) or re.search(r"days:\s*(\d+)", prompt_lower)
        days = int(days_match.group(1)) if days_match else 3
        
        # Pull allowed places from prompt if present
        allowed_places = []
        places_match = re.search(r"(?:allowed_places|rag context).*?(\[.*?\])", prompt, re.IGNORECASE | re.DOTALL)
        if places_match:
            try:
                allowed_places = json.loads(places_match.group(1))
            except:
                pass
                
        from planner.planner_agent import assemble_schedule
        planner_input = {
            "destination": destination,
            "days": days,
            "allowed_places": allowed_places,
            "behavior_profile": {},
            "avoid": []
        }
        plan_dict = assemble_schedule(planner_input)
        return json.dumps(plan_dict)

    # 3. Budget Optimization Agent
    elif "budget" in sys_lower or "estimating realistic" in sys_lower or "budget_cost" in prompt_lower:
        # User requested: hotel_cost, food_cost, transport_cost, activity_cost, total_cost
        hotel = 6000
        food = 3500
        transport = 3000
        activity = 2500
        total = hotel + food + transport + activity
        
        return json.dumps({
            "hotel_cost": hotel,
            "food_cost": food,
            "transport_cost": transport,
            "activity_cost": activity,
            "total_cost": total
        })

    # 4. Rewards Optimization Agent
    elif "rewards" in sys_lower or "credit card" in sys_lower:
        recommendations = [
            {"category": "Hotel Booking", "instrument": "Credit Card", "reason": "5% reward points on travel portal", "estimated_savings": 500},
            {"category": "Food & Dining", "instrument": "UPI", "reason": "Direct wallet cashback", "estimated_savings": 200}
        ]
        return json.dumps({
            "recommendations": recommendations,
            "total_estimated_savings": 700,
            "notes": ["Use rewards card where applicable."]
        })

    # 5. Summary Agent (narrative consultant-style guide)
    elif "summary" in sys_lower or "travel guide" in sys_lower or "guide" in sys_lower:
        dest_match = re.search(r"destination:\s*([^\n]+)", prompt_lower)
        destination = dest_match.group(1).strip().title() if dest_match else "Destination"
        
        days_match = re.search(r"days:\s*([0-9]+)", prompt_lower)
        days = int(days_match.group(1)) if days_match else 3
        
        guide = f"# Travel Guide for {destination}\n\n"
        guide += f"Here is your personalized narrative travel guide for a {days}-day trip to {destination}.\n\n"
        
        # Retrieve places mentioned in prompt
        places = []
        for p in DEMO_ATTRACTIONS.get(destination, ["local spots"]):
            if p.lower() in prompt_lower:
                places.append(p)
        if not places:
            places = DEMO_ATTRACTIONS.get(destination, ["local spots"])[:3]
            
        for d in range(1, days + 1):
            p1 = places[(d*2 - 2) % len(places)]
            p2 = places[(d*2 - 1) % len(places)]
            guide += f"Day {d} begins with a wonderful visit to {p1} to explore its rich local details. "
            guide += f"After a local lunch, head over to {p2} in the afternoon for scenic exploration, "
            guide += f"before concluding your day with a delightful dining experience nearby.\n\n"
            
        guide += "### Estimated daily spend\n"
        guide += "* Daily budget average: ₹4,500\n"
        guide += f"* Grand total: ₹{4500 * days}\n\n"
        
        guide += "### Credit card reward savings\n"
        guide += "* Use co-branded credit cards for hotel and transit bookings to save up to 10%.\n"
        
        return guide

    # 6. Refinement Agent
    elif "itinerary editor" in sys_lower or "refinement" in prompt_lower or "current plan" in prompt_lower:
        current_plan = {}
        feedback = ""
        
        # Split by "User Feedback:" to safely isolate the Current Plan JSON block
        if "user feedback:" in prompt_lower:
            parts = prompt.split("User Feedback:")
            plan_part = parts[0]
            start_idx = plan_part.find('{')
            end_idx = plan_part.rfind('}')
            if start_idx != -1 and end_idx != -1:
                try:
                    current_plan = json.loads(plan_part[start_idx:end_idx+1])
                except Exception as e:
                    logger.error(f"Mock refine failed to load plan JSON: {e}")
                    
            if len(parts) > 1:
                fb_part = parts[1].split("Structured Query Context:")[0]
                feedback = fb_part.strip()
        
        # Fallback to standard regex if splitting did not work
        if not current_plan:
            plan_match = re.search(r"current plan:\s*(\{.*?\})", prompt_lower, re.DOTALL)
            if plan_match:
                try:
                    current_plan = json.loads(plan_match.group(1))
                except:
                    pass
        if not feedback:
            fb_match = re.search(r"user feedback:\s*([^\n]+)", prompt_lower)
            if fb_match:
                feedback = fb_match.group(1).strip()
            
        # Run local fallback refine to surgically edit plan
        from agents.refinement_agent import _fallback_refine
        dest = current_plan.get("destination") or "Manali"
        ref = _fallback_refine(current_plan or {"days": []}, feedback, {"destination": dest})
        return json.dumps(ref)

    return f"This is a mock fallback response for: {prompt[:100]}..."


def generate_ollama(model: str, prompt: str, system_prompt: Optional[str], temperature: float) -> str:
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    url = f"{ollama_url}/api/chat"
    headers = {"content-type": "application/json"}
    
    ollama_model = model
    if "/" in model:
        ollama_model = model.split("/")[-1].lower()
        if "qwen2.5-7b" in ollama_model:
            ollama_model = "qwen2.5:7b"
        elif "qwen2.5" in ollama_model:
            ollama_model = "qwen2.5"
            
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": ollama_model,
        "messages": messages,
        "options": {"temperature": temperature},
        "stream": False
    }
    
    response = robust_post(url, payload, headers)
    if response.status_code == 200:
        return response.json()["message"]["content"].strip()
    else:
        raise Exception(f"Ollama API failed: {response.text}")
