# AgriMind AI – Agentic Smart Agriculture Assistant

> **Voice-First Multilingual Agricultural Decision Support for Indian Farmers**  
> *Submitted for The Great Indian AI Internship Challenge by Gnani AI*

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React_18_%2B_Vite-61DAFB.svg?style=flat&logo=react)](https://react.dev)
[![Gnani AI](https://img.shields.io/badge/Voice_AI-Gnani_Prisma_%26_Timbre-F59E0B.svg?style=flat)](https://gnani.ai)
[![Gemini Vision](https://img.shields.io/badge/Vision_AI-Google_Gemini_2.5_Flash-4285F4.svg?style=flat&logo=google)](https://deepmind.google/technologies/gemini)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat&logo=python)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-31%2F31_Passed-brightgreen.svg?style=flat)](https://pytest.org)

---

## 1. Project Title
**AgriMind AI – Agentic Smart Agriculture Assistant**  
*Subtitle:* Voice-First Multilingual Agricultural Decision Support for Indian Farmers.

---

## 2. Project Overview
**AgriMind AI** is an intelligent, voice-first agricultural decision support assistant engineered specifically for Indian farmers. By combining **Gnani AI's** Indic speech-to-text (Prisma) and text-to-speech (Timbre) engines with **Google Gemini Vision** multimodal leaf pathology analysis and deterministic scientific agronomy models, AgriMind AI eliminates linguistic and technological barriers for smallholders. Farmers can speak in their native regional language, photograph plant foliage, and receive real-time spoken and visual recommendations tailored to their land parcels.

---

## 3. Problem Statement
Smallholder and regional farmers across India face systemic challenges when seeking timely, expert agricultural advice:
- **Linguistic Exclusion:** Most agritech platforms operate primarily in English or formal Hindi, failing to cater to regional dialects and colloquial farming terms.
- **Digital Literacy & Interface Friction:** Smallholder farmers often struggle with complex, text-heavy applications, multi-step navigation, and technical spreadsheets.
- **Unreliable Dosages:** Generic generative AI chatbots often hallucinate chemical and water quantities, posing grave ecological and financial risks.
- **Information Fragmentation:** Crop pathology, irrigation rules, soil test results, weather forecasts, and APMC Mandi price tickers reside in isolated silos.

---

## 4. Proposed Solution
AgriMind AI introduces a unified conversational and cadastral farm assistant accessible entirely through spoken Indic voice:
1. **Spoken Voice Interaction:** Farmers speak queries naturally in **Telugu**, **Hindi**, or **Indian English**.
2. **Instant Spoken Delivery:** Responses are converted into crystal-clear spoken audio, allowing farmers to listen without reading long text.
3. **Multimodal Foliar Disease Diagnosis:** Leaf photographs are analyzed for foliar lesions, blight, and pest attacks using vision models with non-hallucinatory safety guardrails.
4. **Deterministic Scientific Agronomy:** Irrigation schedules follow **FAO-56 Penman-Monteith** equations, while fertilizer quantities follow **ICAR Soil Test Crop Response (STCR)** targeted yield formulas.
5. **Hyperlocal Intelligence:** Real-time agro-weather alerts, Delta-T pesticide spray windows, and APMC wholesale mandi price trends protect crops and farm income.

---

## 5. Key Features

| Capability | Module | Implementation Description |
|---|---|---|
| **Voice Querying (STT)** | `Gnani Prisma` | 16kHz WAV Indic speech recognition supporting Telugu, Hindi, and Indian English. |
| **Spoken Advisory (TTS)** | `Gnani Timbre` | 48kHz high-fidelity speech synthesis using verified voices (`Avinash`, `Shivani`). |
| **Foliar Diagnosis** | `Gemini 2.5 Flash` | Multimodal leaf lesion analysis producing structured ICAR-aligned treatment guidance. |
| **Precision Irrigation** | `FAO-56 Engine` | Daily crop evapotranspiration ($ET_c$), soil Available Water Capacity (AWC), and liters/acre advice. |
| **Nutrient Balancing** | `ICAR STCR Engine` | Soil test-based N-P-K nutrient balancing for basal and top-dressing applications. |
| **Agro-Weather Advisory** | `Weather Service` | OpenWeatherMap integration calculating thermal stress index and Delta-T chemical spray windows. |
| **Mandi Price Discovery** | `Market Tool` | APMC wholesale market intelligence tracking modal, minimum, and maximum rates with 7-day volatility bands. |
| **Agronomy Knowledge RAG** | `Knowledge Tool` | Local vector cosine similarity retrieval over ICAR crop production handbooks. |

---

## 6. Gnani AI Integration (Featured Voice Stack)

AgriMind AI integrates official Gnani AI voice APIs to deliver a seamless hands-free interface:

```
Farmer Speaks (Audio Blob)
      │
      ▼
Browser WebRTC MediaRecorder ──► FastAPI Backend Normalizer (16kHz WAV)
                                       │
                                       ▼
                         Gnani Prisma STT (v3) [api.vachana.ai/stt/v3]
                                       │
                                       ▼
                           Transcribed Farmer Query
                                       │
                                       ▼
                       Agentic Intent Routing & Scientific Engine
                                       │
                                       ▼
                           Synthesized Agronomic Advice
                                       │
                                       ▼
                     Gnani Timbre TTS (v3.0) [api.vachana.ai/api/v1/tts/inference]
                                       │
                                       ▼
                          48kHz Audio Stream (WAV / MP3)
                                       │
                                       ▼
Farmer Hears Native Speech (Avinash / Shivani Voice with 0.85x–1.15x speed clamping)
```

### Verified Language & Voice Configurations
- **Telugu (`te-IN`):** Voice **`Avinash`** (Official Timbre v3.0 model).
- **Hindi (`hi-IN`):** Voice **`Shivani`** (Official Timbre v3.0 model).
- **Indian English (`en-IN`):** Voice **`Avinash`** (Official Timbre v3.0 model).

---

## 7. Google Gemini Vision Integration

Crop leaf pathology is powered by **Google Gemini 2.5 Flash Vision** (`gemini-2.5-flash`):
- **Structured Schema:** Emits condition, severity (`Mild`, `Moderate`, `Severe`, `Uncertain`), diagnostic observations, and separate organic vs. chemical management steps.
- **Safety Guardrails:** Rejects unidentifiable, synthetic, or blurry images without guessing, requesting the farmer to submit a clearer photo.
- **Legal Advisory Disclaimer:** Explicitly marks all findings as agricultural decision support requiring expert agronomic confirmation.
- **Resilience:** Features 60-second in-memory caching and a 2-attempt network retry loop.

---

## 8. Technical Architecture

AgriMind AI is engineered as a **FastAPI Modular Monolith** paired with a responsive **React 18 + Vite** frontend.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   TIER 1: PRESENTATION LAYER (CLIENT)                  │
│       React 18 + Vite Web Application (AudioRecorder, Chat, Farm)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP REST / Multipart Form Data
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              TIER 2: APPLICATION & SECURITY (FASTAPI :8000)            │
│         JWT Auth (Passlib/Bcrypt) • Input Guardrails • Pydantic v2     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               TIER 3: AGENTIC ROUTER & DECISION ENGINES                │
│  ┌───────────────────────┐ ┌───────────────────┐ ┌──────────────────┐  │
│  │   Gnani Voice Stack   │ │   Gemini Vision   │ │ Scientific Rules │  │
│  │ Prisma STT / Timbre   │ │  2.5 Flash Vision │ │ FAO-56 / ICAR    │  │
│  └───────────────────────┘ └───────────────────┘ └──────────────────┘  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│            TIER 4: DATA PERSISTENCE & IN-PROCESS SCHEDULING            │
│     SQLite Database (SQLAlchemy ORM) • ICAR Vector RAG • APScheduler   │
└────────────────────────────────────────────────────────────────────────┘
```

The high-resolution architectural diagram is available at [`AgriMind_Architecture.png`](AgriMind_Architecture.png) (editable source: [`AgriMind_Architecture.mmd`](AgriMind_Architecture.mmd)).

---

## 9. Technology Stack

- **Frontend:** React 18, Vite 5, Tailwind-styled custom CSS, WebRTC MediaRecorder API, HTML5 AudioContext.
- **Backend:** Python 3.10+, FastAPI, Pydantic v2, Starlette, Uvicorn.
- **Voice AI:** Gnani AI Prisma STT (v3) & Gnani AI Timbre TTS (v3.0).
- **Vision AI:** Google Gemini 2.5 Flash (`google.genai` SDK).
- **Data Persistence:** SQLite (development default) / PostgreSQL (production), SQLAlchemy 2.0 ORM.
- **Background Tasks:** APScheduler (in-process cron/interval scheduler).
- **Audio Processing:** Python standard library `wave`, `struct`, in-memory sound normalization.

---

## 10. GitHub Repository URL
- **Official Repository:** [https://github.com/Karthik-9465/agrimind.git](https://github.com/Karthik-9465/agrimind.git)

---

## 11. Team Details & Institution
- **Project Lead:** Karthik Sonaveni ([karthiksonaveni2@gmail.com](mailto:karthiksonaveni2@gmail.com))
- **Team Members:** `[Team Member 2 Name - Placeholder]`, `[Team Member 3 Name - Placeholder]`
- **Institution:** Bharat Institute of Engineering and Technology (BIET)
- **Challenge:** The Great Indian AI Internship Challenge by Gnani AI

---

## 12. Installation & Local Execution Instructions

### Prerequisites
- Python 3.10 or higher
- Node.js 18+ and npm
- Git

### Step 1: Clone Repository
```bash
git clone https://github.com/Karthik-9465/agrimind.git
cd agrimind
```

### Step 2: Backend Setup
```bash
# Create and activate virtual environment (optional but recommended)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt
```

### Step 3: Frontend Setup
```bash
cd frontend
npm install
cd ..
```

### Step 4: Run Application
In terminal 1 (Backend):
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

In terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Open your browser at `http://localhost:5173`.

---

## 13. Environment Variable Setup

Copy the template file to configure your local credentials:
```bash
cp .env.example .env
```

Edit `.env` using your actual API credentials (placeholders shown below):
```env
# Application Core
ENV=development
DEBUG=True
SECRET_KEY=generate_a_secure_jwt_secret_key_here

# Database Configuration (SQLite default; PostgreSQL supported)
DATABASE_URL=sqlite:///./agrimind.db

# Gnani AI Configuration (Voice Stack)
GNANI_API_KEY=your_gnani_api_key_here
GNANI_ACCESS_TOKEN=your_gnani_access_token_here
GNANI_STT_ENDPOINT=https://api.vachana.ai/stt/v3
GNANI_TTS_ENDPOINT=https://api.vachana.ai/api/v1/tts/inference
GNANI_TTS_MODEL=timbre-v3.0
GNANI_DEFAULT_VOICE=Avinash
GNANI_DEFAULT_LANG=te-IN
GNANI_MODE=LIVE

# Google Gemini Vision Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_MODE=LIVE

# Hyperlocal Weather API (Optional)
OPENWEATHER_API_KEY=your_openweather_api_key_here
```

---

## 14. Demo Instructions

A complete 2-minute 30-second live demonstration script is provided in [`AgriMind_Gnani_Demo_Script.md`](AgriMind_Gnani_Demo_Script.md).

### Live Verification Flow:
1. **Health Verification:** Query `GET /api/v1/health/integrations?refresh=true` to verify that both `gnani_voice` and `gemini_vision` report `CONNECTED`.
2. **Telugu Voice Interaction:**
   - Select **Telugu** in the dashboard.
   - Record the query: *"నా టమాటా పంటకు పూత దశలో ఏ ఎరువులు వాడాలి?"*
   - Verify transcription returned by Gnani Prisma.
   - Click **`Play Response`** to listen to speech generated by Gnani Timbre (`Avinash` voice).
3. **Foliar Diagnosis:**
   - Attach a leaf photo in the chat.
   - Verify structured disease identification and ICAR-aligned organic treatments.

---

## 15. Responsible AI, Agronomic Disclaimers & Limitations

1. **Advisory Decision Support:** AgriMind AI provides agronomic guidance designed to augment farmer knowledge. It is not a substitute for certified agronomist field inspections or licensed chemical applicator oversight.
2. **Deterministic Dosage Protection:** Generative LLMs are never permitted to generate unvalidated chemical dosages. All chemical recommendations reference validated ICAR STCR equations and state agricultural extension guidelines.
3. **Uncertainty Guardrails:** When crop foliage images are blurry, unidentifiable, or out of domain, Gemini Vision explicitly reports `Uncertain` and directs the farmer to submit clearer foliage photos.
4. **Dialect Diversity:** While Gnani AI provides high Indic speech accuracy, extreme rural colloquialisms or heavy tractor background noise may necessitate re-recording in quieter environments.

---

## 16. Verification & Test Suite

AgriMind AI includes a comprehensive 31-test automated suite covering all modules:
```bash
pytest tests/ -v
```
**Test Results: 31 passed / 31 total (100%)**
- `tests/test_gemini_detection_and_connectivity.py`: 9 passed
- `tests/test_gnani_live_and_robustness.py`: 11 passed
- `tests/test_agrimind_v2.py`: 11 passed
- Frontend Production Build: `npm run build` exits with code 0.
