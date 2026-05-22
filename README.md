# ✈️ Multi-Agent AI Travel Planner

An intelligent AI-powered travel planning system built using **LangGraph**, **FastAPI**, **Streamlit**, **ChromaDB**, and **RAG architecture**.

This project generates realistic multi-day itineraries using multiple AI agents, behavioral memory, destination validation, budget awareness, rewards optimization, and retrieval-augmented travel intelligence.

---

# 🚀 Features

✅ Multi-Agent Architecture  
✅ AI Trip Planning  
✅ Behavioral Memory System  
✅ RAG-based Destination Retrieval  
✅ Budget-Aware Planning  
✅ Reward Optimization Support  
✅ Destination Validation  
✅ Natural Language Refinement  
✅ FastAPI Backend  
✅ Streamlit Frontend  
✅ ChromaDB Vector Memory  
✅ LangGraph Workflow Orchestration  
✅ Structured Travel Summaries  

---

# 🧠 AI Agents

The system uses specialized AI agents:

| Agent | Responsibility |
|---|---|
| planner_agent.py | Generates travel itinerary |
| query_agent.py | Extracts user trip preferences |
| rag_agent.py | Retrieves travel knowledge using RAG |
| validator_agent.py | Cleans and validates itinerary |
| memory_agent.py | Stores and retrieves behavioral memory |
| refinement_agent.py | Refines itinerary using user feedback |
| budget_agent.py | Optimizes budget allocation |
| rewards_agent.py | Handles reward/credit-card optimization |
| summary_agent.py | Generates trip summaries |
| common.py | Shared helper functions |
| constants.py | Global project constants |

---

# 🏗️ Tech Stack

| Component | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI |
| Workflow Engine | LangGraph |
| Vector Database | ChromaDB |
| AI Model | OpenAI |
| Retrieval | RAG |
| Memory | Behavioral Memory |
| Language | Python |

---

# 📂 Project Structure

```bash
travel_ai/
│
├── agents/
│   ├── budget_agent.py
│   ├── common.py
│   ├── constants.py
│   ├── memory_agent.py
│   ├── planner_agent.py
│   ├── query_agent.py
│   ├── rag_agent.py
│   ├── refinement_agent.py
│   ├── rewards_agent.py
│   ├── summary_agent.py
│   ├── validator_agent.py
│   └── __init__.py
│
├── api/
│   ├── app.py
│   └── __init__.py
│
├── graph/
│   ├── workflow.py
│   └── __init__.py
│
├── memory/
│   └── chroma_db/
│
├── rag_data/
│   └── travel_data.json
│
├── ui/
│   ├── streamlit_app.py
│   └── __init__.py
│
├── main.py
├── requirements.txt
├── run_api.sh
├── run_ui.sh
├── .gitignore
├── README.md
└── .env
```

---

# ⚙️ Installation

## 1️⃣ Clone Repository

```bash
git clone https://github.com/Hariom312003/travel_ai.git
cd travel_ai
```

---

## 2️⃣ Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔑 Environment Variables

Create a `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key
```

---

# ▶️ Run Backend

```bash
bash run_api.sh
```

Backend runs on:

```txt
http://localhost:8000
```

---

# 🎨 Run Frontend

```bash
bash run_ui.sh
```

Frontend runs on:

```txt
http://localhost:8501
```

---

# 🔄 LangGraph Workflow

The workflow executes:

1. Query Extraction  
2. Memory Retrieval  
3. RAG Retrieval  
4. Itinerary Planning  
5. Budget Optimization  
6. Reward Optimization  
7. Validation & Cleanup  
8. Summary Generation  

---

# 🧠 Behavioral Memory

The system remembers:

- travel pacing
- food preferences
- scenic interests
- budget style
- relaxation preference
- local-food interest
- historical preferences

Memory is stored using **ChromaDB**.

---

# 📌 Example Query

```txt
Plan a 3 day Manali trip under 20000 with local food and relaxed pacing.
```

---

# 📋 Example Output

✅ Structured itinerary  
✅ Morning / Afternoon / Evening plans  
✅ Budget-aware recommendations  
✅ Local food suggestions  
✅ Destination validation  
✅ Travel pacing optimization  

---

# 🔍 Retrieval-Augmented Generation (RAG)

The project uses RAG to retrieve:

- destination knowledge
- attractions
- local food
- travel descriptions
- destination tags
- contextual planning information

Data source:

```txt
rag_data/travel_data.json
```

---

# 💳 Reward Optimization

The system supports:

- credit card reward awareness
- travel reward optimization
- budget balancing
- spending recommendations

---

# 🛡️ Validation Layer

The validator agent prevents:

❌ invalid destinations  
❌ duplicate places  
❌ mixed-city itineraries  
❌ unrealistic schedules  
❌ malformed outputs  
❌ hallucinated attractions  

---

# 📸 UI Features

✅ Dark Theme  
✅ Trip Profile Dashboard  
✅ Itinerary Tabs  
✅ Memory-Aware Recommendations  
✅ Budget Insights  
✅ Reward Insights  
✅ Natural Language Refinement  

---

# 📈 Future Improvements

- Google Maps Integration
- Flight API Integration
- Hotel Recommendation Engine
- Multi-user Authentication
- AI Expense Tracking
- PDF Export
- Voice-Based Planning
- Live Weather Integration
- Booking Integration

---

# 👨‍💻 Author

Hariom Gupta  
M.Tech IT  
IIIT Allahabad

GitHub:  
https://github.com/Hariom312003

---

# ⭐ Repository

If you like this project, give it a ⭐ on GitHub.
