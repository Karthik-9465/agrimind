import io
import os
import sys
import time
import wave
import threading
import pytest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.modules.agent import reasoning
from app.modules.agent.engine import agent_engine
from app.modules.agent.schemas import ChatRequest, ChatTurn
from app.modules.agent.voice_service import GnaniVoiceService

client = TestClient(app)


def _wav_bytes(duration_sec: float = 0.8, freq_tag: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        sample = (freq_tag % 100).to_bytes(2, "little", signed=True)
        wf.writeframes(sample * int(16000 * duration_sec))
    return buf.getvalue()


@pytest.fixture
def farmer_headers():
    signup_payload = {
        "email": "reliability_tester@agrimind.ai",
        "password": "Password123!",
        "full_name": "Reliability Test Farmer",
        "role": "farmer",
    }
    res = client.post("/api/v1/auth/signup", json=signup_payload)
    if res.status_code == 201:
        token = res.json()["access_token"]
    else:
        login_res = client.post(
            "/api/v1/auth/login",
            json={"email": "reliability_tester@agrimind.ai", "password": "Password123!"},
        )
        token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# -----------------------------------------------------------------------------
# PART A: Gemini Planner Structured Schema, Truncation & General Fallback Tests
# -----------------------------------------------------------------------------
def test_planner_config_uses_structured_schema_and_zero_thinking(monkeypatch):
    """Test 1: Verifies planner configures response_schema=PlannerDecision & thinking_budget=0."""
    monkeypatch.setenv("GEMINI_MODE", "LIVE")
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyMockedValidLengthTestKey1234567890")

    captured = {}

    class _FakeModels:
        def generate_content(self, model, contents, config):
            captured["model"] = model
            captured["config"] = config
            parsed = reasoning.PlannerDecision(
                is_agricultural=True,
                is_pure_greeting=False,
                response_language="te",
                normalized_english_query="Which fertilizer should be used for tomato flowering?",
                selected_tool="fertilizer_rules_engine",
                crop="Tomato",
                growth_stage="flowering",
            )
            cand = SimpleNamespace(finish_reason="STOP", content=SimpleNamespace(parts=[]))
            return SimpleNamespace(parsed=parsed, text=parsed.model_dump_json(), candidates=[cand])

    fake_client = SimpleNamespace(models=_FakeModels())
    with patch("google.genai.Client", return_value=fake_client):
        ctx = {
            "original_query": "నా టమాటా పంటకు పూత దశలో ఏ ఎరువులు వాడాలి?",
            "normalized_query": "Which fertilizer for tomato flowering stage?",
            "reply_language": "te",
            "detected_style": "te",
            "history_text": "None",
            "farm_crop": None,
            "resolved_soil": "Loam",
            "resolved_location": "Mandya, India",
        }
        plan = reasoning.plan_agricultural_turn(ctx)

    assert plan is not None
    assert plan["selected_tool"] == "fertilizer_rules_engine"
    assert plan["crop"] == "Tomato"
    assert plan["growth_stage"] == "flowering"
    cfg = captured["config"]
    assert cfg.response_mime_type == "application/json"
    assert cfg.response_schema is reasoning.PlannerDecision
    assert cfg.max_output_tokens >= 768
    assert cfg.thinking_config is not None
    assert cfg.thinking_config.thinking_budget == 0


def test_planner_handles_unterminated_and_malformed_json_with_general_fallback(monkeypatch):
    """Test 2 & 5: Reproduces exact 'line 2 column 3 (char 4)' malformed JSON and verifies general Gemini reasoning succeeds."""
    monkeypatch.setenv("GEMINI_MODE", "LIVE")
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyMockedValidLengthTestKey1234567890")

    calls = []

    class _FakeModels:
        def generate_content(self, model, contents, config):
            calls.append(config)
            if getattr(config, "response_mime_type", None) == "application/json":
                # Exact production failure payload reported by user
                cand = SimpleNamespace(finish_reason="MAX_TOKENS", content=SimpleNamespace(parts=[]))
                return SimpleNamespace(
                    parsed=None,
                    text='{\n  "is_agricultural',
                    candidates=[cand],
                )
            # General agricultural reasoning fallback call still succeeds!
            cand = SimpleNamespace(finish_reason="STOP", content=SimpleNamespace(parts=[]))
            return SimpleNamespace(
                parsed=None,
                text=(
                    "For mulching chillies against thrips and moisture stress, spread organic straw mulch (5–7 cm) "
                    "around the root zone or silver-black reflective plastic mulch between planting rows."
                ),
                candidates=[cand],
            )

    with patch("google.genai.Client", return_value=SimpleNamespace(models=_FakeModels())):
        reply, tool, *_ = agent_engine.process_request(
            ChatRequest(message="How does reflective mulching help control thrips in chilli?", language="en")
        )

    assert tool == "agri_assistant_chat"
    assert "mulch" in reply.lower() and "thrips" in reply.lower()
    assert "feel free to ask any agriculture-related question" not in reply.lower()
    assert len(calls) == 2  # Planner rejected truncated JSON cleanly -> general Gemini call ran!


def test_planner_rejects_incomplete_or_unexpected_schemas_safely(monkeypatch):
    """Test 3: Empty text, array JSON, and missing keys return None safely; fertilizer query still routes cleanly."""
    assert reasoning.validate_planner_payload("") is None
    assert reasoning.validate_planner_payload("[]") is None
    assert reasoning.validate_planner_payload('{"random_key": 123}') is None
    assert reasoning.validate_planner_payload('{\n  "broken') is None

    # Normalizes variant casing cleanly
    normalized = reasoning.validate_planner_payload({
        "is_agricultural": True,
        "selected_tool": "fertilizer_rules_engine",
        "growth_stage": "Flowering",
        "crop": "Tomato",
        "response_language": "TE",
    })
    assert normalized is not None
    assert normalized["growth_stage"] == "flowering"
    assert normalized["response_language"] == "te"

    # Test 6: Specialized fertilizer query still selects fertilizer_rules_engine when planner returns incomplete output
    monkeypatch.setenv("GEMINI_MODE", "LIVE")
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyMockedValidLengthTestKey1234567890")
    with patch("app.modules.agent.reasoning._generate_gemini_text", side_effect=["{\n  \"", None]):
        reply, tool, _, _, fert, *_ = agent_engine.process_request(
            ChatRequest(message="నా టమాటా పంటకు పూత దశలో ఏ ఎరువులు వాడాలి?", language="te")
        )
    assert tool == "fertilizer_rules_engine"
    assert fert is not None and fert.crop == "Tomato" and fert.growth_stage == "Flowering"
    assert "టమాటా" in reply and "పూత" in reply


def test_gemini_connectivity_failure_graceful_multilingual_fallback(monkeypatch):
    """Test 4 & 11: Connectivity exceptions never crash; preserves language across te/hi/en/romanized_te."""
    monkeypatch.setenv("GEMINI_MODE", "LIVE")
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSyMockedValidLengthTestKey1234567890")

    class _FailingModels:
        def generate_content(self, model, contents, config):
            raise ConnectionError("Server disconnected without sending a response.")

    with patch("google.genai.Client", return_value=SimpleNamespace(models=_FailingModels())):
        # Telugu unknown-stage Cotton -> honest Telugu stage overview + clarification
        r_te, t_te, *_ = agent_engine.process_request(
            ChatRequest(message="పత్తి పంటకు ప్రస్తుతం ఏ పోషకాలు అవసరం", language="te")
        )
        assert t_te == "agri_assistant_chat"
        assert "పత్తి" in r_te and "దశ" in r_te

        # Romanized Telugu unknown-stage Cotton -> preserved gracefully without crashing
        r_rom, t_rom, *_ = agent_engine.process_request(
            ChatRequest(message="patti pantaku prastutam em poshakalu kavali", language="en")
        )
        assert t_rom == "agri_assistant_chat"
        assert "cotton" in r_rom.lower() and "stage" in r_rom.lower()

        # Hindi tomato flowering fertilizer -> localized Hindi template
        r_hi, t_hi, _, _, fert_hi, *_ = agent_engine.process_request(
            ChatRequest(message="मेरी टमाटर की फसल में फूल आने की अवस्था में कौन सी खाद डालें?", language="hi")
        )
        assert t_hi == "fertilizer_rules_engine"
        assert fert_hi.growth_stage == "Flowering"
        assert "टमाटर" in r_hi and "फूल" in r_hi


# -----------------------------------------------------------------------------
# PART B: Gnani Prisma STT Transport, Backoff, Permanent Errors & Concurrency
# -----------------------------------------------------------------------------
def test_stt_curl_schannel_and_timeout_retries_with_backoff_and_phase_logs(monkeypatch):
    """Test 8: Handles curl 56 (Schannel close) and curl 28 (35s timeout) with configurable timeouts, backoff+jitter, and proper HTTP status."""
    sample_wav = _wav_bytes(1.0)
    monkeypatch.setenv("GNANI_MODE", "LIVE")
    monkeypatch.setenv("GNANI_STT_CONNECT_TIMEOUT", "7")
    monkeypatch.setenv("GNANI_STT_TIMEOUT", "22")
    monkeypatch.setenv("GNANI_STT_MAX_RETRIES", "3")

    sleep_durations = []

    p56 = MagicMock(returncode=56, stdout=b"", stderr=b"curl: (56) schannel: server closed abruptly")
    p28 = MagicMock(returncode=28, stdout=b"", stderr=b"curl: (28) Operation timed out after 22000 milliseconds")

    with (
        patch.object(GnaniVoiceService, "get_api_key", return_value="vach_test_key_1234567890"),
        patch("subprocess.run", side_effect=[p56, p56, p28]) as mock_run,
        patch("app.modules.agent.voice_service.time.sleep", side_effect=lambda s: sleep_durations.append(s)),
    ):
        res = client.post(
            "/api/v1/agent/voice/transcribe",
            files={"file": ("voice.wav", sample_wav, "audio/wav")},
            data={"language": "te"},
        )

    assert res.status_code == 504
    assert "timed out" in res.json()["detail"].lower()
    assert mock_run.call_count == 3
    first_cmd = mock_run.call_args_list[0][0][0]
    second_cmd = mock_run.call_args_list[1][0][0]
    assert "--connect-timeout" in first_cmd and "7.0" in first_cmd
    assert "--max-time" in first_cmd and "22.0" in first_cmd
    assert "Expect:" in first_cmd
    assert "-4" not in first_cmd and "-4" in second_cmd
    # Exponential backoff + jitter increases on attempt 2 vs attempt 1
    assert len(sleep_durations) == 2
    assert sleep_durations[1] > sleep_durations[0]

    # Also test curl 56 final failure -> 502 Bad Gateway with phase=tls_negotiation_or_server_close
    with (
        patch.object(GnaniVoiceService, "get_api_key", return_value="vach_test_key_1234567890"),
        patch("subprocess.run", side_effect=[p56, p56, p56]),
        patch("app.modules.agent.voice_service.time.sleep"),
    ):
        res_502 = client.post(
            "/api/v1/agent/voice/transcribe",
            files={"file": ("voice.wav", sample_wav, "audio/wav")},
            data={"language": "te"},
        )
    assert res_502.status_code == 502
    assert "tls_negotiation_or_server_close" in res_502.json()["detail"]


def test_stt_does_not_retry_permanent_auth_validation_or_unsupported_format(monkeypatch):
    """Test 9: HTTP 401/403 (even empty body) and HTTP 415/400 unsupported format NEVER retry."""
    sample_wav = _wav_bytes(1.0)
    monkeypatch.setenv("GNANI_MODE", "LIVE")

    for status_code, expected_http in ((401, 401), (403, 401), (415, 400), (400, 400)):
        proc = MagicMock(
            returncode=0,
            stdout=f"__HTTP_STATUS__:{status_code}".encode("utf-8"),
            stderr=b"",
        )
        with (
            patch.object(GnaniVoiceService, "get_api_key", return_value="vach_test_key_1234567890"),
            patch("subprocess.run", return_value=proc) as mock_run,
        ):
            res = client.post(
                "/api/v1/agent/voice/transcribe",
                files={"file": ("voice.wav", sample_wav, "audio/wav")},
                data={"language": "en"},
            )
        assert res.status_code == expected_http
        assert mock_run.call_count == 1


def test_stt_simultaneous_duplicate_deduplicated_and_consecutive_independent(monkeypatch):
    """Test 7 & 10: Simultaneous identical requests share 1 upstream call; consecutive requests run independently."""
    wav_a = _wav_bytes(0.8, freq_tag=10)
    wav_b = _wav_bytes(0.8, freq_tag=20)
    monkeypatch.setenv("GNANI_MODE", "LIVE")

    call_counter = {"count": 0}

    def _fake_subprocess(cmd, **kwargs):
        call_counter["count"] += 1
        idx = call_counter["count"]
        time.sleep(0.15)
        proc = MagicMock()
        proc.returncode = 0
        proc.stderr = b""
        payload = (
            f'{{"success":true,"transcript":"Transcript #{idx}","detected_language_code":"te-IN"}}\n'
            f'__HTTP_STATUS__:200__CURL_META__:dns=0.01;tcp=0.02;tls=0.04;pre=0.05;ttfb=0.20;total=0.21;ul=25644;ip=1.2.3.4'
        )
        proc.stdout = payload.encode("utf-8")
        return proc

    with (
        patch.object(GnaniVoiceService, "get_api_key", return_value="vach_test_key_1234567890"),
        patch("subprocess.run", side_effect=_fake_subprocess),
    ):
        # A. Two simultaneous identical requests -> only 1 upstream subprocess call
        results = [None, None]

        def _worker(slot):
            results[slot] = GnaniVoiceService.transcribe_audio(wav_a, "speech.wav", "audio/wav", "te")

        t1 = threading.Thread(target=_worker, args=(0,))
        t2 = threading.Thread(target=_worker, args=(1,))
        t1.start()
        time.sleep(0.03)
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        assert call_counter["count"] == 1
        assert results[0]["text"] == "Transcript #1"
        assert results[1]["text"] == "Transcript #1"

        # B. Two consecutive API requests (same audio again + different audio) -> neither interferes
        r_seq1 = client.post(
            "/api/v1/agent/voice/transcribe",
            files={"file": ("voice1.wav", wav_a, "audio/wav")},
            data={"language": "te"},
        )
        r_seq2 = client.post(
            "/api/v1/agent/voice/transcribe",
            files={"file": ("voice2.wav", wav_b, "audio/wav")},
            data={"language": "en"},
        )

    assert call_counter["count"] == 3
    assert r_seq1.status_code == 200 and r_seq1.json()["text"] == "Transcript #2"
    assert r_seq2.status_code == 200 and r_seq2.json()["text"] == "Transcript #3"


def test_gnani_tts_continues_working(monkeypatch):
    """Test 12: Verifies Gnani Timbre TTS validation, speed clamping, RIFF WAV chunk patching & DEMO mode continue working."""
    monkeypatch.setenv("GNANI_MODE", "DEMO")
    res_demo = client.post(
        "/api/v1/agent/voice/synthesize",
        json={"text": "పత్తి పంటకు సలహా", "language": "te", "voice": "Avinash", "speed": 1.0},
    )
    assert res_demo.status_code == 200
    assert res_demo.content[:4] == b"RIFF"

    monkeypatch.setenv("GNANI_MODE", "LIVE")
    # Build synthetic streaming WAV with 0xFFFFFFFF size markers (like live Timbre)
    pcm = b"\x01\x00" * 1600
    riff_stream = bytearray(
        b"RIFF\xff\xff\xff\xffWAVEfmt "
        + b"\x10\x00\x00\x00\x01\x00\x01\x00\x80\xbb\x00\x00\x00\x77\x01\x00\x02\x00\x10\x00"
        + b"data\xff\xff\xff\xff"
        + pcm
    )
    fake_resp = MagicMock(status_code=200, content=bytes(riff_stream))
    with (
        patch.object(GnaniVoiceService, "get_api_key", return_value="vach_test_key_1234567890"),
        patch("app.modules.agent.voice_service.requests.post", return_value=fake_resp) as mock_post,
    ):
        res_live = client.post(
            "/api/v1/agent/voice/synthesize",
            json={"text": "Tomato flowering stage fertilizer schedule", "language": "en", "voice": "Avinash", "speed": 1.5},
        )

    assert res_live.status_code == 200
    assert res_live.headers["content-type"].startswith("audio/wav")
    assert res_live.content[:4] == b"RIFF" and res_live.content[4:8] != b"\xff\xff\xff\xff"
    sent_payload = mock_post.call_args.kwargs["json"]
    assert sent_payload["speed"] == 1.15  # Safely clamped to Timbre limit

