import os
import io
import base64
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.db.init_db import init_db
from app.modules.agent.tools.irrigation import calculate_irrigation_schedule
from app.modules.agent.tools.fertilizer import get_fertilizer_recommendation
from app.modules.agent.tools.weather import get_weather_forecast
from app.modules.agent.tools.market import get_market_prices
from app.modules.agent.tools.knowledge import search_crop_knowledge

init_db()
client = TestClient(app)

def create_sample_jpeg_b64() -> str:
    img = Image.new("RGB", (100, 100), color="green")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

@pytest.fixture
def auth_headers():
    signup_payload = {
        "email": "phase3farmer@agrimind.ai",
        "password": "Password123!",
        "full_name": "Phase 3 Farmer",
        "role": "farmer"
    }
    res = client.post("/api/v1/auth/signup", json=signup_payload)
    if res.status_code == 201:
        token = res.json()["access_token"]
    else:
        login_res = client.post("/api/v1/auth/login", json={"email": "phase3farmer@agrimind.ai", "password": "Password123!"})
        token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# 1. Irrigation Engine Tests
def test_irrigation_engine_valid_and_missing_inputs():
    res = calculate_irrigation_schedule(crop_name="tomato", soil_type="Clay", growth_stage="flowering", temp_c=34.0)
    assert res.crop == "Tomato"
    assert "mm/day" in res.water_requirement
    assert res.data_source == "AgriMind Rule-Based Engine"
    assert res.is_mock is False

    res_missing = calculate_irrigation_schedule(crop_name="")
    assert res_missing.water_requirement == "Insufficient Information"

# 2. Fertilizer Engine Tests
def test_fertilizer_engine_structure():
    res = get_fertilizer_recommendation(crop_name="rice", soil_type="Loam", growth_stage="basal", soil_ph=5.5)
    assert res.crop == "Rice"
    assert len(res.recommendation) > 0
    assert "Acidic soil" in res.soil_considerations
    assert "disclaimer" in res.model_dump()

# 3. Weather Service Tests
def test_weather_service_mock_mode_and_api_failure(monkeypatch):
    # Mock mode when key is absent
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    w_mock = get_weather_forecast("Mandya, India")
    assert w_mock.is_mock is True
    assert w_mock.source == "DEMO / MOCK"

    # API Failure with invalid key raises RuntimeError
    monkeypatch.setenv("OPENWEATHER_API_KEY", "INVALID_WEATHER_KEY")
    with pytest.raises(RuntimeError):
        get_weather_forecast("Mandya, India")

# 4. Market Prices Tests
def test_market_prices_demo_dataset():
    res = get_market_prices("Tomato", "Mandya")
    assert res.commodity == "Tomato"
    assert res.unit == "₹ / quintal"
    assert res.is_demo_data is True
    assert res.source == "Curated Demo APMC Dataset"
    assert res.modal_price > 0

# 5. RAG Knowledge Tool Tests
def test_rag_knowledge_search():
    res = search_crop_knowledge("tomato planting depth")
    assert res.source_document != ""
    assert res.relevant_section != "None"
    assert "depth" in res.answer.lower() or "planting" in res.answer.lower()

    res_empty = search_crop_knowledge("xyz_non_existent_term_12345")
    assert res_empty.source_metadata.get("status") == "not_found"

# 6. Agent Intent Routing Tests via API
def test_agent_routing_intents(auth_headers, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)

    # a. Irrigation Query
    res1 = client.post("/api/v1/agent/chat", json={"message": "What is the recommended irrigation schedule for my tomato crop?"}, headers=auth_headers)
    assert res1.status_code == 200
    assert res1.json()["tool_used"] == "irrigation_rules_engine"
    assert res1.json()["irrigation"] is not None

    # b. Fertilizer Query
    res2 = client.post("/api/v1/agent/chat", json={"message": "Give me a basal NPK fertilizer recommendation for rice."}, headers=auth_headers)
    assert res2.status_code == 200
    assert res2.json()["tool_used"] == "fertilizer_rules_engine"
    assert res2.json()["fertilizer"] is not None

    # c. Weather Query
    res3 = client.post("/api/v1/agent/chat", json={"message": "What is the weather forecast and rainfall advisory?"}, headers=auth_headers)
    assert res3.status_code == 200
    assert res3.json()["tool_used"] == "weather_service"
    assert res3.json()["weather"] is not None

    # d. Market Query
    res4 = client.post("/api/v1/agent/chat", json={"message": "What are current Mandi market prices for wheat?"}, headers=auth_headers)
    assert res4.status_code == 200
    assert res4.json()["tool_used"] == "mandi_market_lookup"
    assert res4.json()["market"] is not None

    # e. Knowledge RAG Query
    res5 = client.post("/api/v1/agent/chat", json={"message": "Search knowledge guide on tomato planting depth and soil preparation."}, headers=auth_headers)
    assert res5.status_code == 200
    assert res5.json()["tool_used"] == "rag_knowledge_tool"
    assert res5.json()["knowledge"] is not None

    # f. Image Priority Routing over Text Intent
    img_b64 = create_sample_jpeg_b64()
    res6 = client.post("/api/v1/agent/chat", json={
        "message": "What is the weather forecast?", # Text says weather, but image is attached!
        "image_b64": img_b64
    }, headers=auth_headers)
    assert res6.status_code == 200
    assert res6.json()["tool_used"] == "disease_diagnosis_tool"
    assert res6.json()["assessment"] is not None

# 7. Authorization Verification
def test_authorization_enforced(auth_headers):
    res = client.post("/api/v1/agent/chat", json={
        "message": "Water schedule",
        "farm_id": "other-user-invalid-farm-id"
    }, headers=auth_headers)
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]
