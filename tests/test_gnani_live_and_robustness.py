import os
import sys
import io
import wave
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.modules.agent.voice_service import (
    GnaniVoiceService,
    SUPPORTED_TIMBRE_VOICES,
    DEFAULT_VOICE_MAP
)
from app.modules.agent.audio_processor import process_and_standardize_audio

client = TestClient(app)

def create_pcm_wav_bytes(duration=1.0, rate=16000, channels=1):
    """Generates standard 16-bit Linear PCM mono WAV byte sequence."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        # 16-bit silence
        wf.writeframes(b"\x00\x00" * int(rate * duration))
    return buf.getvalue()

# -----------------------------------------------------------------------------
# 1. STT Audio Format & Validation Tests (Task 1 & Task 5)
# -----------------------------------------------------------------------------
def test_audio_processor_standardizes_wav():
    """Validates that audio_processor accepts standard WAV and preserves 16kHz mono parameters."""
    raw_wav = create_pcm_wav_bytes(duration=1.0, rate=16000, channels=1)
    std_wav, duration, mime = process_and_standardize_audio(raw_wav, "recording.wav", "audio/wav")
    assert mime == "audio/wav"
    assert duration >= 0.9
    assert std_wav.startswith(b"RIFF")
    
    with wave.open(io.BytesIO(std_wav), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 16000
        assert wf.getsampwidth() == 2

def test_stt_rejects_empty_audio():
    """Validates that empty audio uploads are rejected with HTTP 400."""
    files = {"file": ("empty.wav", io.BytesIO(b""), "audio/wav")}
    response = client.post("/api/v1/agent/voice/transcribe", files=files, data={"language": "te"})
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

def test_stt_rejects_too_short_audio():
    """Validates that audio recordings shorter than 0.2s are rejected with HTTP 400."""
    tiny_audio = create_pcm_wav_bytes(duration=0.05, rate=16000)
    files = {"file": ("tiny.wav", io.BytesIO(tiny_audio), "audio/wav")}
    response = client.post("/api/v1/agent/voice/transcribe", files=files, data={"language": "te"})
    assert response.status_code == 400
    assert "too short" in response.json()["detail"].lower()

def test_stt_rejects_corrupted_audio():
    """Validates that random non-audio binary blobs are rejected with HTTP 400."""
    corrupted_data = b"NOT_A_VALID_AUDIO_FILE_DATA_CORRUPT" * 20
    files = {"file": ("corrupt.webm", io.BytesIO(corrupted_data), "audio/webm")}
    response = client.post("/api/v1/agent/voice/transcribe", files=files, data={"language": "hi"})
    assert response.status_code == 400
    assert "corrupted" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()

# -----------------------------------------------------------------------------
# 2. TTS Voice Validation Tests (Task 2 & Task 5)
# -----------------------------------------------------------------------------
def test_unsupported_voice_deepak_rejected():
    """Strictly validates that requesting deprecated voice 'Deepak' raises HTTP 400."""
    payload = {
        "text": "Hello farmer",
        "language": "en",
        "voice": "Deepak",
        "speed": 1.0
    }
    response = client.post("/api/v1/agent/voice/synthesize", json=payload)
    assert response.status_code == 400
    err_detail = response.json()["detail"]
    assert "Deepak" in err_detail
    assert "not supported" in err_detail.lower()
    assert "Avinash" in err_detail

def test_supported_voice_avinash_accepted():
    """Validates that supported voice 'Avinash' is valid and accepted."""
    assert "Avinash" in SUPPORTED_TIMBRE_VOICES
    assert DEFAULT_VOICE_MAP["te-IN"] == "Avinash"
    assert DEFAULT_VOICE_MAP["en-IN"] == "Avinash"

def test_supported_voice_shivani_accepted():
    """Validates that supported voice 'Shivani' is valid and accepted."""
    assert "Shivani" in SUPPORTED_TIMBRE_VOICES
    assert DEFAULT_VOICE_MAP["hi-IN"] == "Shivani"

# -----------------------------------------------------------------------------
# 3. Live & Demo Synthesis Playability Tests (Task 3 & Task 5)
# -----------------------------------------------------------------------------
def test_synthesized_audio_is_valid_wav():
    """Validates that synthesized audio contains a valid RIFF WAVE header and is playable."""
    payload = {
        "text": "AgriMind crop advisory",
        "language": "en",
        "voice": "Avinash",
        "speed": 1.0
    }
    response = client.post("/api/v1/agent/voice/synthesize", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    
    audio_bytes = response.content
    assert audio_bytes[:4] == b"RIFF"
    assert audio_bytes[8:12] == b"WAVE"
    
    with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
        assert wf.getnchannels() in (1, 2)
        assert wf.getsampwidth() == 2
        # Official Gnani Timbre native rate is 48,000 Hz; demo chime is 22,050 Hz
        assert wf.getframerate() in (16000, 22050, 24000, 44100, 48000)
        assert wf.getnframes() > 0

def test_tts_in_memory_caching():
    """Validates that duplicate synthesis requests are served instantly from cache."""
    payload = {
        "text": "Cache verification text prompt for farming guidance",
        "language": "en",
        "voice": "Avinash",
        "speed": 1.0
    }
    res1 = client.post("/api/v1/agent/voice/synthesize", json=payload)
    assert res1.status_code == 200
    
    res2 = client.post("/api/v1/agent/voice/synthesize", json=payload)
    assert res2.status_code == 200
    assert res1.content == res2.content
    assert res2.headers.get("X-Audio-Provider") in ["Gnani AI Timbre v3.0 (Cached)", "Gnani AI Timbre (Dev Mock Mode)"]

def test_tts_mp3_container_support():
    """Validates that requesting MP3 container produces audio/mpeg stream."""
    payload = {
        "text": "Testing MP3 container audio output format",
        "language": "en",
        "voice": "Avinash",
        "speed": 1.0,
        "container": "mp3"
    }
    res = client.post("/api/v1/agent/voice/synthesize", json=payload)
    assert res.status_code == 200
    # In live mode it returns audio/mpeg, in demo mode fallback returns audio/wav chime
    assert res.headers["content-type"].startswith(("audio/mpeg", "audio/wav"))
    if res.headers["content-type"].startswith("audio/mpeg"):
        assert res.content[:3] == b"ID3" or res.content[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")

def test_tts_speed_clamping_safeguard():
    """Validates that out-of-bounds speed requests (e.g. 0.5 or 2.0) are safely clamped to 0.85-1.15 without API error."""
    payload = {
        "text": "Testing speed clamping safeguard",
        "language": "en",
        "voice": "Avinash",
        "speed": 1.5 # Exceeds Gnani 1.15 limit
    }
    res = client.post("/api/v1/agent/voice/synthesize", json=payload)
    # Backend clamps to 1.15, so request must succeed with 200 rather than failing with 400
    assert res.status_code == 200
    assert len(res.content) > 100
