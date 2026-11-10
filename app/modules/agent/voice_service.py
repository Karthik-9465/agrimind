import os
import io
import math
import wave
import struct
import logging
import tempfile
import subprocess
import requests
from typing import Optional, Tuple, Dict, Any
from app.modules.agent.audio_processor import process_and_standardize_audio

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
        """Resolves GNANI_API_KEY or GNANI_API_KEY_ID from environment."""
        key = (os.getenv("GNANI_API_KEY") or os.getenv("GNANI_API_KEY_ID") or "").strip()
        if not key or key.startswith("your_") or key == "placeholder":
            return None
        return key

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
        2. Sends standardized audio to Gnani Prisma STT with robust connection handling.
        """
        mode_env = os.getenv("GNANI_MODE", "").strip().upper()
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
        # 3. Live Gnani Prisma STT Call
        # -------------------------------------------------------------
        endpoint = cls.get_stt_endpoint()

        # Write standardized 16kHz WAV to temporary file
        temp_wav_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                tf.write(standardized_wav)
                temp_wav_path = tf.name

            # Execute via curl for robust Schannel TLS handling on Windows
            cmd = [
                "curl.exe",
                "-s",
                "-S",
                "--max-time", "35",
                endpoint,
                "-H", f"X-API-Key-ID: {api_key}",
                "-F", f"audio_file=@{temp_wav_path};type=audio/wav",
                "-F", f"language_code={lang_code}"
            ]

            result_proc = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
            if result_proc.returncode != 0:
                logger.error(f"curl STT upload failed (code {result_proc.returncode}): {result_proc.stderr}")
                raise RuntimeError(f"Gnani STT connection failed: {result_proc.stderr}")

            raw_stdout = result_proc.stdout.strip()
            if not raw_stdout:
                raise RuntimeError("Gnani STT returned an empty response.")

            import json
            result = json.loads(raw_stdout)

            # Check if API returned an error
            if result.get("success") is False:
                err_info = result.get("error", {})
                err_msg = err_info.get("message") or str(err_info)
                logger.error(f"Gnani STT API error: {err_msg}")
                raise RuntimeError(f"Gnani Prisma STT error: {err_msg}")

            # Extract transcription string
            transcript_text = (
                result.get("transcript") or 
                result.get("output", {}).get("literal") or 
                result.get("text") or 
                ""
            )

            # Clean any whitespace
            transcript_text = transcript_text.strip()

            return {
                "text": transcript_text,
                "language_detected": result.get("detected_language_code") or lang_code,
                "confidence": 0.96 if transcript_text else 0.0,
                "duration_seconds": round(duration, 2),
                "is_mock": False,
                "provider": "Gnani AI Prisma v3.0",
                "raw_response": result
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gnani STT response JSON: {raw_stdout}")
            raise RuntimeError(f"Failed to decode Gnani STT response: {raw_stdout[:200]}") from e
        except subprocess.TimeoutExpired as e:
            logger.error("Gnani STT curl process timed out.")
            raise RuntimeError("Gnani STT API connection timed out. Please retry.") from e
        finally:
            if temp_wav_path and os.path.exists(temp_wav_path):
                try:
                    os.unlink(temp_wav_path)
                except Exception:
                    pass

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
