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
- PostgreSQL for relational data
- A local Chroma/FAISS vector store for RAG
- A LangChain agent with tool-calling to: disease diagnosis (Gemini Vision), irrigation rules engine, fertilizer rules engine, weather lookup, market lookup, RAG knowledge tool
- JWT auth, farm/crop CRUD
- A minimal frontend (React, or Streamlit if time-pressed) — chat interface + farm profile
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
| Data Platform | Single PostgreSQL instance + local vector store |
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
│   └── db/
├── vector_store/
├── frontend/
└── production_artifacts/     # walkthroughs, screenshots per phase
```

## 5. Tech Stack Decisions

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI (Python) | Same language as LangChain/Gemini SDK — less glue code |
| DB | PostgreSQL | Free-tier friendly (Supabase/Neon), simple |
| Vector store | Chroma (local, embedded) | Zero extra infra vs. pgvector |
| LLM | Gemini (via LangChain) | Matches original diagram |
| Frontend | React, or Streamlit if time-pressed | Streamlit ships a usable UI in hours |
| Scheduling | APScheduler | In-process, no broker needed |
| Auth | JWT (python-jose / fastapi-users) | Fast to implement |

## 6. Build Phases (`task.md` — feed one phase to Antigravity per task)

Require a `walkthrough.md` in `production_artifacts/` at the end of each phase before starting the next.

### Phase 1 — Foundation & Auth (Week 1)
- [ ] Scaffold FastAPI app using the repo structure in Section 4
- [ ] PostgreSQL connection + migrations (Alembic)
- [ ] Auth module: signup/login, JWT issuance, password hashing
- [ ] Farm module: CRUD for farm profile + crop records
- [ ] Minimal frontend: login page + farm profile page
- [ ] Verify: Gemini API key works with a basic test call, logged in `walkthrough.md`

### Phase 2 — Core Agent + First Tool (Week 2)
- [ ] Build `agent/engine.py`: LangChain agent with intent detection + tool-calling harness
- [ ] Implement `tools/disease.py`: accept image upload, call Gemini Vision, return diagnosis
- [ ] Wire chat endpoint: farmer message/image → agent → tool → response
- [ ] Verify: full loop demoable — upload a leaf photo, get a diagnosis back through the agent

### Phase 3 — Remaining Engines + Data Services (Week 3)
- [ ] `tools/irrigation.py`: rule-based schedule from crop + soil + weather
- [ ] `tools/fertilizer.py`: rule-based agronomy recommendations
- [ ] `tools/weather.py`: real OpenWeatherMap integration
- [ ] `tools/market.py`: static/dummy dataset lookup
- [ ] `tools/knowledge.py` + vector_store: ingest 5–10 crop advisory PDFs, wire as RAG tool
- [ ] Verify: agent correctly routes between all 5 tools based on farmer intent

### Phase 4 — Integration, Polish & Demo Prep (Week 4)
- [ ] Notification stub (console/email) triggered by scheduler
- [ ] Input guardrails on agent (reject unsafe/off-topic queries gracefully)
- [ ] End-to-end test pass, fix rough edges
- [ ] Record demo walkthrough + screenshots for `production_artifacts/`
- [ ] Write report section mapping monolith → full microservices diagram as "production scaling path"

## 7. Agent Rules & Guardrails
- Don't add new dependencies without listing them in a plan first — keep `requirements.txt` intentional.
- Never modify `production_artifacts/` except to add new walkthroughs — it's the audit trail.
- Every phase goes PLANNING → EXECUTION → VERIFICATION; don't skip VERIFICATION (run tests, capture a screenshot or example transcript) before marking a `task.md` item done.
- If a task could be solved with a rule/lookup instead of a new ML model or new infra service, always choose the rule/lookup — this is a scope-control default, not a shortcut to cut corners.
- Ask before touching auth/security-sensitive code without a written plan first.

## 8. Skills to seed in `skills/`
- `gemini-tool-calling.md` — conventions for defining LangChain tools against Gemini (function schemas, error handling, response parsing)
- `rag-ingestion.md` — how to chunk/embed PDFs into Chroma consistently
- `fastapi-module-conventions.md` — how each module should be structured (router, schema, service, repository) so the codebase stays consistent across 4 weeks of agent-driven changes

## 9. Kickoff Prompts (paste into Antigravity's Manager/Agent surface)

**Phase 1 kickoff:**
> Read AGENTS.md and task.md. Execute Phase 1 only. Scaffold the FastAPI app per the repo structure in AGENTS.md, implement the auth and farm modules, and stand up the minimal frontend. Stop and produce a walkthrough.md before starting Phase 2.

**Phase 2 kickoff:**
> Read AGENTS.md and task.md — Phase 1 is complete (see production_artifacts/). Execute Phase 2 only: build the LangChain agent engine and the disease-diagnosis tool via Gemini Vision. Do not implement irrigation/fertilizer/weather/market/knowledge tools yet — those are Phase 3.

**Phase 3 kickoff:**
> Read AGENTS.md and task.md — Phases 1–2 are complete. Execute Phase 3 only: implement the irrigation, fertilizer, weather, market, and knowledge/RAG tools and wire them into the agent. Verify tool routing before finishing.

**Phase 4 kickoff:**
> Read AGENTS.md and task.md — Phases 1–3 are complete. Execute Phase 4 only: add the notification stub and guardrails, run a full end-to-end pass, and produce the final demo walkthrough with screenshots.

## 10. Definition of Done (per phase)
A phase is done when: `task.md` items for that phase are checked, a `walkthrough.md` exists with screenshots or a transcript proving the feature works, and nothing outside that phase's scope was touched.
