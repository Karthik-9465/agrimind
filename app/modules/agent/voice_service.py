import os
import io
import json
import math
import wave
import shutil
import struct
import hashlib
import random
import threading
import logging
import tempfile
import subprocess
import time
import requests
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse

from app.config import settings
from app.modules.agent.audio_processor import process_and_standardize_audio

def _decode_subprocess_output(raw_output: Any) -> str:
    """Safely decodes subprocess stdout/stderr (bytes, str, or None) using UTF-8."""
    if raw_output is None:
        return ""
    if isinstance(raw_output, (bytes, bytearray)):
        return bytes(raw_output).decode("utf-8", errors="replace").strip()
    return str(raw_output).strip()

logger = logging.getLogger("agrimind.voice")

# Official Gnani AI Endpoints and Model Defaults
DEFAULT_GNANI_STT_ENDPOINT = "https://api.vachana.ai/stt/v3"
DEFAULT_GNANI_TTS_ENDPOINT = "https://api.vachana.ai/api/v1/tts/inference"
DEFAULT_GNANI_TTS_CONTAINER = "wav"

# Official Gnani Timbre v3.0 Audio Constants
TIMBRE_NATIVE_SAMPLE_RATE = 48000
TIMBRE_SPEED_MIN = 0.85
TIMBRE_SPEED_MAX = 1.15

# Supported Language Code Mappings (Gnani requires full regional codes)
LANGUAGE_MAP = {
    "te": "te-IN",       # Telugu
    "hi": "hi-IN",       # Hindi
    "en": "en-IN",       # Indian English
    "auto": "indic-auto" # Indic Auto Detect
}

# Supported Voices for model 'timbre-v3.0' verified directly from Gnani API
SUPPORTED_TIMBRE_VOICES = [
    "Avinash", "Shivani", "Lakshmi", "Kalpana", "Shubham",
    "Prakash", "Devansh", "Yashraj", "Chetana", "Vasudha",
    "Harshad", "Riyaa", "Tarika"
]

# Verified default voices per language (configurable via environment variables)
DEFAULT_VOICE_MAP = {
    "te-IN": "Avinash",   # Verified Telugu male voice (Lakshmi and Kalpana also supported)
    "hi-IN": "Shivani",   # Verified Hindi female voice (Avinash and Shubham also supported)
    "en-IN": "Avinash",   # Verified Indian English male voice (Shivani also supported)
    "indic-auto": "Avinash"
}

# In-memory synthesis cache to avoid duplicate expensive API requests
_audio_cache: Dict[str, Tuple[bytes, str]] = {}

# Thread-safe single-flight registry preventing simultaneous duplicate STT uploads
_inflight_stt_lock = threading.Lock()
_inflight_stt_requests: Dict[str, Dict[str, Any]] = {}

def generate_synthetic_audio_chime() -> bytes:
    """
    Generates a valid 16-bit mono 22050Hz PCM WAV chime using Python's standard library.
    Plays a gentle two-tone harmonic notification in the farmer's browser during demo/mock mode.
    """
    buf = io.BytesIO()
    sample_rate = 22050
    duration = 0.8  # seconds
    num_samples = int(sample_rate * duration)
    
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)      # Mono
        wf.setsampwidth(2)      # 16-bit
        wf.setframerate(sample_rate)
        frames = bytearray()
        
        for i in range(num_samples):
            t = float(i) / sample_rate
            # 587.33Hz (D5) transitioning to 880Hz (A5) gentle melodic chime with exponential decay
            freq = 587.33 if t < 0.35 else 880.0
            decay = math.exp(-3.5 * (t if t < 0.35 else (t - 0.35)))
            sample = int(14000 * decay * math.sin(2.0 * math.pi * freq * t))
            frames.extend(struct.pack('<h', max(-32768, min(32767, sample))))
            
        wf.writeframes(frames)
        
    return buf.getvalue()

class GnaniVoiceService:
    """
    Official Gnani AI integration service powering:
    1. Speech-to-Text via Gnani Prisma (v3.0)
    2. Text-to-Speech via Gnani Timbre (v3.0)
    Provides transparent development mock mode when credentials are not configured.
    """

    @classmethod
    def get_api_key(cls) -> Optional[str]:
        """Resolves GNANI_API_KEY or GNANI_API_KEY_ID via central config (handles placeholders)."""
        return settings.get_gnani_api_key()

    @classmethod
    def get_stt_endpoint(cls) -> str:
        return os.getenv("GNANI_STT_ENDPOINT", DEFAULT_GNANI_STT_ENDPOINT).strip()

    @classmethod
    def get_tts_endpoint(cls) -> str:
        return os.getenv("GNANI_TTS_ENDPOINT", DEFAULT_GNANI_TTS_ENDPOINT).strip()

    @classmethod
    def get_configured_voice(cls, lang_code: str, requested_voice: Optional[str] = None) -> str:
        """
        Resolves and strictly validates voice against timbre-v3.0 supported voices.
        Never silently substitutes an invalid requested voice.
        """
        if requested_voice:
            voice_candidate = requested_voice.strip()
            if voice_candidate not in SUPPORTED_TIMBRE_VOICES:
                raise ValueError(
                    f"Voice '{voice_candidate}' is not supported by model 'timbre-v3.0'. "
                    f"Supported voices: {', '.join(SUPPORTED_TIMBRE_VOICES)}"
                )
            return voice_candidate

        # Check environment overrides
        env_voice = os.getenv("GNANI_TTS_VOICE", "").strip()
        if env_voice:
            if env_voice not in SUPPORTED_TIMBRE_VOICES:
                raise ValueError(
                    f"Environment variable GNANI_TTS_VOICE='{env_voice}' is not in supported voices: "
                    f"{', '.join(SUPPORTED_TIMBRE_VOICES)}"
                )
            return env_voice

        # Check language-specific environment override
        if lang_code == "te-IN":
            te_voice = os.getenv("GNANI_TTS_VOICE_TE", "").strip()
            if te_voice and te_voice in SUPPORTED_TIMBRE_VOICES:
                return te_voice
        elif lang_code == "hi-IN":
            hi_voice = os.getenv("GNANI_TTS_VOICE_HI", "").strip()
            if hi_voice and hi_voice in SUPPORTED_TIMBRE_VOICES:
                return hi_voice
        elif lang_code == "en-IN":
            en_voice = os.getenv("GNANI_TTS_VOICE_EN", "").strip()
            if en_voice and en_voice in SUPPORTED_TIMBRE_VOICES:
                return en_voice

        # Default fallback from verified map
        return DEFAULT_VOICE_MAP.get(lang_code, "Avinash")

    @classmethod
    def check_gnani_status(cls) -> Dict[str, Any]:
        """
        Evaluates the operational status of Gnani AI STT & TTS services.
        """
        mode_env = os.getenv("GNANI_MODE", "").strip().upper()
        api_key = cls.get_api_key()

        services_info = {
            "stt": {"model": "prisma-v3.0", "languages": ["te-IN", "hi-IN", "en-IN", "indic-auto"]},
            "tts": {"model": "timbre-v3.0", "voices": SUPPORTED_TIMBRE_VOICES}
        }

        if mode_env == "DEMO":
            return {
                "mode": "DEMO",
                "services": services_info,
                "configured": bool(api_key),
                "authenticated": False,
                "status_detail": "Explicit DEMO mode active via GNANI_MODE=DEMO setting."
            }

        if not api_key:
            return {
                "mode": "NOT_CONFIGURED",
                "services": services_info,
                "configured": False,
                "authenticated": False,
                "status_detail": "GNANI_API_KEY is not configured in environment. System operates in transparent multilingual DEMO mock mode."
            }

        return {
            "mode": "LIVE",
            "services": services_info,
            "configured": True,
            "authenticated": True,
            "status_detail": "Connected to Gnani AI API gateway (Prisma v3.0 STT & Timbre v3.0 TTS)."
        }

    @classmethod
    def _classify_failure_phase(cls, exit_code: int, err_snippet: str, curl_meta: Optional[str] = None) -> str:
        """Determines whether transport failed during DNS, TCP connect, TLS/Schannel, audio upload, or server wait."""
        low = (err_snippet or "").lower()
        meta_vals: Dict[str, float] = {}
        if curl_meta:
            for item in curl_meta.split(";"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    try:
                        meta_vals[k.strip()] = float(v.strip())
                    except ValueError:
                        pass

        if exit_code == 6 or "could not resolve host" in low:
            return "dns_resolution"
        if exit_code == 7 or "failed to connect" in low or "connection timed out" in low:
            return "connection_establishment"
        if exit_code in (35, 56, 60) or any(tok in low for tok in ("schannel", "ssl", "tls", "server closed abruptly")):
            return "tls_negotiation_or_server_close"
        if exit_code == 55 or "send failure" in low or "connection was aborted" in low:
            return "audio_upload"
        if exit_code == 28:
            tcp_t = meta_vals.get("tcp", 0.0)
            pre_t = meta_vals.get("pre", 0.0)
            ttfb_t = meta_vals.get("ttfb", 0.0)
            if tcp_t == 0.0:
                return "connection_establishment"
            if pre_t > 0.0 and ttfb_t == 0.0:
                return "server_processing"
            return "request_timeout"
        if exit_code == 52:
            return "server_processing"
        return "transport"

    @classmethod
    def _classify_curl_error(
        cls,
        exit_code: int,
        stt_host: str,
        err_snippet: str,
        elapsed: float,
        curl_meta: Optional[str] = None
    ) -> Tuple[Exception, bool]:
        """Maps curl non-zero exit codes to typed exceptions, failure phases, and retry eligibility."""
        phase = cls._classify_failure_phase(exit_code, err_snippet, curl_meta=curl_meta)
        if exit_code == 6:
            return ConnectionError(
                f"Gnani STT DNS resolution failed for host '{stt_host}' (phase={phase}): {err_snippet}"
            ), True
        if exit_code == 28:
            return TimeoutError(
                f"Gnani STT request timed out after {elapsed:.2f}s connecting to '{stt_host}' (phase={phase}): {err_snippet}"
            ), True
        if exit_code in (7, 35, 52, 55, 56, 60):
            return ConnectionError(
                f"Gnani STT connection aborted/network error (curl exit {exit_code}, phase={phase}) for '{stt_host}': {err_snippet}"
            ), True
        return RuntimeError(f"Gnani STT curl execution failed (exit {exit_code}, phase={phase}): {err_snippet}"), False

    @classmethod
    def _extract_http_status_and_body(cls, raw_stdout: str) -> Tuple[Optional[int], str, Optional[str]]:
        """Extracts optional trailing curl HTTP status and timing metadata without disturbing plain responses."""
        marker = "__HTTP_STATUS__:"
        meta_marker = "__CURL_META__:"
        if marker in raw_stdout:
            body_part, status_part = raw_stdout.rsplit(marker, 1)
            curl_meta = None
            if meta_marker in status_part:
                status_str, meta_str = status_part.split(meta_marker, 1)
                status_digits = status_str.strip()
                curl_meta = meta_str.strip()
            else:
                status_digits = status_part.strip()
            try:
                return int(status_digits), body_part.strip(), curl_meta
            except ValueError:
                return None, body_part.strip(), curl_meta
        return None, raw_stdout, None

    @classmethod
    def _parse_and_validate_stt_json(
        cls,
        parsed_response: Dict[str, Any],
        http_status: Optional[int],
        lang_code: str,
        duration: float
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Exception], bool]:
        """
        Inspects parsed Gnani Prisma JSON payload.
        Returns (success_dict, error_to_raise, should_retry).
        Never retries permanent auth (401/403) or validation/unsupported-format (400/413/415/422) errors.
        """
        detail = parsed_response.get("detail")
        if detail is not None:
            if isinstance(detail, dict):
                err_code = detail.get("error_code")
                err_msg = detail.get("message", "Gnani STT error")
                status_val = detail.get("status_code") or http_status
                if err_code == "RATE_LIMITED" or status_val == 429:
                    return None, RuntimeError(f"Gnani STT rate limited (429): {err_msg}"), True
                if err_code in ("INVALID_API_KEY", "MISSING_API_KEY") or status_val in (401, 403):
                    logger.error(f"Gnani STT API authentication failed: {err_code}")
                    return None, PermissionError(f"Gnani STT authentication failed ({err_code}): {err_msg}"), False
                if status_val in (400, 413, 415, 422) or any(
                    k in f"{err_code or ''} {err_msg}".lower()
                    for k in ("unsupported", "invalid format", "invalid audio", "codec", "too large")
                ):
                    return None, ValueError(f"Gnani STT rejected audio/input ({err_code or status_val}): {err_msg}"), False
                should_retry_srv = bool(status_val and int(status_val) >= 500)
                return None, RuntimeError(f"Gnani STT service error (HTTP {status_val}): {err_msg}"), should_retry_srv
            if isinstance(detail, list):
                return None, ValueError(f"Gnani STT input validation error: {detail}"), False
            if isinstance(detail, str):
                low_det = detail.lower()
                if "unauthorized" in low_det or "forbidden" in low_det or http_status in (401, 403):
                    return None, PermissionError(f"Gnani STT authentication error: {detail}"), False
                if http_status in (400, 413, 415, 422) or any(k in low_det for k in ("unsupported", "format", "invalid audio")):
                    return None, ValueError(f"Gnani STT audio validation/format error: {detail}"), False
                return None, RuntimeError(f"Gnani STT service error: {detail}"), bool(http_status and http_status >= 500)

        if http_status in (401, 403):
            return None, PermissionError(f"Gnani STT authentication failed (HTTP {http_status})."), False
        if http_status in (400, 413, 415, 422):
            return None, ValueError(f"Gnani STT rejected audio/request (HTTP {http_status}): {parsed_response}"), False

        if parsed_response.get("success") is False:
            err_info = parsed_response.get("error", {})
            err_msg = err_info.get("message") if isinstance(err_info, dict) else str(err_info)
            logger.error(f"Gnani STT API error: {err_msg}")
            if any(k in (err_msg or "").lower() for k in ("unsupported", "invalid format", "invalid audio", "sample rate")):
                return None, ValueError(f"Gnani Prisma STT format/validation error: {err_msg}"), False
            if any(k in (err_msg or "").lower() for k in ("unauthorized", "invalid api key", "forbidden")):
                return None, PermissionError(f"Gnani Prisma STT authentication error: {err_msg}"), False
            return None, RuntimeError(f"Gnani Prisma STT error: {err_msg}"), False

        transcript_text = (
            parsed_response.get("transcript") or
            parsed_response.get("output", {}).get("literal") or
            parsed_response.get("text") or
            ""
        ).strip()

        return {
            "text": transcript_text,
            "language_detected": parsed_response.get("detected_language_code") or lang_code,
            "confidence": 0.96 if transcript_text else 0.0,
            "duration_seconds": round(duration, 2),
            "is_mock": False,
            "provider": "Gnani AI Prisma v3.0",
            "raw_response": parsed_response
        }, None, False

    @classmethod
    def _execute_stt_attempt(
        cls,
        curl_exe: str,
        endpoint: str,
        sanitized_url: str,
        stt_host: str,
        api_key: str,
        temp_wav_path: str,
        lang_code: str,
        attempt: int,
        max_attempts: int,
        duration: float,
        connect_timeout: float = 10.0,
        total_timeout: float = 35.0,
        payload_bytes: int = 0
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Exception], bool]:
        """Executes one bounded STT upload attempt via binary subprocess capture with phase telemetry."""
        transport_flags = ["--http1.1", "--ssl-no-revoke", "--no-buffer"]
        if attempt >= 2:
            # Fallback to explicit IPv4 on retry if dual-stack / IPv6 stalled or aborted
            transport_flags.append("-4")

        proxy_configured = bool(
            os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        )

        cmd = [
            curl_exe,
            "-s",
            "-S",
            *transport_flags,
            "--connect-timeout", f"{connect_timeout:.1f}",
            "--max-time", f"{total_timeout:.1f}",
            "-w", "\n__HTTP_STATUS__:%{http_code}__CURL_META__:dns=%{time_namelookup};tcp=%{time_connect};tls=%{time_appconnect};pre=%{time_pretransfer};ttfb=%{time_starttransfer};total=%{time_total};ul=%{size_upload};ip=%{remote_ip}",
            "-X", "POST",
            endpoint,
            "-H", f"X-API-Key-ID: {api_key}",
            "-H", "Expect:",
            "-F", f"audio_file=@{temp_wav_path};type=audio/wav",
            "-F", f"language_code={lang_code}"
        ]

        logger.info(
            f"Gnani STT request: method=POST url={sanitized_url} host={stt_host} "
            f"lang={lang_code} wav_bytes={payload_bytes} duration={duration:.2f}s "
            f"connect_timeout={connect_timeout:.1f}s max_time={total_timeout:.1f}s "
            f"proxy_configured={proxy_configured} attempt={attempt}/{max_attempts} ipv4_forced={attempt >= 2}"
        )

        t_start = time.monotonic()
        try:
            # Capture raw bytes (text=False) to avoid Windows CP1252 UnicodeDecodeError on Indic scripts
            result_proc = subprocess.run(cmd, capture_output=True, text=False, timeout=total_timeout + 5.0)
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - t_start
            logger.warning(f"Gnani STT subprocess timed out after {elapsed:.2f}s (phase=subprocess_deadline) on attempt {attempt}/{max_attempts}")
            return None, TimeoutError(f"Gnani STT API connection timed out after {elapsed:.2f}s."), True
        except OSError as oe:
            elapsed = time.monotonic() - t_start
            logger.error(f"Gnani STT subprocess OS failure ({elapsed:.2f}s): {oe}")
            return None, ConnectionError(f"Failed to invoke curl subprocess ({curl_exe}): {oe}"), False

        elapsed = time.monotonic() - t_start
        raw_stdout = _decode_subprocess_output(getattr(result_proc, "stdout", None))
        raw_stderr = _decode_subprocess_output(getattr(result_proc, "stderr", None))
        http_status, body_text, curl_meta = cls._extract_http_status_and_body(raw_stdout)

        if result_proc.returncode != 0:
            phase = cls._classify_failure_phase(result_proc.returncode, raw_stderr, curl_meta=curl_meta)
            logger.warning(
                f"Gnani STT transport failure: method=POST url={sanitized_url} phase={phase} "
                f"exit_code={result_proc.returncode} elapsed={elapsed:.3f}s "
                f"meta={curl_meta or 'none'} stderr={raw_stderr[:200]}"
            )
            err, should_retry = cls._classify_curl_error(
                result_proc.returncode, stt_host, raw_stderr, elapsed, curl_meta=curl_meta
            )
            return None, err, should_retry

        logger.info(
            f"Gnani STT response: method=POST url={sanitized_url} "
            f"status={http_status} exit_code={result_proc.returncode} elapsed={elapsed:.3f}s "
            f"body_chars={len(body_text)} meta={curl_meta or 'none'}"
        )

        # Permanent authentication / validation / unsupported-format HTTP status (do NOT retry)
        if http_status in (401, 403):
            return None, PermissionError(f"Gnani STT authentication failed (HTTP {http_status}): {body_text[:160]}"), False
        if http_status in (400, 413, 415, 422):
            return None, ValueError(f"Gnani STT rejected audio/request (HTTP {http_status}): {body_text[:160]}"), False

        # Handle HTTP 504 upstream gateway timeout independently
        if http_status == 504 or body_text.lower().startswith("error code: 504") or "504 gateway" in body_text.lower():
            return None, TimeoutError(f"Gnani STT upstream gateway error (HTTP 504) after {elapsed:.2f}s."), True

        # Handle HTTP 502/503/HTML upstream gateway errors independently
        if http_status in (502, 503) or body_text.lower().startswith(("error code: 502", "error code: 503", "<html>", "<!doctype")):
            return None, ConnectionError(f"Gnani STT upstream gateway error (HTTP {http_status or '5xx'}): {body_text[:120]}"), True

        if http_status == 429:
            return None, RuntimeError(f"Gnani STT rate limited (HTTP 429): {body_text[:160]}"), True

        if not body_text:
            retry_empty = http_status is None or http_status == 0 or http_status >= 500
            return None, RuntimeError(f"Gnani STT returned an empty response (HTTP {http_status})."), retry_empty

        try:
            parsed_response = json.loads(body_text)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode Gnani STT response JSON (HTTP {http_status}): {body_text[:200]}")
            retry_decode = http_status is None or http_status == 0 or http_status >= 500
            return (
                None,
                RuntimeError(f"Failed to decode Gnani STT response (HTTP {http_status}): {body_text[:150]}"),
                retry_decode
            )

        return cls._parse_and_validate_stt_json(parsed_response, http_status, lang_code, duration)

    @classmethod
    def _compute_retry_backoff(cls, attempt: int, last_error: Optional[Exception]) -> float:
        """Bounded exponential backoff with jitter (higher base on HTTP 429 rate-limit)."""
        err_str = str(last_error or "").lower()
        is_rate_limit = "429" in err_str or "rate" in err_str
        base = 1.5 if is_rate_limit else 0.75
        delay = min(base * (2 ** max(0, attempt - 1)), 6.0)
        jitter = random.uniform(0.05, 0.35)
        return round(delay + jitter, 3)

    @classmethod
    def _live_stt_request(
        cls,
        standardized_wav: bytes,
        lang_code: str,
        api_key: str,
        duration: float
    ) -> Dict[str, Any]:
        """Handles temp file lifecycle, timeouts, host diagnostics, and bounded retries for live Gnani Prisma STT."""
        endpoint = cls.get_stt_endpoint()
        parsed_ep = urlparse(endpoint)
        sanitized_url = f"{parsed_ep.scheme}://{parsed_ep.netloc}{parsed_ep.path}"
        stt_host = parsed_ep.hostname or ""

        if stt_host and stt_host != "api.vachana.ai":
            logger.warning(f"Configured STT hostname '{stt_host}' differs from official default 'api.vachana.ai'")

        connect_timeout = settings.get_gnani_stt_connect_timeout()
        total_timeout = settings.get_gnani_stt_timeout()
        max_attempts = settings.get_gnani_stt_max_retries()

        curl_exe = shutil.which("curl.exe") or shutil.which("curl") or "curl.exe"
        temp_wav_path = None
        last_error: Optional[Exception] = None

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                tf.write(standardized_wav)
                temp_wav_path = tf.name

            for attempt in range(1, max_attempts + 1):
                res, err, should_retry = cls._execute_stt_attempt(
                    curl_exe=curl_exe,
                    endpoint=endpoint,
                    sanitized_url=sanitized_url,
                    stt_host=stt_host,
                    api_key=api_key,
                    temp_wav_path=temp_wav_path,
                    lang_code=lang_code,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    duration=duration,
                    connect_timeout=connect_timeout,
                    total_timeout=total_timeout,
                    payload_bytes=len(standardized_wav)
                )
                if res is not None:
                    return res

                last_error = err
                if not should_retry or attempt >= max_attempts:
                    raise last_error

                backoff = cls._compute_retry_backoff(attempt, last_error)
                logger.info(f"Scheduling Gnani STT retry attempt {attempt + 1}/{max_attempts} after {backoff:.2f}s backoff.")
                time.sleep(backoff)

            raise last_error or RuntimeError("Failed to receive a valid response from Gnani STT.")

        finally:
            if temp_wav_path and os.path.exists(temp_wav_path):
                try:
                    os.unlink(temp_wav_path)
                except Exception:
                    pass

    @classmethod
    def transcribe_audio(
        cls,
        audio_bytes: bytes,
        filename: str = "farmer_voice.webm",
        content_type: str = "audio/webm",
        language: str = "te"
    ) -> Dict[str, Any]:
        """
        Transcribes speech using Gnani Prisma STT API.
        1. Preprocesses and standardizes audio into 16kHz mono 16-bit PCM WAV.
        2. Deduplicates concurrent identical in-flight uploads (single-flight protection).
        3. Sends standardized audio to Gnani Prisma STT with timeouts & exponential backoff retries.
        """
        mode_env = settings.get_gnani_mode()
        api_key = cls.get_api_key()
        lang_code = LANGUAGE_MAP.get(language.lower(), LANGUAGE_MAP["te"])

        # -------------------------------------------------------------
        # 1. Preprocess & Standardize Audio Container & Codec
        # -------------------------------------------------------------
        try:
            standardized_wav, duration, _ = process_and_standardize_audio(
                audio_bytes=audio_bytes,
                original_filename=filename,
                mime_type=content_type
            )
        except ValueError as e:
            logger.warning(f"Audio preprocessing rejected input: {e}")
            raise

        # -------------------------------------------------------------
        # 2. Transparent Mock Mode when credentials absent or mode is DEMO
        # -------------------------------------------------------------
        if mode_env == "DEMO" or not api_key:
            logger.info("GNANI operating in transparent development mock mode.")
            mock_transcripts = {
                "te-IN": "నా టమాటా పంటకు పూత దశలో ఏ ఎరువులు వాడాలి మరియు ఎంత మోతాదులో ఇవ్వాలి?",
                "hi-IN": "मेरी टमाटर की फसल में फूल आने की अवस्था में कौन सा उर्वरक और कितनी मात्रा में देना चाहिए?",
                "en-IN": "What is the recommended fertilizer dosage for my tomato crop in flowering stage?",
                "indic-auto": "నా టమాటా పంటకు పూత దశలో ఏ ఎరువులు వాడాలి మరియు ఎంత మోతాదులో ఇవ్వాలి?"
            }
            transcription = mock_transcripts.get(lang_code, mock_transcripts["en-IN"])
            return {
                "text": transcription,
                "language_detected": lang_code,
                "confidence": 0.95,
                "duration_seconds": round(duration, 2),
                "is_mock": True,
                "provider": "Gnani AI Prisma (Dev Mock Mode)",
                "note": "GNANI_API_KEY not configured or GNANI_MODE=DEMO. Running in transparent development mock mode."
            }

        # -------------------------------------------------------------
        # 3. Single-Flight Guard & Live Gnani Prisma STT Call
        # -------------------------------------------------------------
        dedup_key = hashlib.sha256(b"|".join([lang_code.encode("utf-8"), standardized_wav])).hexdigest()
        is_leader = False
        with _inflight_stt_lock:
            entry = _inflight_stt_requests.get(dedup_key)
            if entry is None:
                entry = {"event": threading.Event(), "result": None, "error": None}
                _inflight_stt_requests[dedup_key] = entry
                is_leader = True

        if not is_leader:
            logger.info(f"Coalescing simultaneous duplicate Gnani STT request (key={dedup_key[:12]}).")
            wait_limit = settings.get_gnani_stt_timeout() * settings.get_gnani_stt_max_retries() + 15.0
            finished = entry["event"].wait(timeout=wait_limit)
            if not finished:
                raise TimeoutError("Timed out waiting for in-flight duplicate Gnani STT transcription.")
            if entry["error"] is not None:
                raise entry["error"]
            return dict(entry["result"])

        try:
            result = cls._live_stt_request(
                standardized_wav=standardized_wav,
                lang_code=lang_code,
                api_key=api_key,
                duration=duration
            )
            entry["result"] = result
            return dict(result)
        except Exception as exc:
            entry["error"] = exc
            raise
        finally:
            with _inflight_stt_lock:
                _inflight_stt_requests.pop(dedup_key, None)
            entry["event"].set()

    @classmethod
    def synthesize_speech(
        cls,
        text: str,
        language: str = "te",
        speed: float = 1.0,
        voice: Optional[str] = None,
        container: Optional[str] = None
    ) -> Tuple[bytes, str, bool, str]:
        """
        Synthesizes text into high-fidelity speech using Gnani Timbre TTS (v3.0).
        1. Validates voice strictly against SUPPORTED_TIMBRE_VOICES.
        2. Configures official audio container (WAV / MP3) with native 48,000 Hz sample rate.
        3. Enforces valid Timbre speed bounds (0.85 to 1.15) to prevent API validation failures.
        4. Normalizes WAV headers to replace streaming 0xFFFFFFFF chunk sizes with exact byte counts.
        5. Implements connection/read timeouts, network retry backoff, and LRU memory caching.
        Returns:
            Tuple of (audio_bytes, content_type, is_mock, provider_label)
        """
        mode_env = os.getenv("GNANI_MODE", "").strip().upper()
        api_key = cls.get_api_key()
        lang_code = LANGUAGE_MAP.get(language.lower(), LANGUAGE_MAP["te"])
        
        # Strictly resolve and validate voice
        selected_voice = cls.get_configured_voice(lang_code, voice)

        # -------------------------------------------------------------
        # 1. Mock / Development Mode when credentials absent or mode is DEMO
        # -------------------------------------------------------------
        if mode_env == "DEMO" or not api_key:
            logger.info("GNANI_API_KEY not configured for TTS. Generating synthetic audible WAV notification chime.")
            chime_bytes = generate_synthetic_audio_chime()
            return chime_bytes, "audio/wav", True, "Gnani AI Timbre (Dev Mock Mode)"

        # -------------------------------------------------------------
        # 2. Check LRU In-Memory Audio Cache
        # -------------------------------------------------------------
        container_target = (container or os.getenv("GNANI_TTS_CONTAINER", DEFAULT_GNANI_TTS_CONTAINER)).strip().lower()
        if container_target not in ("wav", "mp3"):
            container_target = "wav"

        # Strictly clamp speed to Gnani Timbre v3.0 supported bounds (0.85 to 1.15)
        safe_speed = max(TIMBRE_SPEED_MIN, min(float(speed), TIMBRE_SPEED_MAX))

        cache_key = f"{hash(text)}:{selected_voice}:{lang_code}:{safe_speed:.2f}:{container_target}"
        if cache_key in _audio_cache:
            logger.info("Serving synthesized audio from in-memory cache.")
            cached_bytes, cached_ct = _audio_cache[cache_key]
            return cached_bytes, cached_ct, False, "Gnani AI Timbre v3.0 (Cached)"

        # -------------------------------------------------------------
        # 3. Live Gnani Timbre TTS API Call with Retries and Timeouts
        # -------------------------------------------------------------
        endpoint = cls.get_tts_endpoint()
        headers = {
            "X-API-Key-ID": api_key,
            "Content-Type": "application/json",
            "User-Agent": "AgriMind-VoiceClient/2.0"
        }
        payload = {
            "model": "timbre-v3.0",
            "text": text,
            "voice": selected_voice,
            "language": lang_code,
            "speed": safe_speed,
            "audio_config": {
                "container": container_target
            }
        }

        # Timeout: (connect_timeout=10.0s, read_timeout=35.0s)
        timeout_config = (10.0, 35.0)
        max_attempts = 2

        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=timeout_config
                )

                # HTTP 400: Validation error (e.g. invalid voice/speed) -> DO NOT RETRY
                if response.status_code == 400:
                    err_body = response.text
                    logger.error(f"Gnani TTS validation error [400]: {err_body}")
                    raise ValueError(f"Gnani Timbre TTS validation error (HTTP 400): {err_body}")

                if response.status_code in (401, 403):
                    logger.error(f"Gnani TTS authentication failed [{response.status_code}]")
                    raise RuntimeError("Gnani Timbre TTS authentication failed: Invalid or expired X-API-Key-ID.")

                if response.status_code == 429:
                    logger.error("Gnani TTS rate limit exceeded [429]")
                    raise RuntimeError("Gnani Timbre TTS rate limit exceeded. Please retry momentarily.")

                if response.status_code != 200:
                    logger.error(f"Gnani TTS API error [{response.status_code}]: {response.text}")
                    if attempt < max_attempts:
                        import time
                        time.sleep(1.0)
                        continue
                    raise RuntimeError(f"Gnani Timbre TTS service error HTTP {response.status_code}: {response.text}")

                raw_audio = response.content
                if not raw_audio or len(raw_audio) < 100:
                    raise RuntimeError("Gnani TTS returned an empty audio response.")

                # Inspect and format response audio container
                if raw_audio.startswith(b"RIFF"):
                    # Native WAV container: patch streaming 0xFFFFFFFF chunk lengths with exact byte count
                    if len(raw_audio) >= 44 and (raw_audio[4:8] == b"\xff\xff\xff\xff" or raw_audio[40:44] == b"\xff\xff\xff\xff"):
                        audio_mutable = bytearray(raw_audio)
                        total_len = len(audio_mutable)
                        data_len = max(0, total_len - 44)
                        audio_mutable[4:8] = struct.pack('<I', total_len - 8)
                        audio_mutable[40:44] = struct.pack('<I', data_len)
                        audio_bytes = bytes(audio_mutable)
                    else:
                        audio_bytes = raw_audio
                    content_type = "audio/wav"

                elif raw_audio.startswith((b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"ID3")):
                    # Native MP3 container
                    audio_bytes = raw_audio
                    content_type = "audio/mpeg"

                else:
                    # Raw PCM fallback: native Timbre v3.0 sample rate is 48,000 Hz, 16-bit mono
                    buf = io.BytesIO()
                    with wave.open(buf, 'wb') as wf:
                        wf.setnchannels(1)                      # Mono
                        wf.setsampwidth(2)                      # 16-bit
                        wf.setframerate(TIMBRE_NATIVE_SAMPLE_RATE)  # 48,000 Hz
                        wf.writeframes(raw_audio)
                    audio_bytes = buf.getvalue()
                    content_type = "audio/wav"

                # Store in cache (limit cache to 50 items)
                if len(_audio_cache) > 50:
                    _audio_cache.pop(next(iter(_audio_cache)))
                _audio_cache[cache_key] = (audio_bytes, content_type)

                return audio_bytes, content_type, False, "Gnani AI Timbre v3.0"

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"Gnani TTS attempt {attempt} failed with network error: {str(e)}")
                if attempt < max_attempts:
                    import time
                    time.sleep(1.5)
                    continue
                raise RuntimeError("Gnani TTS API connection timed out. Please try again.") from e
            except ValueError:
                # Validation error: re-raise immediately
                raise
            except Exception as e:
                logger.error(f"Unexpected error in Gnani TTS: {str(e)}")
                raise RuntimeError(f"Failed to communicate with Gnani TTS API: {str(e)}") from e
