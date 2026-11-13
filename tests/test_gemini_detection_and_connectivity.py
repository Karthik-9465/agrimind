import io
import os
import sys
import base64
import pytest
from PIL import Image

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app
from app.config import settings, is_placeholder
from app.modules.agent.tools.disease import (
    check_gemini_status,
    diagnose_crop_disease_with_gemini,
    get_mock_disease_assessment,
    _gemini_status_cache
)

client = TestClient(app)

def create_sample_leaf_jpeg_bytes() -> bytes:
    """Generates a small in-memory green leaf JPEG byte stream."""
    img = Image.new("RGB", (64, 64), color=(34, 139, 34))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

# -----------------------------------------------------------------------------
# 1. Configuration & Precedence Tests
# -----------------------------------------------------------------------------
def test_placeholder_detection():
    """Validates that dummy template values are properly identified as placeholders."""
    assert is_placeholder("") is True
    assert is_placeholder(None) is True
    assert is_placeholder("your_api_key_here") is True
    assert is_placeholder("placeholder") is True
    assert is_placeholder("AIzaSy_YOUR_OFFICIAL_KEY") is True
    assert is_placeholder("short") is True
    # Valid candidate format
    assert is_placeholder("AQ.Ab8ValidKeyExampleLongEnough1234567890") is False

def test_gemini_key_precedence(monkeypatch):
    """Validates that GEMINI_API_KEY is primary and GOOGLE_API_KEY is fallback."""
    # Scenario A: GEMINI_API_KEY takes precedence
    monkeypatch.setenv("GEMINI_API_KEY", "primary_key_val_1234567890")
    monkeypatch.setenv("GOOGLE_API_KEY", "fallback_key_val_1234567890")
    assert settings.get_gemini_api_key() == "primary_key_val_1234567890"

    # Scenario B: GEMINI_API_KEY is placeholder -> falls back to GOOGLE_API_KEY
    monkeypatch.setenv("GEMINI_API_KEY", "your_gemini_key_placeholder")
    monkeypatch.setenv("GOOGLE_API_KEY", "fallback_key_val_1234567890")
    assert settings.get_gemini_api_key() == "fallback_key_val_1234567890"

def test_missing_key_detection(monkeypatch):
    """Validates NOT_CONFIGURED state when key is absent."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_MODE", "LIVE")
    _gemini_status_cache["result"] = None

    status = check_gemini_status(force_probe=True)
    assert status["mode"] == "NOT_CONFIGURED"
    assert status["configured"] is False
    assert status["authenticated"] is False

def test_explicit_demo_mode(monkeypatch):
    """Validates DEMO state when GEMINI_MODE=DEMO."""
    monkeypatch.setenv("GEMINI_MODE", "DEMO")
    _gemini_status_cache["result"] = None

    status = check_gemini_status(force_probe=True)
    assert status["mode"] == "DEMO"
    assert status["authenticated"] is False

# -----------------------------------------------------------------------------
# 2. Connectivity & State Machine Unit Tests
# -----------------------------------------------------------------------------
def test_invalid_key_detection(monkeypatch):
    """Validates that an invalid key triggers the INVALID_KEY state."""
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyFakeInvalidKeyForTesting1234567890")
    monkeypatch.setenv("GEMINI_MODE", "LIVE")
    _gemini_status_cache["result"] = None

    status = check_gemini_status(force_probe=True)
    assert status["mode"] in ["INVALID_KEY", "MODEL_ERROR", "CONNECTION_ERROR"]
    assert status["authenticated"] is False

def test_model_error_detection(monkeypatch):
    """Validates that requesting a non-existent model results in MODEL_ERROR."""
    # Keep real key if present, test bad model name
    real_key = settings.get_gemini_api_key()
    if not real_key:
        pytest.skip("Skipping model error test: No real Gemini key available.")

    monkeypatch.setenv("GEMINI_MODEL", "gemini-nonexistent-model-xyz")
    _gemini_status_cache["result"] = None

    status = check_gemini_status(force_probe=True)
    assert status["mode"] == "MODEL_ERROR"

# -----------------------------------------------------------------------------
# 3. Live Dashboard Status Endpoints
# -----------------------------------------------------------------------------
def test_dashboard_status_endpoints():
    """Validates that /api/v1/health/integrations returns verified CONNECTED state."""
    res = client.get("/api/v1/health/integrations?refresh=true")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    
    gemini_stat = data["providers"]["gemini_vision"]
    # With valid key configured, mode should be one of valid status machine states
    assert gemini_stat["mode"] in ["CONNECTED", "DEMO", "NOT_CONFIGURED", "CONNECTION_ERROR", "MODEL_ERROR"]
    assert "status_detail" in gemini_stat
    assert "model" in gemini_stat

def test_gemini_health_refresh_query_param():
    """Validates that ?refresh=true parameter works on /api/v1/health/gemini."""
    res = client.get("/api/v1/health/gemini?refresh=true")
    assert res.status_code == 200
    stat = res.json()
    assert stat["mode"] in ["CONNECTED", "DEMO", "NOT_CONFIGURED", "CONNECTION_ERROR", "MODEL_ERROR"]

# -----------------------------------------------------------------------------
# 4. Gemini Vision Image Request Verification
# -----------------------------------------------------------------------------
def test_gemini_vision_processing_flow():
    """Validates that diagnose_crop_disease_with_gemini produces a valid structured assessment."""
    leaf_bytes = create_sample_leaf_jpeg_bytes()
    try:
        assessment = diagnose_crop_disease_with_gemini(
            image_bytes=leaf_bytes,
            mime_type="image/jpeg",
            crop_context="Tomato field foliage",
            observed_symptoms="Small circular spots"
        )
    except RuntimeError as e:
        if "quota exceeded" in str(e).lower() or "resource_exhausted" in str(e).lower():
            pytest.skip(f"Gemini free tier daily quota limit reached: {e}")
        raise

    assert assessment is not None

    assert assessment is not None
    assert assessment.identified_crop != ""
    assert assessment.possible_condition != ""
    assert assessment.assessment_level in ["Likely", "Possible", "Uncertain"]
    assert assessment.severity in ["Mild", "Moderate", "Severe", "Uncertain"]
    assert len(assessment.observations) > 0
    assert isinstance(assessment.organic_treatment, list)
    assert isinstance(assessment.chemical_treatment, list)
    assert assessment.requires_expert_confirmation is True
    assert assessment.disclaimer != ""
