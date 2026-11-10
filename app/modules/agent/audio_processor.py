import os
import io
import wave
import logging
import tempfile
import subprocess
from typing import Tuple

logger = logging.getLogger("agrimind.audio_processor")

def get_ffmpeg_path() -> str:
    """Resolves path to working ffmpeg binary."""
    # 1. Check imageio_ffmpeg
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except ImportError:
        pass

    # 2. Check system PATH
    import shutil
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg

    # Fallback to 'ffmpeg' in PATH
    return "ffmpeg"

def process_and_standardize_audio(
    audio_bytes: bytes,
    original_filename: str = "recording.webm",
    mime_type: str = "audio/webm"
) -> Tuple[bytes, float, str]:
    """
    Inspects, validates, and standardizes incoming audio recording into
    16-bit Linear PCM mono 16,000 Hz WAV required by Gnani Prisma STT (v3.0).

    Returns:
        Tuple of (standardized_wav_bytes, duration_seconds, "audio/wav")
    Raises:
        ValueError: If audio is empty, corrupted, too short (< 0.2s), or unconvertible.
    """
    if not audio_bytes or len(audio_bytes) < 300:
        raise ValueError("Audio recording is empty or too short (less than 300 bytes). Please speak clearly into the microphone.")

    # Detect file format from magic bytes or extension
    is_already_wav = (
        len(audio_bytes) >= 12 and 
        audio_bytes[:4] == b"RIFF" and 
        audio_bytes[8:12] == b"WAVE"
    )

    # If it is already a WAV, inspect if it already matches 16kHz mono 16-bit PCM
    if is_already_wav:
        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                channels = wf.getnchannels()
                sample_rate = wf.getframerate()
                sampwidth = wf.getsampwidth()
                nframes = wf.getnframes()
                duration = nframes / float(sample_rate) if sample_rate > 0 else 0.0

                if channels == 1 and sample_rate == 16000 and sampwidth == 2 and duration >= 0.2:
                    logger.info(f"Incoming audio is already valid 16kHz mono PCM WAV ({duration:.2f}s).")
                    return audio_bytes, duration, "audio/wav"
        except Exception as e:
            logger.warning(f"Incoming file claimed to be WAV but failed wave inspection: {e}. Passing to FFmpeg.")

    # Conversion needed: Convert any container (WebM, Opus, Ogg, MP4, AAC, raw WAV) to 16kHz mono 16-bit PCM WAV
    ffmpeg_exe = get_ffmpeg_path()
    
    # Determine appropriate input suffix
    input_suffix = ".webm"
    if "ogg" in mime_type.lower() or original_filename.endswith(".ogg"):
        input_suffix = ".ogg"
    elif "mp4" in mime_type.lower() or original_filename.endswith(".mp4") or original_filename.endswith(".m4a"):
        input_suffix = ".mp4"
    elif is_already_wav or original_filename.endswith(".wav"):
        input_suffix = ".wav"
    elif "mp3" in mime_type.lower() or original_filename.endswith(".mp3"):
        input_suffix = ".mp3"

    input_temp_path = None
    output_temp_path = None

    try:
        with tempfile.NamedTemporaryFile(suffix=input_suffix, delete=False) as tf_in:
            tf_in.write(audio_bytes)
            input_temp_path = tf_in.name

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf_out:
            output_temp_path = tf_out.name

        # Execute FFmpeg: force 1 channel (mono), 16000 Hz, pcm_s16le, WAV container
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i", input_temp_path,
            "-vn",                  # Ignore video stream if WebM/MP4
            "-ac", "1",             # 1 channel (mono)
            "-ar", "16000",         # 16,000 Hz sampling rate
            "-c:a", "pcm_s16le",    # 16-bit signed PCM
            "-f", "wav",            # Explicit WAV container
            output_temp_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            stderr_snippet = result.stderr[-300:] if result.stderr else "Unknown FFmpeg error"
            logger.error(f"FFmpeg conversion failed (code {result.returncode}): {stderr_snippet}")
            raise ValueError(f"Audio conversion failed. Invalid or corrupted audio stream: {stderr_snippet}")

        # Read converted WAV
        with open(output_temp_path, "rb") as f_out:
            converted_wav = f_out.read()

        # Validate converted file using Python wave library
        with wave.open(io.BytesIO(converted_wav), "rb") as wf:
            channels = wf.getnchannels()
            sample_rate = wf.getframerate()
            sampwidth = wf.getsampwidth()
            nframes = wf.getnframes()
            duration = nframes / float(sample_rate) if sample_rate > 0 else 0.0

            if channels != 1 or sample_rate != 16000 or sampwidth != 2:
                raise ValueError(f"Standardized WAV parameters incorrect: ch={channels}, rate={sample_rate}, width={sampwidth}")

            if duration < 0.2:
                raise ValueError(f"Audio recording duration ({duration:.2f}s) is too short. Please speak clearly for at least 1-2 seconds.")

        logger.info(f"Successfully converted audio to 16kHz mono PCM WAV: duration={duration:.2f}s, size={len(converted_wav)} bytes")
        return converted_wav, duration, "audio/wav"

    except subprocess.TimeoutExpired:
        logger.error("FFmpeg conversion timed out after 15 seconds.")
        raise ValueError("Audio processing timed out.")
    finally:
        if input_temp_path and os.path.exists(input_temp_path):
            try:
                os.unlink(input_temp_path)
            except Exception:
                pass
        if output_temp_path and os.path.exists(output_temp_path):
            try:
                os.unlink(output_temp_path)
            except Exception:
                pass

