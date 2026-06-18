# Contributing to MY_AI_TRAVELLER

Thank you for your interest in contributing to **MY_AI_TRAVELLER**! We welcome improvements, bug fixes, features, and optimizations to help make this the premier multi-agent travel planner.

---

## 1. Code of Conduct
Please be respectful and collaborative in all communication, including PR reviews, issues, and discussions.

---

## 2. Setting Up the Local Workspace

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/MY_AI_TRAVELLER.git
   cd MY_AI_TRAVELLER
   ```

2. **Create virtualenv & Install dependencies**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Keys**:
   Create a `.env` file at the root:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
   USE_OLLAMA=False
   ```

---

## 3. Extending the Swarm (Adding Agents)

To introduce a new agent to the planning swarm:
1. Create your agent module inside a designated package under `src/` (e.g. `src/rewards/loyalty_agent.py`).
2. Add unit tests verifying compilation and behaviors in `tests/test_suite.py`.
3. Wire the node functions inside `src/graph/workflow.py`.
4. Run validation checks to ensure zero circular imports or execution lag.

---

## 4. Run Tests & Validation

Always run the full suite before submitting a Pull Request:

* **Unit Tests & API endpoints check**:
  ```bash
  python -m unittest tests/test_suite.py
  ```
* **Planner Quality & Constraint Validation**:
  ```bash
  python -m unittest tests/validate_planner.py
  ```

---

## 5. Pull Request Guidelines
1. Fork the repo and create your branch from `main`.
2. Write descriptive commit messages.
3. Make sure all unit tests and quality validation suites pass (100% success).
4. Update relevant documentation in `docs/` and add examples in `examples/` if adding major feature extensions.
