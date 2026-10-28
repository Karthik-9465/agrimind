# Antigravity Agent Builder Playbook — Farm AI Assistant

## 0. How to use this file
- Save this as `AGENTS.md` in your project root — Antigravity reads it automatically every session.
- Keep `task.md` (Section 6) as a living checklist next to it; check items off as they're completed.
- Feed Antigravity **one phase at a time** (see Section 9's kickoff prompts). This keeps each agent run's context tight and each `walkthrough.md` easy to review before moving on.

## 1. Project Identity
You are building an agentic AI platform for farmers that provides crop disease diagnosis, irrigation/fertilizer guidance, weather-aware alerts, market prices, and a RAG-backed knowledge assistant — all orchestrated by a single conversational agent (LangChain + Gemini).

This is a **solo, final-year academic project with a 4-week build window**. Prioritize a working, demoable vertical slice over architectural completeness. When in doubt, choose the simpler implementation.

## 2. Scope Contract (read before writing any code)

### Build (in scope)
- A single modular monolith backend (FastAPI, Python)
- PostgreSQL for relational data (SQLite for local development default)
- A local Chroma/FAISS vector store for RAG
- A LangChain agent with tool-calling to: disease diagnosis (Gemini Vision), irrigation rules engine, fertilizer rules engine, weather lookup, market lookup, RAG knowledge tool
- JWT auth, farm/crop CRUD
- A minimal frontend (React) — chat interface + farm profile
- APScheduler/cron-based background refresh instead of a message broker

### Explicitly out of scope — do NOT build these
- Separate microservices / independently deployable services
- An API Gateway as its own service
- RabbitMQ or any message broker
- A dedicated worker fleet/cluster
- A Redis caching layer
- Training a custom ML disease-detection model
- Live market-data scraping infrastructure
- Kubernetes/Docker Swarm orchestration
- Voice input beyond a basic browser Web Speech API stub (stretch only, lowest priority)

**If a task seems to require any "do NOT build" item, stop and flag it instead of implementing it.** These are deliberately deferred and presented as "future scaling" in the project report.

## 3. Architecture Mapping (diagram → implementation)

| Diagram Component | Implementation |
|---|---|
| API Gateway | FastAPI routing layer (same app) |
| User Service | `app/modules/auth/` |
| Farm Service | `app/modules/farm/` |
| Notification Service | `app/modules/notifications/` (console/email stub) |
| Agentic AI Engine | `app/modules/agent/` (LangChain + Gemini) |
| Disease ML Service | `app/modules/agent/tools/disease.py` (Gemini Vision call) |
| Irrigation Engine | `app/modules/agent/tools/irrigation.py` (rules) |
| Fertilizer Engine | `app/modules/agent/tools/fertilizer.py` (rules) |
| Weather Service | `app/modules/agent/tools/weather.py` (OpenWeatherMap) |
| Market Service | `app/modules/agent/tools/market.py` (static/dummy dataset) |
| Knowledge/RAG | `app/modules/agent/tools/knowledge.py` + `vector_store/` (Chroma) |
| Data Platform | Single PostgreSQL/SQLite instance + local vector store |
| Message Broker + Workers | `app/scheduler.py` (APScheduler jobs, in-process) |

## 4. Repo Structure

```
project-root/
├── AGENTS.md                 # this file
├── task.md                   # living checklist (Section 6)
├── skills/
│   ├── gemini-tool-calling.md
│   ├── rag-ingestion.md
│   └── fastapi-module-conventions.md
├── app/
│   ├── main.py
│   ├── scheduler.py
│   ├── db/
│   │   ├── session.py
│   │   ├── base.py
│   │   └── models.py
│   ├── modules/
│   │   ├── auth/
│   │   ├── farm/
│   │   ├── notifications/
│   │   └── agent/
│   │       ├── engine.py         # LangChain agent + intent routing
│   │       └── tools/
│   │           ├── disease.py
│   │           ├── irrigation.py
│   │           ├── fertilizer.py
│   │           ├── weather.py
│   │           ├── market.py
│   │           └── knowledge.py
├── vector_store/
├── frontend/
└── production_artifacts/     # walkthroughs, screenshots per phase
```

## 5. Tech Stack Decisions

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI (Python) | Same language as LangChain/Gemini SDK — less glue code |
| DB | PostgreSQL (SQLite fallback) | Free-tier friendly (Supabase/Neon), simple |
| Vector store | Chroma (local, embedded) | Zero extra infra vs. pgvector |
| LLM | Gemini (via LangChain / google-genai) | Matches original diagram |
| Frontend | React + Vite | Clean modern web UI |
| Scheduling | APScheduler | In-process, no broker needed |
| Auth | JWT (python-jose / passlib) | Fast to implement |

## 6. Build Phases (`task.md` — feed one phase to Antigravity per task)

Require a `walkthrough.md` in `production_artifacts/` at the end of each phase before starting the next.
