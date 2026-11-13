import os
import re
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.config import settings
from app.modules.agent.engine import agent_engine
from app.modules.agent.schemas import ChatRequest, ChatTurn

client = TestClient(app)


def _live_gemini_ready() -> bool:
    return settings.get_gemini_mode() != "DEMO" and bool(settings.get_gemini_api_key())


def assert_not_generic_welcome(reply: str):
    low = (reply or "").lower()
    assert len(low.strip()) > 30
    assert "feel free to ask any agriculture-related question" not in low
    assert "నేను మీ అగ్రిమైండ్ ai వ్యవసాయ సహాయకుడిని" not in (reply or "")
    assert "मैं आपका एग्रीमाइंड ai कृषि सहायक हूं" not in (reply or "")


@pytest.fixture
def auth_headers():
    signup_payload = {
        "email": "liveopendomain@agrimind.ai",
        "password": "Password123!",
        "full_name": "Live OpenDomain Farmer",
        "role": "farmer",
    }
    res = client.post("/api/v1/auth/signup", json=signup_payload)
    if res.status_code == 201:
        token = res.json()["access_token"]
    else:
        login_res = client.post(
            "/api/v1/auth/login",
            json={"email": "liveopendomain@agrimind.ai", "password": "Password123!"},
        )
        token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.skipif(not _live_gemini_ready(), reason="Live Gemini credentials unavailable or GEMINI_MODE=DEMO")
def test_live_telugu_and_english_examples():
    # 1. Telugu Tomato Flowering Fertilizer (MUST NOT classify as vegetative)
    r1, t1, _, _, fert1, _, _, _ = agent_engine.process_request(
        ChatRequest(message="నా టమాటా పంటకు పూత దశలో ఏ ఎరువులు వాడాలి?", language="te")
    )
    assert t1 == "fertilizer_rules_engine"
    assert fert1 is not None and fert1.crop == "Tomato" and fert1.growth_stage == "Flowering"
    assert bool(re.search(r"[\u0C00-\u0C7F]", r1))
    assert "టమాటా" in r1 or "పూత" in r1
    assert_not_generic_welcome(r1)

    # 2. Telugu Cotton Nutrients (Unknown Stage -> Cotton answer, NOT welcome greeting / NOT Tomato)
    r2, t2, *_ = agent_engine.process_request(
        ChatRequest(message="పత్తి పంటకు ప్రస్తుతం ఏ పోషకాలు అవసరం", language="te")
    )
    assert bool(re.search(r"[\u0C00-\u0C7F]", r2))
    assert "పత్తి" in r2 or "cotton" in r2.lower()
    assert_not_generic_welcome(r2)

    # 3. English Cotton Unknown Stage -> answers Cotton & asks growth stage
    r3, t3, *_ = agent_engine.process_request(
        ChatRequest(message="What nutrients does my cotton crop need at this stage?", language="en")
    )
    assert "cotton" in r3.lower()
    assert "stage" in r3.lower()
    assert_not_generic_welcome(r3)


@pytest.mark.skipif(not _live_gemini_ready(), reason="Live Gemini credentials unavailable or GEMINI_MODE=DEMO")
def test_live_unseen_topics_multilingual_and_multiturn(auth_headers):
    # 4. Black Soil Improvement
    res_soil = client.post(
        "/api/v1/agent/chat",
        json={"message": "How can I improve my black soil?", "language": "en"},
        headers=auth_headers,
    )
    assert res_soil.status_code == 200
    d_soil = res_soil.json()
    assert d_soil["tool_used"] == "agri_assistant_chat"
    assert any(w in d_soil["reply"].lower() for w in ("organic", "drainage", "soil", "gypsum", "compost", "vertisol"))
    assert_not_generic_welcome(d_soil["reply"])

    # 5. Dairy Farming Startup
    res_dairy = client.post(
        "/api/v1/agent/chat",
        json={"message": "How can I start dairy farming?", "language": "en"},
        headers=auth_headers,
    )
    assert res_dairy.status_code == 200
    d_dairy = res_dairy.json()
    assert d_dairy["tool_used"] == "agri_assistant_chat"
    assert any(w in d_dairy["reply"].lower() for w in ("dairy", "fodder", "shed", "breed", "cattle", "buffalo", "cow"))
    assert_not_generic_welcome(d_dairy["reply"])

    # 6. Completely unseen agri topic: Beekeeping
    res_bee = client.post(
        "/api/v1/agent/chat",
        json={"message": "How can farmers start apiculture beekeeping for honey alongside fruit trees?", "language": "en"},
        headers=auth_headers,
    )
    assert res_bee.status_code == 200
    d_bee = res_bee.json()
    assert d_bee["tool_used"] == "agri_assistant_chat"
    assert any(w in d_bee["reply"].lower() for w in ("bee", "hive", "colony", "honey", "pollination"))
    assert_not_generic_welcome(d_bee["reply"])

    # 7. Romanized Telugu mixed query
    res_rom = client.post(
        "/api/v1/agent/chat",
        json={"message": "na mirchi panta lo aakulu muduthunnayi em cheyali", "language": "en"},
        headers=auth_headers,
    )
    assert res_rom.status_code == 200
    d_rom = res_rom.json()
    assert d_rom["tool_used"] in ("agri_assistant_chat", "rag_knowledge_tool")
    assert any(w in d_rom["reply"].lower() for w in ("mirchi", "chilli", "మిర్చి", "thrips", "mite", "curl", "leaf", "aaku"))
    assert_not_generic_welcome(d_rom["reply"])

    # 8. Hindi unseen pest query
    res_hi = client.post(
        "/api/v1/agent/chat",
        json={"message": "बैंगन में फल और तना छेदक कीट से बचाव के उपाय बताइए?", "language": "hi"},
        headers=auth_headers,
    )
    assert res_hi.status_code == 200
    d_hi = res_hi.json()
    assert bool(re.search(r"[\u0900-\u097F]", d_hi["reply"]))
    assert "बैंगन" in d_hi["reply"] or "कीट" in d_hi["reply"]
    assert_not_generic_welcome(d_hi["reply"])

    # 9. Multi-turn crop switch (Tomato history -> Cotton current question)
    res_switch = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "What nutrients does cotton need?",
            "language": "en",
            "history": [
                {"role": "user", "content": "How can I improve tomato yield?"},
                {"role": "assistant", "content": "Ensure balanced potassium and drip moisture for tomato."},
            ],
        },
        headers=auth_headers,
    )
    assert res_switch.status_code == 200
    d_switch = res_switch.json()
    assert "cotton" in d_switch["reply"].lower()
    assert "tomato" not in d_switch["reply"].lower()
    assert_not_generic_welcome(d_switch["reply"])

    # 10. Current-information question -> transparent real-time limitation
    res_curr = client.post(
        "/api/v1/agent/chat",
        json={"message": "Can you check my PM-KISAN installment status today and live local dealer urea stock in Hubballi?", "language": "en"},
        headers=auth_headers,
    )
    assert res_curr.status_code == 200
    d_curr = res_curr.json()
    assert any(w in d_curr["reply"].lower() for w in ("cannot", "unable", "pmkisan", "official", "portal", "verify", "real-time", "live"))
    assert_not_generic_welcome(d_curr["reply"])

    # 11. Subtle non-agricultural question refusal
    res_non = client.post(
        "/api/v1/agent/chat",
        json={"message": "Write a detailed summary of the UEFA Champions League finals.", "language": "en"},
        headers=auth_headers,
    )
    assert res_non.status_code == 200
    d_non = res_non.json()
    assert d_non["tool_used"] == "input_guardrail_refusal"

