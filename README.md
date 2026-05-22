# ✈️ Multi-Agent AI Travel Planner

An intelligent AI-powered travel planning system built using:

- LangGraph
- FastAPI
- Streamlit
- ChromaDB
- Retrieval-Augmented Generation (RAG)
- Behavioral Memory
- Multi-Agent Architecture

---

# 🚀 Features

## ✅ AI Trip Planning
Generate complete travel itineraries using natural language.

Example:

```text
Plan a 3 day Manali trip under 20000 with local food and relaxed cafes.
```

---

## ✅ Multi-Agent System

The project uses specialized AI agents:

- Planner Agent
- RAG Agent
- Validator Agent
- Memory Agent
- Refinement Agent

---

## ✅ Destination-Locked RAG

The system prevents cross-destination contamination.

Example:
- Goa places will NOT appear in Manali itineraries
- Jaipur attractions will NOT appear in Goa trips

---

## ✅ Behavioral Memory

The system remembers ONLY:
- travel style
- food preference
- pacing preference
- budget style

It does NOT store:
- destinations
- itinerary text
- private trip details

---

## ✅ Streamlit UI

Interactive modern frontend for:
- trip generation
- itinerary refinement
- reward optimization
- memory visualization

---

# 🛠 Tech Stack

| Component | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI |
| Workflow | LangGraph |
| Vector DB | ChromaDB |
| LLM | OpenAI |
| Memory | Behavioral Memory |
| Retrieval | RAG |

---

# 📂 Project Structure

```text
travel_ai/
│
├── agents/
│   ├── planner_agent.py
│   ├── rag_agent.py
│   ├── validator_agent.py
│   ├── memory_agent.py
│   ├── refinement_agent.py
│   └── constants.py
│
├── api/
├── graph/
├── ui/
├── memory/
├── rag_data/
├── README.md
└── requirements.txt
```

---

# ⚡ Installation

## Clone Repository

```bash
git clone https://github.com/Hariom312003/travel_ai.git
cd travel_ai
```

---

## Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔑 Environment Variables

Create `.env`

```env
OPENAI_API_KEY=your_key_here
```

---

# ▶️ Run FastAPI

```bash
uvicorn api.app:app --reload
```

API:
```text
http://localhost:8000
```

---

# ▶️ Run Streamlit

```bash
streamlit run ui/streamlit_app.py
```

UI:
```text
http://localhost:8501
```

---

# 🧠 Architecture

```text
constants.py
↓
rag_agent.py
↓
planner_agent.py
↓
validator_agent.py
↓
workflow.py
↓
api/ui
```

---

# 🔒 Safety Features

- Removes hallucinated destinations
- Removes contaminated memory
- Prevents cross-destination leakage
- Cleans itinerary before rendering
- Restricts memory to behavioral preferences only

---

# 📸 Example Query

```text
Plan a 2 day Goa trip with beaches and seafood under 15000
```

---

# 👨‍💻 Author

Hariom Gupta

M.Tech IT
Indian Institute of Information Technology Allahabad

---

# ⭐ Future Improvements

- Hotel recommendation engine
- Flight integration
- Real-time weather
- Maps integration
- Expense prediction
- Multi-user memory
