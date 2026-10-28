# Agrimind Agentic — Build Task Checklist

## Phase 1 — Foundation & Auth (Week 1)
- [x] Scaffold FastAPI app using the repo structure in Section 4
- [x] PostgreSQL connection + SQLite fallback + migrations/init script
- [x] Auth module: signup/login, JWT issuance, password hashing
- [x] Farm module: CRUD for farm profile + crop records
- [x] Minimal frontend: login page + farm profile page
- [x] Verify: Gemini API key works with a basic test call, logged in `production_artifacts/phase1_walkthrough.md`

## Phase 2 — Core Agent + First Tool (Week 2)
- [x] Build `agent/engine.py`: LangChain agent with intent detection + tool-calling harness
- [x] Implement `tools/disease.py`: accept image upload, call Gemini Vision, return diagnosis
- [x] Wire chat endpoint: farmer message/image → agent → tool → response
- [x] Image validation with Pillow, JWT auth protection, DB report persistence, AgriTech UI
- [x] Verify: full loop demoable — upload a leaf photo, get a diagnosis back through the agent, logged in `production_artifacts/phase2_walkthrough.md`

## Phase 3 — Remaining Engines + Data Services (Week 3)
- [x] `tools/irrigation.py`: rule-based schedule from crop + soil + weather
- [x] `tools/fertilizer.py`: rule-based agronomy recommendations
- [x] `tools/weather.py`: real OpenWeatherMap integration + mock fallback
- [x] `tools/market.py`: static APMC Mandi dataset provider (`is_demo_data=True`)
- [x] `tools/knowledge.py` + vector_store: ingest crop advisory documents, wire as RAG tool
- [x] Verify: agent correctly routes between all 6 tools based on farmer intent, logged in `production_artifacts/phase3_walkthrough.md`

## Phase 4 — Integration, Polish & Demo Prep (Week 4)
- [x] Notification stub (console/email) triggered by scheduler
- [x] Input guardrails on agent (reject unsafe/off-topic queries gracefully)
- [x] End-to-end test pass, fix rough edges
- [x] Record demo walkthrough + screenshots for `production_artifacts/`
- [x] Write report section mapping monolith → full microservices diagram as "production scaling path"
