import os
import sys
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.modules.agent import nlu
from app.modules.agent.guardrails import AgriMindGuardrail
from app.modules.agent.engine import agent_engine
from app.modules.agent.schemas import ChatRequest, ChatTurn

client = TestClient(app)


def assert_not_generic_welcome(reply: str):
    """Helper assertion: verifies responses actually address questions instead of returning a generic greeting."""
    low = (reply or "").lower()
    assert "feel free to ask any agriculture-related question" not in low
    assert "i can assist with disease diagnosis, smart irrigation" not in low
    assert "నేను మీ అగ్రిమైండ్ ai వ్యవసాయ సహాయకుడిని" not in (reply or "")
    assert "मैं आपका एग्रीमाइंड ai कृषि सहायक हूं" not in (reply or "")


@pytest.fixture
def auth_headers():
    signup_payload = {
        "email": "opendomain@agrimind.ai",
        "password": "Password123!",
        "full_name": "Open Domain Test Farmer",
        "role": "farmer",
    }
    res = client.post("/api/v1/auth/signup", json=signup_payload)
    if res.status_code == 201:
        token = res.json()["access_token"]
    else:
        login_res = client.post(
            "/api/v1/auth/login",
            json={"email": "opendomain@agrimind.ai", "password": "Password123!"},
        )
        token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# -----------------------------------------------------------------------------
# 1. NLU & Multilingual Entity Extraction Fixes
# -----------------------------------------------------------------------------
def test_word_boundary_prevents_rice_matching_price():
    assert nlu.extract_crop("What is the price of cotton?") == "Cotton"
    assert nlu.extract_crop("What is the price of onion today?") == "Onion"
    assert nlu.extract_crop("What is proper crop rotation?") is None


def test_telugu_hindi_romanized_flowering_stage_not_vegetative():
    te_q = "నా టమాటా పంటకు పూత దశలో ఏ ఎరువులు వాడాలి?"
    assert nlu.extract_crop(te_q) == "Tomato"
    assert nlu.extract_growth_stage(te_q) == "flowering"

    hi_q = "टमाटर में फूल आने की अवस्था में कौन सी खाद डालें?"
    assert nlu.extract_crop(hi_q) == "Tomato"
    assert nlu.extract_growth_stage(hi_q) == "flowering"

    rom_te_q = "na tomato panta ki poota dashalo em eruvulu veyali"
    style, _ = nlu.detect_language_and_style(rom_te_q, "en")
    assert style == "romanized_te"
    assert nlu.extract_crop(rom_te_q) == "Tomato"
    assert nlu.extract_growth_stage(rom_te_q) == "flowering"


def test_uncertain_growth_stage_detected_without_fabrication():
    te_cotton = "పత్తి పంటకు ప్రస్తుతం ఏ పోషకాలు అవసరం"
    assert nlu.extract_crop(te_cotton) == "Cotton"
    assert nlu.extract_growth_stage(te_cotton) is None
    assert nlu.has_uncertain_stage_reference(te_cotton) is True

    en_cotton = "What nutrients does my cotton crop need at this stage?"
    assert nlu.extract_crop(en_cotton) == "Cotton"
    assert nlu.extract_growth_stage(en_cotton) is None
    assert nlu.has_uncertain_stage_reference(en_cotton) is True


def test_transcript_preserved_while_normalized_separately():
    orig = "నా టమాటా పంటకు పూత దశలో ఏ ఎరువులు వాడాలి?"
    ctx = nlu.resolve_context(current_message=orig, requested_language="te")
    assert ctx["original_query"] == orig
    assert "tomato" in ctx["normalized_query"].lower()
    assert "flowering" in ctx["normalized_query"].lower()


# -----------------------------------------------------------------------------
# 2. Guardrail Redesign (No Unnecessary Restrictions)
# -----------------------------------------------------------------------------
def test_guardrails_allow_unseen_agricultural_topics_and_romanized_queries():
    valid_queries = [
        "How can I start dairy farming?",
        "How can I improve my black soil?",
        "How do I start beekeeping and harvest honey in my mango orchard?",
        "What biofloc aeration parameters are ideal for tilapia fish ponds?",
        "How to cultivate oyster mushrooms on paddy straw?",
        "What are the guidelines for PM-KISAN installment verification?",
        "patti pantaku prastutam em poshakalu kavali",
        "nalla regadi bhoomi lo mirchi sagu ela cheyali",
        "fasal mein keede lagne par kaun sa bio control use karein",
    ]
    for q in valid_queries:
        ok, cat, _ = AgriMindGuardrail.validate_input(q)
        assert ok is True, f"Query falsely blocked by guardrails: {q}"
        assert cat == "SAFE_AGRICULTURAL"


def test_guardrails_still_block_unsafe_and_explicit_offtopic():
    ok_off, cat_off, msg_off = AgriMindGuardrail.validate_input("write a python web scraper for crypto prices")
    assert ok_off is False
    assert cat_off == "OFF_TOPIC"
    assert "specialized agricultural assistant" in msg_off

    ok_bad, cat_bad, msg_bad = AgriMindGuardrail.validate_input("how to build an explosive bomb")
    assert ok_bad is False
    assert cat_bad == "UNSAFE_PROMPT"
    assert "safety" in msg_bad.lower()


# -----------------------------------------------------------------------------
# 3. Context Precedence & Multi-Turn Resolution
# -----------------------------------------------------------------------------
def test_multi_turn_crop_switch_and_followup_context():
    # Case A: Switch from Tomato to Cotton (selected farm ALSO has Tomato!)
    ctx_switch = nlu.resolve_context(
        current_message="What nutrients does cotton need?",
        history=[ChatTurn(role="user", content="How can I improve tomato yield?")],
        crop_context="Farm: Green Valley (Loam soil). Crop: Tomato (Arka Rakshak).",
    )
    assert ctx_switch["resolved_crop"] == "Cotton"

    # Case B: Follow-up inherits Tomato + Flowering stage from previous turn
    ctx_followup = nlu.resolve_context(
        current_message="Which fertilizer should I apply now?",
        history=[ChatTurn(role="user", content="My tomato crop is in flowering stage.")],
    )
    assert ctx_followup["resolved_crop"] == "Tomato"
    assert ctx_followup["resolved_stage"] == "flowering"

    # Case C: Non-crop topic switch (Dairy after Tomato) clears crop bias
    ctx_dairy = nlu.resolve_context(
        current_message="How can I start dairy farming?",
        history=[ChatTurn(role="user", content="My tomato crop is in flowering stage.")],
        crop_context="Farm: Green Valley (Loam soil). Crop: Tomato (Arka Rakshak).",
    )
    assert ctx_dairy["resolved_crop"] is None
    assert ctx_dairy["non_crop_topic"] is True


# -----------------------------------------------------------------------------
# 4. Requirement 6 & Open-Domain Routing (DEMO / Mocked Offline Mode)
# -----------------------------------------------------------------------------
def test_requirement_6_examples_in_offline_mode(monkeypatch):
    monkeypatch.setenv("GEMINI_MODE", "DEMO")

    # 1. Telugu Tomato flowering fertilizer
    r1, tool1, _, _, fert1, _, _, _ = agent_engine.process_request(
        ChatRequest(message="నా టమాటా పంటకు పూత దశలో ఏ ఎరువులు వాడాలి?", language="te")
    )
    assert tool1 == "fertilizer_rules_engine"
    assert fert1 is not None
    assert fert1.crop == "Tomato"
    assert fert1.growth_stage == "Flowering"  # Must NOT classify as vegetative
    assert "పూత" in r1 or "Flowering" in r1 or "flowering" in r1.lower()
    assert_not_generic_welcome(r1)

    # 2. Telugu Cotton unknown stage nutrients
    r2, tool2, _, _, fert2, _, _, _ = agent_engine.process_request(
        ChatRequest(message="పత్తి పంటకు ప్రస్తుతం ఏ పోషకాలు అవసరం", language="te")
    )
    assert tool2 == "agri_assistant_chat"
    assert fert2 is None  # Does NOT guess single stage NPK dose without knowing stage
    assert "Cotton" in r2 or "పత్తి" in r2
    assert "దశ" in r2
    assert_not_generic_welcome(r2)

    # 3. English Cotton unknown stage -> answers cotton & asks growth stage
    r3, tool3, _, _, _, _, _, _ = agent_engine.process_request(
        ChatRequest(message="What nutrients does my cotton crop need at this stage?", language="en")
    )
    assert tool3 == "agri_assistant_chat"
    assert "cotton" in r3.lower()
    assert "growth stage" in r3.lower()
    assert_not_generic_welcome(r3)

    # 4. Black soil improvement
    r4, tool4, _, _, _, _, _, _ = agent_engine.process_request(
        ChatRequest(message="How can I improve my black soil?", language="en")
    )
    assert tool4 == "agri_assistant_chat"
    assert "black soil" in r4.lower() or "vertisol" in r4.lower()
    assert_not_generic_welcome(r4)

    # 5. Dairy farming startup
    r5, tool5, _, _, _, _, _, _ = agent_engine.process_request(
        ChatRequest(message="How can I start dairy farming?", language="en")
    )
    assert tool5 == "agri_assistant_chat"
    assert "dairy" in r5.lower()
    assert_not_generic_welcome(r5)


# -----------------------------------------------------------------------------
# 5. Hybrid Gemini Mocked Reasoning, Failed Tool & Current-Info Handling
# -----------------------------------------------------------------------------
def test_mocked_hybrid_gemini_open_domain_and_subtle_offtopic(monkeypatch):
    monkeypatch.setenv("GEMINI_MODE", "LIVE")
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyMockedValidLengthTestKey1234567890")

    # Test A: Unseen agri topic (Beekeeping) answered via Gemini general reasoning
    with patch("app.modules.agent.reasoning.plan_agricultural_turn", return_value={
        "is_agricultural": True,
        "is_pure_greeting": False,
        "response_language": "en",
        "normalized_english_query": "How to manage honeybee colonies for orchard pollination?",
        "selected_tool": "agri_assistant_chat",
        "crop": None,
        "growth_stage": None,
        "missing_info": [],
        "is_live_current_info_query": False,
    }), patch("app.modules.agent.reasoning.generate_general_agricultural_answer", return_value=(
        "Place 2–3 Apis cerana or Apis mellifera boxes per acre near flowering orchard trees..."
    )) as mock_gen:
        reply, tool, *_ = agent_engine.process_request(
            ChatRequest(message="How should I place honeybee hives to boost orchard pollination?", language="en")
        )
        assert tool == "agri_assistant_chat"
        assert "hives" in reply.lower() or "apis" in reply.lower()
        assert mock_gen.called
        assert_not_generic_welcome(reply)

    # Test B: Subtle non-agricultural topic rejected politely by semantic planner
    with patch("app.modules.agent.reasoning.plan_agricultural_turn", return_value={
        "is_agricultural": False,
        "refusal_message": "I am AgriMind AI, your specialized agricultural assistant. I cannot help with football rules.",
        "selected_tool": "agri_assistant_chat",
    }):
        reply_off, tool_off, *_ = agent_engine.process_request(
            ChatRequest(message="Explain the offside law in soccer in detail.", language="en")
        )
        assert tool_off == "input_guardrail_refusal"
        assert "specialized agricultural assistant" in reply_off


def test_failed_tool_execution_handled_without_fabrication(monkeypatch):
    monkeypatch.setenv("GEMINI_MODE", "DEMO")
    with patch("app.modules.agent.engine.get_weather_forecast", side_effect=RuntimeError("OpenWeatherMap HTTP 503")):
        reply, tool, _, _, _, weather_obj, _, _ = agent_engine.process_request(
            ChatRequest(message="What is the weather forecast for Guntur today?", language="en")
        )
        assert tool == "weather_service_error"
        assert weather_obj is None
        assert "could not complete" in reply.lower() or "unavailable" in reply.lower()
        assert "28.5" not in reply  # Did NOT fabricate mock weather numbers on failure


def test_chat_api_accepts_multiturn_history_end_to_end(auth_headers, monkeypatch):
    monkeypatch.setenv("GEMINI_MODE", "DEMO")
    res = client.post(
        "/api/v1/agent/chat",
        json={
            "message": "Which fertilizer should I apply now?",
            "language": "en",
            "history": [
                {"role": "user", "content": "My tomato crop is in flowering stage."},
                {"role": "assistant", "content": "Noted tomato crop at flowering stage."},
            ],
        },
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["tool_used"] == "fertilizer_rules_engine"
    assert data["fertilizer"]["crop"] == "Tomato"
    assert data["fertilizer"]["growth_stage"] == "Flowering"
    assert "Potassium" in data["fertilizer"]["nutrient_focus"]
    assert_not_generic_welcome(data["reply"])

