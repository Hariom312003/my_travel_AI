# Multi-Agent Specifications

This manual details the role, system prompt parameters, and fallback actions for every specialized agent in the **my_travel_AI** orchestration swarm.

---

## 1. Query Agent
* **Role**: Parses user input into a standardized structured search query.
* **Input**: User query text (e.g., `"Plan a 3-day Manali trip under ₹20,000"`).
* **Output**: JSON containing `destination`, `days`, `budget`, `interests`, `cards`, and style flags.
* **Fallback Behavior**: If the LLM call fails or returns invalid JSON, routes to a local regex parser (`_fallback_parse` in `agents/query_agent.py`) that matches key patterns (like day count, currency numbers, and destinations) and merges them with a default config dictionary.

---

## 2. Memory Agent
* **Role**: Manages the persistent memory profile.
* **Retrieve Cycle**: Queries ChromaDB for historical preferences matching the `user_id` and adds confidence scores.
* **Commit Cycle**: Extracts preferences from the finalized plan and stores them, filtering out destination keywords.
* **Fallback Behavior**: If memory collection is empty or fails, yields default moderate style settings.

---

## 3. RAG Agent
* **Role**: Queries destination knowledge.
* **Input**: Destination name and interests.
* **Output**: A list of grounded place entity dictionaries containing pricing, categories, transit recommendations, and visiting times.
* **Fallback Behavior**: If ChromaDB fails, falls back to a memory-resident heuristic search over the local `travel_data.json` database.

---

## 4. Planner Agent
* **Role**: Constructs the core itinerary schedule.
* **Input**: RAG attractions, parsed query, and memory profile.
* **Output**: A JSON array of days. Each day features Morning, Afternoon, Evening slots, and pacing notes.
* **Fallback Behavior**: Re-attempts generation or returns structured templates using elements selected from the RAG list.

---

## 5. Budget Agent
* **Role**: Audits and estimates cost metrics.
* **Input**: Itinerary schedule and target budget.
* **Output**: Granular cost breakdown (lodging, dining, transport, activities) and status (`within_budget` or `over_budget`).
* **Fallback Behavior**: Employs simple multipliers based on day count, pacing, food style, and hotel category.

---

## 6. Rewards Agent
* **Role**: Matches credit card benefits to category spend.
* **Input**: User's credit cards and budget breakdown.
* **Output**: Optimized payment cards and estimated savings.
* **Fallback Behavior**: Utilizes standard payment rules (e.g., using co-branded retail cards for booking discounts).

---

## 7. Validator Agent
* **Role**: Enforces constraint parameters.
* **Tasks**:
  1. Grounding check: Verifies all scheduled locations belong to the target destination RAG database.
  2. Duplicate check: Ensures no attraction is visited multiple times.
  3. Pacing check: Verifies schedule matches travel pace constraints.
* **Fallback Behavior**: Resolves conflicts by swapping invalid or duplicate entries with valid alternatives from the RAG database.

---

## 8. Summary Agent
* **Role**: Generates user-facing summaries.
* **Input**: Finalized itinerary, budget, and rewards.
* **Output**: Simple English day-by-day travel guide.
* **Fallback Behavior**: Extracts scheduled days and themes via regex to compile a structured travel guide.
