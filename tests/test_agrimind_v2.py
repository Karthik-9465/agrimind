import os
import sys
import io
import wave
import pytest
from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.modules.agent.voice_service import GnaniVoiceService
from app.modules.agent.tools.irrigation import calculate_irrigation_schedule, estimate_reference_evapotranspiration
from app.modules.agent.tools.fertilizer import get_fertilizer_recommendation
from app.modules.agent.tools.weather import get_weather_forecast
from app.modules.agent.tools.market import get_market_prices
from app.modules.agent.tools.knowledge import search_crop_knowledge
from app.modules.agent.engine import agent_engine
from app.modules.agent.schemas import ChatRequest

client = TestClient(app)

# -----------------------------------------------------------------------------
# 1. Gnani AI Voice Service Tests
# -----------------------------------------------------------------------------
def create_test_wav_bytes(duration=0.5, rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"\x00\x00" * int(rate * duration))
    return buf.getvalue()

def test_gnani_stt_mock_mode(monkeypatch):
    monkeypatch.setenv("GNANI_MODE", "DEMO")
    audio_sample = create_test_wav_bytes(0.5)
    res = GnaniVoiceService.transcribe_audio(audio_sample, language="te")
    assert res["is_mock"] is True
    assert "టమాటా" in res["text"] or "fertilizer" in res["text"].lower()
    assert res["language_detected"] == "te-IN"
    assert res["confidence"] > 0.9

def test_gnani_tts_mock_mode(monkeypatch):
    monkeypatch.setenv("GNANI_MODE", "DEMO")
    audio_bytes, content_type, is_mock, provider = GnaniVoiceService.synthesize_speech("నమస్కారం", language="te")
    assert is_mock is True
    assert len(audio_bytes) > 0
    assert content_type == "audio/wav"

def test_gnani_voice_endpoints(monkeypatch):
    monkeypatch.setenv("GNANI_MODE", "DEMO")
    wav_content = create_test_wav_bytes(0.5)
    files = {"file": ("test_voice.wav", io.BytesIO(wav_content), "audio/wav")}
    response = client.post("/api/v1/agent/voice/transcribe", files=files, data={"language": "hi"})
    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert data["language_detected"] == "hi-IN"
    assert data["is_mock"] is True

    # Test synthesize endpoint
    tts_payload = {"text": "फसल में सिंचाई करें", "language": "hi", "speed": 1.0}
    tts_res = client.post("/api/v1/agent/voice/synthesize", json=tts_payload)
    assert tts_res.status_code == 200
    assert len(tts_res.content) > 0

# -----------------------------------------------------------------------------
# 2. Smart Irrigation FAO-56 Penman-Monteith Tests
# -----------------------------------------------------------------------------
def test_fao56_irrigation_calculations():
    # ETo estimation
    eto = estimate_reference_evapotranspiration(temp_c=32.0)
    assert eto >= 4.0

    # Tomato flowering stage (high Kc = 1.15)
    res_tomato = calculate_irrigation_schedule(
        crop_name="tomato",
        soil_type="Clay Loam",
        growth_stage="flowering",
        temp_c=30.0,
        field_area_acres=2.5
    )
    assert res_tomato.crop == "Tomato"
    assert "mm/day" in res_tomato.water_requirement
    assert "Liters" in res_tomato.water_requirement
    assert res_tomato.is_mock is False

    # Rainfall deduction test
    res_rain = calculate_irrigation_schedule(
        crop_name="cotton",
        soil_type="Black Clay",
        growth_stage="vegetative",
        rainfall_mm=25.0
    )
    assert "Hold all irrigation" in res_rain.recommended_action
    assert "Replenished" in res_rain.soil_moisture_status

# -----------------------------------------------------------------------------
# 3. Fertilizer ICAR STCR Rule Tests
# -----------------------------------------------------------------------------
def test_icar_stcr_fertilizer_engine():
    # Basal stage for Paddy with Low Soil Nitrogen (+25% N adjustment)
    res_paddy = get_fertilizer_recommendation(
        crop_name="rice",
        soil_type="Clay",
        growth_stage="basal",
        soil_n_status="low",
        field_area_acres=3.0
    )
    assert "Rice" in res_paddy.crop
    assert res_paddy.growth_stage == "Basal"
    assert len(res_paddy.recommendation) > 0
    # Check that DAP or Urea commercial fertilizers are listed with area scaling
    rec_text = " ".join(res_paddy.recommendation)
    assert "DAP" in rec_text or "Urea" in rec_text
    assert "Total for 3.0 ac" in rec_text
    assert "FYM" in res_paddy.organic_option or "Dhaincha" in res_paddy.organic_option

    # Acidic soil pH amendment check
    res_acidic = get_fertilizer_recommendation(
        crop_name="tomato",
        soil_type="Sandy",
        growth_stage="vegetative",
        soil_ph=5.2
    )
    assert "Acidic soil" in res_acidic.soil_considerations
    assert "Lime" in res_acidic.soil_considerations

# -----------------------------------------------------------------------------
# 4. Live Weather & Open-Meteo Tests
# -----------------------------------------------------------------------------
def test_weather_retrieval():
    weather = get_weather_forecast(location="Hyderabad, India")
    assert weather.location != ""
    assert weather.temperature_c > -10.0
    assert weather.humidity_percent >= 0
    assert weather.forecast != ""
    assert weather.source in ["Open-Meteo Live Meteorology", "OpenWeatherMap (Live)", "DEMO / MOCK", "DEMO / MOCK (Offline Fallback)", "OpenWeatherMap"]

# -----------------------------------------------------------------------------
# 5. Market Price APMC Mandi Tests
# -----------------------------------------------------------------------------
def test_apmc_market_prices():
    market = get_market_prices(commodity="chilli", state_or_mandi="Guntur")
    assert "Chilli" in market.commodity
    assert market.modal_price > 10000.0
    assert "Guntur" in market.mandi
    assert market.unit == "₹ / quintal"

# -----------------------------------------------------------------------------
# 6. RAG Knowledge Store Tests
# -----------------------------------------------------------------------------
def test_rag_knowledge_search():
    res = search_crop_knowledge("fall armyworm whorl feeding maize")
    assert "Maize" in res.source_document or "Fall Armyworm" in res.relevant_section or "Spodoptera" in res.answer
    assert res.source_metadata.get("status") != "not_found"

# -----------------------------------------------------------------------------
# 7. Agent Multilingual Intent Routing Tests
# -----------------------------------------------------------------------------
def test_agent_multilingual_routing():
    # Telugu Language Request
    req_te = ChatRequest(message="టమాటా పంటకు ఎరువులు ఏమి వేయాలి?", language="te")
    reply, tool, disease, irrigation, fertilizer, weather, market, knowledge = agent_engine.process_request(req_te)
    assert tool == "fertilizer_rules_engine"
    assert fertilizer is not None
    assert "టమాటా" in reply or "ఎరువుల" in reply

    # Hindi Language Request
    req_hi = ChatRequest(message="टमाटर में सिंचाई कब और कितनी करनी चाहिए?", language="hi")
    reply_hi, tool_hi, _, irrigation_hi, _, _, _, _ = agent_engine.process_request(req_hi)
    assert tool_hi == "irrigation_rules_engine"
    assert irrigation_hi is not None
    assert "जल आवश्यकता" in reply_hi or "सिंचाई" in reply_hi

# -----------------------------------------------------------------------------
# 8. Direct Dashboard REST Endpoints Tests
# -----------------------------------------------------------------------------
def test_direct_dashboard_endpoints():
    # Weather
    w_res = client.get("/api/v1/agent/weather?location=Guntur")
    assert w_res.status_code == 200

    # Irrigation calculation
    irr_res = client.post("/api/v1/agent/irrigation/calculate", data={
        "crop": "Cotton",
        "soil_type": "Black Clay",
        "growth_stage": "mid_season",
        "location": "Rajkot",
        "irrigation_method": "drip",
        "field_area_acres": 4.0
    })
    assert irr_res.status_code == 200
    assert irr_res.json()["crop"] == "Cotton"

    # Fertilizer calculation
    fert_res = client.post("/api/v1/agent/fertilizer/calculate", data={
        "crop": "Tomato",
        "soil_type": "Loam",
        "growth_stage": "basal",
        "field_area_acres": 2.0,
        "soil_ph": 6.8
    })
    assert fert_res.status_code == 200
    assert fert_res.json()["crop"] == "Tomato"

    # Market prices
    mkt_res = client.get("/api/v1/agent/market/prices?commodity=cotton")
    assert mkt_res.status_code == 200
    assert "Cotton" in mkt_res.json()["commodity"]

# -----------------------------------------------------------------------------
# 9. Integrations Health State Machine Endpoints
# -----------------------------------------------------------------------------
def test_integrations_health_endpoints():
    res = client.get("/api/v1/health/integrations")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "providers" in data
    assert "gemini_vision" in data["providers"]
    assert "gnani_ai" in data["providers"]
    assert data["providers"]["gemini_vision"]["mode"] in ["LIVE", "CONNECTED", "DEMO", "NOT_CONFIGURED", "AUTH_FAILED", "CONFIGURED_NOT_TESTED", "CONNECTION_ERROR", "MODEL_ERROR"]
    assert data["providers"]["gnani_ai"]["mode"] in ["LIVE", "DEMO", "NOT_CONFIGURED", "AUTH_FAILED"]

    # Test alias
    alias_res = client.get("/api/health/integrations")
    assert alias_res.status_code == 200
    assert alias_res.json()["providers"]["weather"]["mode"] == "LIVE"

