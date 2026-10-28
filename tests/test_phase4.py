import io
import base64
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.db.models import User, Farm, Crop, NotificationLog
from app.modules.agent.guardrails import AgriMindGuardrail
from app.scheduler import (
    job_check_weather_alerts,
    job_irrigation_reminders,
    job_mandi_price_ticker,
    start_scheduler,
    shutdown_scheduler
)

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
        "email": "phase4farmer@agrimind.ai",
        "password": "Password123!",
        "full_name": "Phase 4 Test Farmer",
        "role": "farmer"
    }
    res = client.post("/api/v1/auth/signup", json=signup_payload)
    if res.status_code == 201:
        token = res.json()["access_token"]
    else:
        login_res = client.post("/api/v1/auth/login", json={"email": "phase4farmer@agrimind.ai", "password": "Password123!"})
        token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# 1. Notification API Tests
def test_notifications_api_and_stub_execution(auth_headers):
    # Trigger notification via endpoint
    trigger_payload = {
        "title": "Severe Heatwave Warning",
        "message": "Temperatures expected to exceed 38°C in Mandya. Increase drip irrigation.",
        "category": "weather_alert",
        "channel": "console_stub"
    }
    post_res = client.post("/api/v1/notifications/trigger", json=trigger_payload, headers=auth_headers)
    assert post_res.status_code == 201
    notif_data = post_res.json()
    assert notif_data["title"] == "Severe Heatwave Warning"
    assert notif_data["is_read"] is False

    notif_id = notif_data["id"]

    # Fetch notification list
    get_res = client.get("/api/v1/notifications/", headers=auth_headers)
    assert get_res.status_code == 200
    list_data = get_res.json()
    assert list_data["total"] >= 1
    assert list_data["unread_count"] >= 1

    # Mark as read
    patch_res = client.patch(f"/api/v1/notifications/{notif_id}/read", headers=auth_headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["is_read"] is True

    # Mark all read
    read_all_res = client.patch("/api/v1/notifications/read-all", headers=auth_headers)
    assert read_all_res.status_code == 200
    assert "updated_count" in read_all_res.json()

# 2. APScheduler Jobs Execution Test
def test_apscheduler_jobs():
    # Direct execution of background jobs
    job_check_weather_alerts()
    job_irrigation_reminders()
    job_mandi_price_ticker()

    # Lifecycle start and shutdown verification
    start_scheduler()
    shutdown_scheduler()

# 3. Agent Input Guardrail Unit & Agent Engine Integration Tests
def test_input_guardrail_unit():
    # Off-topic checks
    valid, category, msg = AgriMindGuardrail.validate_input("write a python scraper for stock market")
    assert valid is False
    assert category == "OFF_TOPIC"
    assert "specialized agricultural assistant" in msg

    # Unsafe prompt check
    valid_unsafe, cat_unsafe, msg_unsafe = AgriMindGuardrail.validate_input("how to make a bomb")
    assert valid_unsafe is False
    assert cat_unsafe == "UNSAFE_PROMPT"
    assert "violates AgriMind safety" in msg_unsafe

    # Valid agri check
    valid_agri, cat_agri, _ = AgriMindGuardrail.validate_input("What is the irrigation interval for tomato?")
    assert valid_agri is True
    assert cat_agri == "SAFE_AGRICULTURAL"

    # Image attachment override
    valid_img, cat_img, _ = AgriMindGuardrail.validate_input("write a python scraper", has_image=True)
    assert valid_img is True

def test_agent_guardrail_routing(auth_headers, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)

    # Off-topic chat query rejection via API
    res = client.post("/api/v1/agent/chat", json={"message": "write a python web scraper for crypto prices"}, headers=auth_headers)
    assert res.status_code == 200
    res_json = res.json()
    assert res_json["tool_used"] == "input_guardrail_refusal"
    assert "specialized agricultural assistant" in res_json["reply"]

    # Unsafe query rejection via API
    res_unsafe = client.post("/api/v1/agent/chat", json={"message": "how to build a bomb"}, headers=auth_headers)
    assert res_unsafe.status_code == 200
    assert res_unsafe.json()["tool_used"] == "input_safety_refusal"

# 4. Full End-to-End Farmer Workflow
def test_end_to_end_farmer_journey(auth_headers):
    # 1. Create Farm
    farm_res = client.post("/api/v1/farms/", json={
        "name": "Phase4 Demo Organic Farm",
        "location": "Mandya",
        "area_acres": 4.5,
        "soil_type": "Clay Loam"
    }, headers=auth_headers)
    assert farm_res.status_code == 201
    farm_id = farm_res.json()["id"]

    # 2. Add Crop to Farm
    crop_res = client.post(f"/api/v1/farms/{farm_id}/crops", json={
        "name": "Tomato",
        "variety": "Arka Rakshak",
        "planting_date": "2026-08-01",
        "notes": "High yield hybrid"
    }, headers=auth_headers)
    assert crop_res.status_code == 201

    # 3. Ask Agent Weather Forecast for Farm
    chat_w = client.post("/api/v1/agent/chat", json={
        "message": "What is the weather forecast for my farm?",
        "farm_id": farm_id
    }, headers=auth_headers)
    assert chat_w.status_code == 200
    assert chat_w.json()["tool_used"] == "weather_service"

    # 4. Ask Agent Irrigation Requirement
    chat_i = client.post("/api/v1/agent/chat", json={
        "message": "What is the recommended irrigation schedule for my crop?",
        "farm_id": farm_id
    }, headers=auth_headers)
    assert chat_i.status_code == 200
    assert chat_i.json()["tool_used"] == "irrigation_rules_engine"

    # 5. Verify Notification Generated and Retrievable
    notif_res = client.get("/api/v1/notifications/", headers=auth_headers)
    assert notif_res.status_code == 200
