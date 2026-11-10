# AgriMind AI — Gnani AI Internship Challenge Video Demonstration Script

**Project:** AgriMind AI – Agentic Smart Agriculture Assistant  
**Event:** The Great Indian AI Internship Challenge by Gnani AI  
**Author / Presenter:** Karthik Sonaveni  
**Institution:** Bharat Institute of Engineering and Technology (BIET)  
**Target Video Duration:** 2 minutes 30 seconds (Within strict 2:00 – 3:00 limit)  
**Language / Delivery:** Clear, simple, natural Indian English  
**Core Focus:** Live Gnani AI Voice Stack Integration (Prisma STT + Timbre TTS)  

---

## Technical Setup Before Recording
1. **Backend Running:** `uvicorn app.main:app --host 127.0.0.1 --port 8000` (FastAPI backend active).
2. **Frontend Running:** `npm run dev` in `frontend/` (Dashboard loaded at `http://localhost:5173`).
3. **Environment Verified:** Live Gnani API credentials configured in `.env` (`GNANI_MODE=LIVE`).
4. **Verified Language & Voice Combination:** Telugu (`te-IN`), Voice `Avinash` (Gnani Timbre v3.0, 48kHz audio).
5. **Sample Leaf Photo Ready:** High-resolution tomato leaf image with foliar spotting ready for upload.
6. **Screen Recording Layout:** 1080p full screen with clean browser window showing AgriMind AI.

---

## Detailed Step-by-Step Script & Visual Cues

### [0:00 – 0:25] Segment 1: Introduction & Problem Context
* **Timing:** 25 seconds
* **Visual on Screen:** AgriMind AI Dashboard home screen. Point mouse cursor to the top header showing the active badge: **`Gnani Voice: Live (Prisma/Timbre)`** and the language selector dropdown.

> **Spoken Script (Word-for-Word):**  
> "Hello everyone.  
> 
> Today, I am presenting my project, **AgriMind AI – Agentic Smart Agriculture Assistant**.  
> 
> The main idea behind this project is to help farmers access agricultural information through their own language and voice. For Indian smallholders, reading complex English dashboards is a major barrier.  
> 
> For this, I integrated Gnani AI's speech technologies into AgriMind."

---

### [0:25 – 1:05] Segment 2: Gnani Prisma Speech-to-Text (STT) Live Demonstration
* **Timing:** 40 seconds
* **Visual on Screen:**
  1. Open the language selector at the top and select **Telugu (తెలుగు)**.
  2. Navigate to the **AI Assistant** tab.
  3. Click the round green **Microphone** button. The browser prompts for recording permission.
  4. Speak the designated Telugu query clearly into the microphone:
     > *"నా టమాటా పంటకు పూత దశలో ఏ ఎరువులు వాడాలి?"*  
     > *(Transliteration: Naa tomato pantaku pootha dashalo ae eruvulu vaadaali?)*  
     > *(English meaning: Which fertilizer should I use for my tomato crop during flowering stage?)*
  5. Click the button again to stop recording.
  6. The transcription animation triggers. In less than 1.5 seconds, the exact Telugu text appears in the input box.

> **Spoken Script (Word-for-Word):**  
> "Let us look at how the voice query works.  
> 
> First, I select Telugu from the language menu. I open the AI Assistant and click the microphone button to ask a question:  
> 
> *'నా టమాటా పంటకు పూత దశలో ఏ ఎరువులు వాడాలి?'*  
> 
> When the farmer speaks in Telugu, the recorded audio is standardized to a 16 kilohertz WAV container and sent to **Gnani AI Prisma Speech-to-Text** at `api.vachana.ai/stt/v3`.  
> 
> Prisma converts the voice input into text. As you can see on screen, the Telugu transcript is accurate. AgriMind then routes this question into our ICAR STCR fertilizer engine to prepare a relevant recommendation."

---

### [1:05 – 1:50] Segment 3: Gnani Timbre Text-to-Speech (TTS) Live Audio Playback
* **Timing:** 45 seconds
* **Visual on Screen:**
  1. AgriMind displays the generated response card in Telugu with balanced N-P-K nutrient guidance (13:0:45 potassium nitrate and organic neem cake for tomato flowering stage).
  2. The assistant automatically streams the spoken response using Gnani Timbre.
  3. Click the **`🔊 Play Response`** button so the system audio plays clearly through the video recording.
  4. The Telugu voice **Avinash** speaks fluently and naturally in official Gnani Timbre v3.0 quality.
  5. Highlight the response headers showing `X-Audio-Provider: GNANI_TIMBRE` and `X-Audio-Mock: False`.

> **Spoken Script (Word-for-Word):**  
> "Now, instead of providing only a text response, AgriMind sends the answer to **Gnani AI Timbre Text-to-Speech**.  
> 
> Timbre converts the response into spoken audio using the official `timbre-v3.0` model with the verified **Avinash** Telugu voice.  
> 
> Let us listen to the actual generated speech:  
> *(Allow 6–8 seconds of spoken Telugu audio to play through system audio)*  
> 
> Timbre delivers 48 kilohertz high-fidelity speech. Dynamic speed clamping between 0.85 and 1.15 keeps the delivery steady and natural. This helps farmers listen to agricultural information instead of reading long instructions."

---

### [1:50 – 2:15] Segment 4: Google Gemini Vision Multi-modal Image Analysis
* **Timing:** 25 seconds
* **Visual on Screen:**
  1. Click the **Attach Leaf Photo** paperclip icon in the chat.
  2. Upload the sample tomato leaf with early blight spots.
  3. The structured diagnosis card appears instantly showing:
     - Identified Crop: Tomato
     - Condition: Early Blight (*Alternaria solani*)
     - Assessment Level: Likely | Severity: Moderate
     - Observations: Concentric target-board brown foliar lesions
     - Recommended Action: Organic copper oxychloride spray (ICAR-aligned)
     - Regulatory Disclaimer: Advisory decision support requiring field validation.

> **Spoken Script (Word-for-Word):**  
> "AgriMind also uses **Google Gemini Vision** to analyse crop images and provide possible crop health observations.  
> 
> Here, when a farmer uploads a photo of an infected leaf, Gemini 2.5 Flash detects the foliar lesions and identifies potential early blight, suggesting organic copper remedies alongside a strict expert confirmation disclaimer.  
> 
> In this architecture, Gnani AI handles voice interaction, while Gemini Vision handles image-based analysis."

---

### [2:15 – 2:35] Segment 5: Conclusion & Summary
* **Timing:** 20 seconds
* **Visual on Screen:** Return to the full dashboard view showing the integrated workflow (Voice query transcript, spoken audio playback control, and disease diagnosis card). Display the GitHub repository URL (`https://github.com/Karthik-9465/agrimind.git`) and Gnani Challenge banner.

> **Spoken Script (Word-for-Word):**  
> "Through this project, I have integrated Gnani AI's Prisma Speech-to-Text and Timbre Text-to-Speech into a practical agriculture use case.  
> 
> By combining Indic voice accessibility with scientific agricultural engines, our goal is to make agricultural information more accessible to Indian farmers through voice interaction in their preferred languages.  
> 
> Thank you."

---

## Demonstration Checklist & Verification Rules
- [x] **Timing Guarantee:** Total rehearsed runtime is **2 minutes 35 seconds** (comfortably within the 2:00–3:00 boundary).
- [x] **Authentic Audio:** Audio is fetched live from Gnani Timbre `v3.0` endpoint. No browser `window.speechSynthesis` or synthetic mock chime is presented as real audio.
- [x] **Verified Voice & Language:** Telugu (`te-IN`) with `Avinash` voice; tested and confirmed operational.
- [x] **Explicit Role Separation:** Gnani AI handles Indic voice STT/TTS; Gemini Vision handles foliar leaf image diagnostics; deterministic engines handle FAO-56 irrigation and ICAR fertilizer calculations.
- [x] **Zero Credential Exposure:** Video never displays terminal `.env` files or secret tokens.
