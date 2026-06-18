# Platform Development Roadmap

This document outlines the planned future milestones and enhancements for the **MY_AI_TRAVELLER** platform, categorized into immediate, medium-term, and production-scale horizons.

---

## Phase 1: Short-Term Architectural Enhancements

* **Dynamic Flight/Hotel API Integrations**: Replace static mock databases with real-time pricing feeds (e.g. Skyscanner, Booking.com, Amadeus API).
* **Parallel Agent Node Execution**: Optimize LangGraph routes to execute non-dependent nodes (e.g. Budget Agent and Rewards Agent) concurrently, reducing overall E2E latency by 20-30%.
* **Semantic Cache Layer**: Implement a Redis semantic cache on the Query Understanding node to resolve repeating queries instantly without invoking LLMs.

---

## Phase 2: Personalization & Memory Upgrades

* **Real-time User Profile Synthesis**: Transition memory synthesis from offline batched steps to real-time asynchronous streaming using Celery or Redis queues.
* **Complex Multi-User Planning (Collaborative Swarms)**: Support planning trips for groups, combining multi-tenant behavioral preferences into a unified optimization constraint.
* **Geographical Proximity Routing Engine**: Integrate OSRM (Open Source Routing Machine) or Google Maps Distance Matrix to compute actual drive times between activities, enforcing realistic transit buffers dynamically.

---

## Phase 3: Enterprise-Scale & Production Infrastructure

* **Hybrid RAG Scheme**: Combine semantic vector searches (ChromaDB) with lexical keyword matching (BM25) to increase grounding relevance.
* **Distributed Vector Store Deployment**: Migrate from local file-based ChromaDB client instances to a distributed cluster (e.g. Pinecone, Milvus, or Qdrant) for high-availability production workloads.
* **APM Tracing & Dashboard**: Implement OpenTelemetry hooks across the agent swarm nodes to export execution spans directly to Datadog or Prometheus.
