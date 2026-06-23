# Changelog

All notable changes to **MY_AI_TRAVELLER** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.3.0] - 2026-06-23

### Added
* Deployed multi-LLM SRE failover chain: `Gemini Free -> Groq Free -> OpenRouter Free -> Gemini Backup -> Groq Backup -> OpenRouter Backup`.
* Implemented backup API key configuration in `src/agents/llm.py` via `GEMINI_API_KEY_BACKUP`, `GROQ_API_KEY_BACKUP`, and `OPENROUTER_API_KEY_BACKUP`.
* Configured automated failover telemetry mapping to standard strings (`Gemini`, `Groq`, `OpenRouter`) for clear audit logs.
* Increased API timeout parameter in `robust_post` requests to 120 seconds to guarantee successful generation of large (e.g. 15-day) itineraries.

### Removed
* Removed all legacy Claude, OpenAI, and Mock providers from production execution paths to enforce actual provider execution.

---

## [1.2.0] - 2026-06-18

### Added
* Refactored project structure to a production-grade workspace, encapsulating core agent concerns into modular subfolders: `rag/`, `memory/`, `planner/`, `rewards/`, `validator/`, and `monitoring/` under `src/`.
* Introduced a self-healing duplicate prevention fallback inside the `Validator Agent` that generates unique sub-locations dynamically when the localized RAG dataset size is smaller than the requested day count.
* Added premium system architecture diagrams, user guides, and comprehensive example markdown itineraries for Bangkok, Tokyo, and Paris.
* Created a central Streamlit entry file `app.py` at the root that acts as the primary user dashboard.

### Changed
* Updated testing configurations in `tests/test_suite.py` and `tests/validate_planner.py` to support the modular package imports under `src/`.
* Re-designed Streamlit frontend with a high-contrast dark theme, custom Outfit typography, glassmorphic container widgets, and fluid micro-animations.

---

## [1.1.0] - 2026-06-17

### Added
* Strict destination grounding guardrails that automatically identify cross-destination leakage.
* Implemented multi-tenant user preference memory isolation under ChromaDB, backed by a standardization script that scrubs specific place name keywords to ensure cross-trip transferability without destination leaks.

---

## [1.0.0] - 2026-06-16

### Added
* Initial Multi-Agent travel planning swarm using LangGraph for state management.
* Core agents: Query understanding, Memory parsing, RAG retriever, Schedule builder, Budget modeler, Card rewards optimizer, Validator, and Summary compilers.
* Basic Streamlit UI dashboard.
