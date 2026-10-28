import os
import io
import base64
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.db.init_db import init_db

init_db()
client = TestClient(app)

# Helper function to generate valid sample Base64 JPEG
def create_sample_jpeg_b64(width=100, height=100, color="green") -> str:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

# Helper function to generate valid sample Base64 PNG
def create_sample_png_b64(width=100, height=100, color="green") -> str:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

@pytest.fixture
def auth_headers():
    signup_payload = {
        "email": "agentfarmer@agrimind.ai",
        "password": "Password123!",
        "full_name": "Agent Farmer",
        "role": "farmer"
    }
    res = client.post("/api/v1/auth/signup", json=signup_payload)
    if res.status_code == 201:
        token = res.json()["access_token"]
    else:
        login_res = client.post("/api/v1/auth/login", json={"email": "agentfarmer@agrimind.ai", "password": "Password123!"})
        token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# 1. Unauthenticated request rejection (401)
def test_unauthenticated_chat_rejected():
    res = client.post("/api/v1/agent/chat", json={"message": "Hello AI Agronomist"})
    assert res.status_code == 401

# 2. Authenticated text chat
def test_authenticated_chat_text_query(auth_headers):
    res = client.post("/api/v1/agent/chat", json={"message": "What is proper crop rotation?"}, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert data["tool_used"] == "agri_assistant_chat"

# 3. Missing GEMINI_API_KEY activates explicit DEMO/MOCK mode with is_mock=True
def test_missing_api_key_mock_mode(auth_headers, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    img_b64 = create_sample_jpeg_b64()
    
    res = client.post("/api/v1/agent/chat", json={
        "message": "Diagnose this leaf photo",
        "image_b64": img_b64
    }, headers=auth_headers)

    assert res.status_code == 200
    data = res.json()
    assert data["tool_used"] == "disease_diagnosis_tool"
    assert data["assessment"] is not None
    assert data["assessment"]["is_mock"] is True
    assert data["assessment"]["possible_condition"] != ""
    assert data["assessment"]["assessment_level"] in ["Likely", "Possible", "Uncertain"]

# 4. Invalid image type rejection (400) - e.g., GIF format
def test_invalid_image_type_rejected(auth_headers):
    # Create GIF image
    img = Image.new("RGB", (50, 50), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="GIF")
    gif_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    res = client.post("/api/v1/agent/chat", json={
        "message": "Check this image",
        "image_b64": gif_b64
    }, headers=auth_headers)

    assert res.status_code == 400
    assert "Unsupported image format" in res.json()["detail"]

# 5. Corrupted/invalid Base64 image rejection (400)
def test_corrupted_image_rejected(auth_headers):
    res = client.post("/api/v1/agent/chat", json={
        "message": "Check corrupted file",
        "image_b64": "NotValidBase64Data!@#$%^&*"
    }, headers=auth_headers)

    assert res.status_code == 400
    assert "Image validation failed" in res.json()["detail"]

# 6. Oversized image rejection (400)
def test_oversized_image_rejected(auth_headers, monkeypatch):
    # Mock max size limit to 100 bytes for testing limit enforcement
    import app.modules.agent.image_validator as validator
    monkeypatch.setattr(validator, "MAX_IMAGE_SIZE_BYTES", 100)
    
    img_b64 = create_sample_jpeg_b64(width=200, height=200)

    res = client.post("/api/v1/agent/chat", json={
        "message": "Huge image",
        "image_b64": img_b64
    }, headers=auth_headers)

    assert res.status_code == 400
    assert "exceeds maximum permitted limit" in res.json()["detail"]

# 7. Farm & Crop Ownership Authorization Validation (403)
def test_farm_ownership_authorization(auth_headers):
    res = client.post("/api/v1/agent/chat", json={
        "message": "Diagnose my crop",
        "farm_id": "non-existent-or-other-user-farm-id"
    }, headers=auth_headers)

    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]

# 8. Disease Report Persistence & Reports Lookup
def test_disease_report_persistence(auth_headers, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    img_b64 = create_sample_png_b64()

    # Create farm first
    farm_res = client.post("/api/v1/farms", json={
        "name": "Validation Test Farm",
        "location": "Mandya",
        "area_acres": 2.0,
        "soil_type": "Loam"
    }, headers=auth_headers)
    farm_id = farm_res.json()["id"]

    # Send chat diagnosis request with farm_id
    res = client.post("/api/v1/agent/chat", json={
        "message": "Diagnose my leaf",
        "image_b64": img_b64,
        "farm_id": farm_id
    }, headers=auth_headers)

    assert res.status_code == 200
    report_id = res.json()["report_id"]
    assert report_id is not None

    # Fetch user reports
    reports_res = client.get("/api/v1/agent/reports", headers=auth_headers)
    assert reports_res.status_code == 200
    reports = reports_res.json()
    assert len(reports) >= 1
    found = any(r["id"] == report_id for r in reports)
    assert found is True

# 9. Real Gemini API failure handling (502 / 500) without exposing secrets
def test_gemini_api_failure_handling(auth_headers, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "INVALID_TEST_KEY_12345")
    img_b64 = create_sample_jpeg_b64()

    res = client.post("/api/v1/agent/chat", json={
        "message": "Diagnose this leaf photo",
        "image_b64": img_b64
    }, headers=auth_headers)

    # Must return controlled 502 Bad Gateway application error without leaking secrets or fake diagnosis
    assert res.status_code == 502
    assert "Crop disease diagnosis service is temporarily unavailable" in res.json()["detail"]
    assert "INVALID_TEST_KEY" not in res.json()["detail"]
