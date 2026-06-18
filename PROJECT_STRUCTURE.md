# Project Structure Guide

This document describes the directory organization and code modules of **MY_AI_TRAVELLER**.

---

```
MY_AI_TRAVELLER/
├── .gitignore               # Standard environment & DB excludes
├── LICENSE                  # Open-source MIT License
├── requirements.txt         # Package dependency specification
├── app.py                   # Streamlit Frontend application
├── README.md                # World-class developer & recruiter documentation
├── CONTRIBUTING.md          # Guide for local workspace setup and PR lifecycle
├── ROADMAP.md               # Future architectural and system improvements
├── CHANGELOG.md             # Iteration releases trace log
│
├── assets/                  # Infrastructure & UI screenshots
│   ├── architecture.png     # Multi-Agent swarm flowchart
│   ├── homepage.png         # Main Streamlit entrance
│   ├── itinerary.png        # Daily schedule timeline view
│   ├── refinement.png       # Live interactive chat refinement console
│   └── monitoring.png       # Logging and performance metrics trace console
│
├── docs/                    # In-depth architectural reports
│   ├── architecture.md      # Storage schemas, decoupling, and api loops
│   ├── workflow.md          # State structures and surgical updates
│   └── agents.md            # Target profiles and default fallbacks of nodes
│
├── examples/                # Compiled production guides
│   ├── bangkok_trip.md      # Sample 3-day budget route for Bangkok
│   ├── tokyo_trip.md        # Sample 3-day culture trip for Tokyo
│   └── paris_trip.md        # Sample 3-day art highlights trip for Paris
│
├── src/                     # Core source packages
│   ├── agents/              # Core LLM orchestrations
│   │   ├── common.py        # Shared JSON extraction and string formatting
│   │   ├── constants.py     # Registry boundaries and path calculations
│   │   ├── demo_data.py     # Demographics fallback data
│   │   ├── llm.py           # Unified client routing & mock generators
│   │   ├── query_agent.py   # Intent metadata extractor node
│   │   ├── refinement_agent.py # Surgical edit handler node
│   │   └── summary_agent.py # Final layout compiling node
│   │
│   ├── graph/               # Graph topology and execution hooks
│   │   └── workflow.py      # LangGraph topology config
│   │
│   ├── rag/                 # Retrieval Augmented Grounding
│   │   └── rag_agent.py     # ChromaDB retrieval and local heuristic search
│   │
│   ├── memory/              # Personalization database interfaces
│   │   └── memory_agent.py  # User style partitions extraction & sanitizing
│   │
│   ├── planner/             # Spacial routing & schedule generation
│   │   └── planner_agent.py # Clustering and pacing scheduler
│   │
│   ├── rewards/             # Fiscal auditing
│   │   ├── budget_agent.py  # Granular cost modeler node
│   │   └── rewards_agent.py # Card reward matcher node
│   │
│   ├── validator/           # Swarm self-healing loops
│   │   └── validator_agent.py # Grounding, duplicate, template auditing node
│   │
│   ├── monitoring/          # APM and performance logging
│   │   └── logger.py        # Context monitors and latency counters
│   │
│   └── api/                 # Decoupled server backend
│       └── app.py           # FastAPI REST routing handlers
│
└── tests/                   # Automation suites
    ├── test_suite.py        # End-to-end integration & compilation test client
    └── validate_planner.py  # Quality audits for strict uniqueness & leaks
```
