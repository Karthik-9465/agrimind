import io
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.modules.agent.voice_service import GnaniVoiceService

client = TestClient(app)

def create_sample_wav_bytes(duration_sec=1.0) -> bytes:
    """Generates minimal valid 16kHz mono 16-bit PCM WAV."""
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * int(16000 * duration_sec))
    return buf.getvalue()

# -----------------------------------------------------------------------------
# 1. Root Cause Verification: UnboundLocalError 'json' must NEVER occur
# -----------------------------------------------------------------------------
def test_unbound_local_error_json_is_fixed():
    """
    Simulates a curl failure and verifies that UnboundLocalError is NOT raised.
    Instead, a clean TimeoutError or RuntimeError must be raised.
    """
    sample_wav = create_sample_wav_bytes(1.0)
    
    with patch("subprocess.run") as mock_run:
        mock_run.returncode = 28
        mock_run.side_effect = None
        mock_proc = MagicMock()
        mock_proc.returncode = 28
        mock_proc.stderr = "curl: (28) Operation timed out"
        mock_run.return_value = mock_proc
        
        with patch.object(GnaniVoiceService, "get_api_key", return_value="vach_test_key_1234567890"):
            with patch.dict(os.environ, {"GNANI_MODE": "LIVE"}):
                with pytest.raises(TimeoutError) as exc_info:
                    GnaniVoiceService.transcribe_audio(
                        audio_bytes=sample_wav,
                        filename="speech.wav",
                        content_type="audio/wav",
                        language="te"
                    )
                # Verify that the exception is a genuine TimeoutError and NOT an UnboundLocalError
                assert "timed out" in str(exc_info.value).lower()
                assert "json" not in str(exc_info.value).lower()

def test_non_json_upstream_response_handled_gracefully():
    """
    Simulates an upstream Cloudflare/Gateway HTTP 504 error ('error code: 504')
    and validates that bounded retries run cleanly and TimeoutError is raised.
    """
    sample_wav = create_sample_wav_bytes(1.0)
    
    with patch("subprocess.run") as mock_run, patch("app.modules.agent.voice_service.time.sleep"):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = b"error code: 504 Gateway Time-out\n__HTTP_STATUS__:504"
        mock_proc.stderr = b""
        mock_run.return_value = mock_proc
        
        with patch.object(GnaniVoiceService, "get_api_key", return_value="vach_test_key_1234567890"):
            with patch.dict(os.environ, {"GNANI_MODE": "LIVE"}):
                with pytest.raises(TimeoutError) as exc_info:
                    GnaniVoiceService.transcribe_audio(
                        audio_bytes=sample_wav,
                        filename="speech.wav",
                        content_type="audio/wav",
                        language="te"
                    )
                assert "504" in str(exc_info.value)
                assert "json" not in str(exc_info.value).lower()
                assert mock_run.call_count == 3


def test_502_html_upstream_error_raises_connection_error():
    """Simulates an HTML 502 Bad Gateway response and verifies ConnectionError."""
    sample_wav = create_sample_wav_bytes(1.0)

    with patch("subprocess.run") as mock_run, patch("app.modules.agent.voice_service.time.sleep"):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = b"<html><body>502 Bad Gateway</body></html>\n__HTTP_STATUS__:502"
        mock_proc.stderr = b""
        mock_run.return_value = mock_proc

        with patch.object(GnaniVoiceService, "get_api_key", return_value="vach_test_key_1234567890"):
            with patch.dict(os.environ, {"GNANI_MODE": "LIVE"}):
                with pytest.raises(ConnectionError) as exc_info:
                    GnaniVoiceService.transcribe_audio(
                        audio_bytes=sample_wav,
                        filename="speech.wav",
                        content_type="audio/wav",
                        language="te"
                    )
                assert "502" in str(exc_info.value)


def test_malformed_non_5xx_json_raises_runtime_error():
    """Simulates malformed non-JSON HTTP 200 payload and verifies RuntimeError."""
    sample_wav = create_sample_wav_bytes(1.0)

    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = b"not-valid-json-payload\n__HTTP_STATUS__:200"
        mock_proc.stderr = b""
        mock_run.return_value = mock_proc

        with patch.object(GnaniVoiceService, "get_api_key", return_value="vach_test_key_1234567890"):
            with patch.dict(os.environ, {"GNANI_MODE": "LIVE"}):
                with pytest.raises(RuntimeError) as exc_info:
                    GnaniVoiceService.transcribe_audio(
                        audio_bytes=sample_wav,
                        filename="speech.wav",
                        content_type="audio/wav",
                        language="te"
                    )
                assert "decode" in str(exc_info.value).lower() or "json" in str(exc_info.value).lower()
                assert mock_run.call_count == 1

def test_authentication_failure_parsed_cleanly():
    """
    Simulates Gnani API returning 401 INVALID_API_KEY and ensures PermissionError is raised.
    """
    sample_wav = create_sample_wav_bytes(1.0)
    
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = '{"detail":{"error_code":"INVALID_API_KEY","message":"Unauthorized","status_code":401}}'
        mock_run.return_value = mock_proc
        
        with patch.object(GnaniVoiceService, "get_api_key", return_value="vach_test_key_1234567890"):
            with patch.dict(os.environ, {"GNANI_MODE": "LIVE"}):
                with pytest.raises(PermissionError) as exc_info:
                    GnaniVoiceService.transcribe_audio(
                        audio_bytes=sample_wav,
                        filename="speech.wav",
                        content_type="audio/wav",
                        language="te"
                    )
                assert "authentication failed" in str(exc_info.value).lower()

def test_successful_api_response_parsing():
    """
    Simulates a successful Gnani Prisma response and verifies correct schema mapping.
    """
    sample_wav = create_sample_wav_bytes(1.0)
    
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = '{"success":true,"transcript":"టమాటా పంటకు ఎరువులు","detected_language_code":"te-IN","model":"prisma-v2.5"}'
        mock_run.return_value = mock_proc
        
        with patch.object(GnaniVoiceService, "get_api_key", return_value="vach_test_key_1234567890"):
            with patch.dict(os.environ, {"GNANI_MODE": "LIVE"}):
                res = GnaniVoiceService.transcribe_audio(
                    audio_bytes=sample_wav,
                    filename="speech.wav",
                    content_type="audio/wav",
                    language="te"
                )
                assert res["text"] == "టమాటా పంటకు ఎరువులు"
                assert res["language_detected"] == "te-IN"
                assert res["is_mock"] is False
                assert res["provider"] == "Gnani AI Prisma v3.0"

# -----------------------------------------------------------------------------
# 2. FastAPI Endpoint Integration Tests
# -----------------------------------------------------------------------------
def test_endpoint_empty_audio_rejected():
    """Validates that empty audio uploads return HTTP 400."""
    res = client.post(
        "/api/v1/agent/voice/transcribe",
        files={"file": ("empty.wav", b"", "audio/wav")},
        data={"language": "te"}
    )
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()

def test_endpoint_corrupted_audio_rejected():
    """Validates that non-audio bytes return HTTP 400."""
    res = client.post(
        "/api/v1/agent/voice/transcribe",
        files={"file": ("bad.wav", b"NOT_A_VALID_WAV_FILE_HEADER_XYZ", "audio/wav")},
        data={"language": "te"}
    )
    assert res.status_code == 400

def test_endpoint_mock_mode_when_key_absent(monkeypatch):
    """Validates transparent mock mode when API key is missing."""
    monkeypatch.setenv("GNANI_MODE", "DEMO")
    sample_wav = create_sample_wav_bytes(1.0)
    
    res = client.post(
        "/api/v1/agent/voice/transcribe",
        files={"file": ("speech.wav", sample_wav, "audio/wav")},
        data={"language": "te"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "టమాటా" in data["text"]
    assert data["is_mock"] is True

def test_endpoint_authentication_error_returns_401():
    """Validates that Gnani 401 returns FastAPI 401 instead of generic 502."""
    sample_wav = create_sample_wav_bytes(1.0)
    
    with patch.object(GnaniVoiceService, "transcribe_audio", side_effect=PermissionError("Gnani STT authentication failed")):
        res = client.post(
            "/api/v1/agent/voice/transcribe",
            files={"file": ("speech.wav", sample_wav, "audio/wav")},
            data={"language": "te"}
        )
        assert res.status_code == 401
        assert "authentication" in res.json()["detail"].lower()

def test_endpoint_timeout_returns_504():
    """Validates that Gnani timeout returns FastAPI 504 instead of generic 502."""
    sample_wav = create_sample_wav_bytes(1.0)
    
    with patch.object(GnaniVoiceService, "transcribe_audio", side_effect=TimeoutError("Gnani STT connection timed out")):
        res = client.post(
            "/api/v1/agent/voice/transcribe",
            files={"file": ("speech.wav", sample_wav, "audio/wav")},
            data={"language": "te"}
        )
        assert res.status_code == 504
        assert "timed out" in res.json()["detail"].lower()


def test_binary_utf8_telugu_decoding_with_cp1252_invalid_bytes():
    """
    Verifies subprocess binary capture (text=False) decodes Telugu UTF-8 bytes
    containing 0x81 / 0x8d (which crash Windows cp1252 text=True decoding).
    """
    sample_wav = create_sample_wav_bytes(1.0)
    telugu_text = "పురుగుల మందు మరియు ఎరువులు"  # UTF-8 contains \x81 and \x8d bytes
    utf8_payload = (
        '{"success":true,"transcript":"' + telugu_text + '","detected_language_code":"te-IN"}'
        '\n__HTTP_STATUS__:200'
    ).encode("utf-8")
    assert b"\x81" in utf8_payload or b"\x8d" in utf8_payload

    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = utf8_payload
        mock_proc.stderr = b"\x81\x8d"
        mock_run.return_value = mock_proc

        with patch.object(GnaniVoiceService, "get_api_key", return_value="vach_test_key_1234567890"):
            with patch.dict(os.environ, {"GNANI_MODE": "LIVE"}):
                res = GnaniVoiceService.transcribe_audio(
                    audio_bytes=sample_wav,
                    filename="speech.wav",
                    content_type="audio/wav",
                    language="te"
                )
                assert res["text"] == telugu_text
                assert res["language_detected"] == "te-IN"
                assert res["is_mock"] is False
                _, kwargs = mock_run.call_args
                assert kwargs.get("text") is False


def test_subprocess_none_stdout_and_stderr_handled_safely():
    """
    Verifies stdout=None and stderr=None never raise AttributeError on .strip().
    """
    sample_wav = create_sample_wav_bytes(1.0)

    with patch("subprocess.run") as mock_run, patch("app.modules.agent.voice_service.time.sleep"):
        mock_proc = MagicMock()
        mock_proc.returncode = 55
        mock_proc.stdout = None
        mock_proc.stderr = None
        mock_run.return_value = mock_proc

        with patch.object(GnaniVoiceService, "get_api_key", return_value="vach_test_key_1234567890"):
            with patch.dict(os.environ, {"GNANI_MODE": "LIVE"}):
                with pytest.raises(ConnectionError) as exc_info:
                    GnaniVoiceService.transcribe_audio(
                        audio_bytes=sample_wav,
                        filename="speech.wav",
                        content_type="audio/wav",
                        language="te"
                    )
                assert "exit 55" in str(exc_info.value).lower()


def test_dns_error_exit_code_6_raises_connection_error():
    """Verifies curl exit code 6 (DNS failure) classifies as ConnectionError."""
    sample_wav = create_sample_wav_bytes(1.0)

    with patch("subprocess.run") as mock_run, patch("app.modules.agent.voice_service.time.sleep"):
        mock_proc = MagicMock()
        mock_proc.returncode = 6
        mock_proc.stdout = b""
        mock_proc.stderr = b"curl: (6) Could not resolve host: api.vachana.ai"
        mock_run.return_value = mock_proc

        with patch.object(GnaniVoiceService, "get_api_key", return_value="vach_test_key_1234567890"):
            with patch.dict(os.environ, {"GNANI_MODE": "LIVE"}):
                with pytest.raises(ConnectionError) as exc_info:
                    GnaniVoiceService.transcribe_audio(
                        audio_bytes=sample_wav,
                        filename="speech.wav",
                        content_type="audio/wav",
                        language="te"
                    )
                assert "dns" in str(exc_info.value).lower()
                assert mock_run.call_count == 3


def test_exit_code_55_retries_with_ipv4_and_succeeds():
    """
    Verifies transient curl exit code 55 triggers a bounded retry using '-4' (IPv4)
    and succeeds when attempt 2 returns HTTP 200.
    """
    sample_wav = create_sample_wav_bytes(1.0)

    proc_fail = MagicMock()
    proc_fail.returncode = 55
    proc_fail.stdout = b""
    proc_fail.stderr = b"curl: (55) Send failure: Connection was aborted"

    proc_ok = MagicMock()
    proc_ok.returncode = 0
    proc_ok.stdout = '{"success":true,"transcript":"నా పంటకు నీరు పెట్టాలా","detected_language_code":"te-IN"}\n__HTTP_STATUS__:200'.encode("utf-8")
    proc_ok.stderr = b""

    with patch("subprocess.run", side_effect=[proc_fail, proc_ok]) as mock_run, patch("app.modules.agent.voice_service.time.sleep"):
        with patch.object(GnaniVoiceService, "get_api_key", return_value="vach_test_key_1234567890"):
            with patch.dict(os.environ, {"GNANI_MODE": "LIVE"}):
                res = GnaniVoiceService.transcribe_audio(
                    audio_bytes=sample_wav,
                    filename="speech.wav",
                    content_type="audio/wav",
                    language="te"
                )
                assert res["text"] == "నా పంటకు నీరు పెట్టాలా"
                assert res["is_mock"] is False
                assert mock_run.call_count == 2
                first_cmd = mock_run.call_args_list[0][0][0]
                second_cmd = mock_run.call_args_list[1][0][0]
                assert "-4" not in first_cmd
                assert "-4" in second_cmd
                assert "--http1.1" in first_cmd
                assert "--ssl-no-revoke" in first_cmd


def test_endpoint_rate_limit_returns_429():
    """Validates that Gnani HTTP 429 rate limit maps to FastAPI HTTP 429."""
    sample_wav = create_sample_wav_bytes(1.0)

    with patch.object(
        GnaniVoiceService,
        "transcribe_audio",
        side_effect=RuntimeError("Gnani STT rate limited (HTTP 429): max concurrency reached")
    ):
        res = client.post(
            "/api/v1/agent/voice/transcribe",
            files={"file": ("speech.wav", sample_wav, "audio/wav")},
            data={"language": "te"}
        )
        assert res.status_code == 429
        assert "rate limited" in res.json()["detail"].lower()


