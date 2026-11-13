import os
import logging
from pathlib import Path
from typing import Optional
from dotenv import dotenv_values, load_dotenv

logger = logging.getLogger("agrimind.config")

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

def is_placeholder(val: Optional[str]) -> bool:
    """Detects dummy placeholder values from templates and example files."""
    if not val:
        return True
    s = val.strip()
    return (
        s.startswith("your_") or 
        s == "placeholder" or 
        s.startswith("AIzaSy_YOUR_") or 
        s.startswith("vach_your_") or
        s == "your_real_gemini_api_key_here" or
        len(s) < 8
    )

def load_central_environment():
    """
    Centrally loads .env into os.environ.
    If os.environ contains an empty or placeholder value from the parent shell,
    a valid credential found in .env will override it.
    """
    if ENV_FILE.exists():
        # First pass: standard non-destructive load
        load_dotenv(dotenv_path=ENV_FILE, override=False)
        
        # Second pass: check critical keys for stale placeholders in os.environ
        file_values = dotenv_values(ENV_FILE)
        critical_keys = [
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "GNANI_API_KEY",
            "GNANI_API_KEY_ID",
            "GEMINI_MODE",
            "GEMINI_MODEL",
            "GNANI_MODE",
            "SECRET_KEY",
            "DATABASE_URL"
        ]
        for key in critical_keys:
            file_val = (file_values.get(key) or "").strip()
            if file_val and not is_placeholder(file_val):
                env_val = (os.environ.get(key) or "").strip()
                if not env_val or is_placeholder(env_val):
                    logger.info(f"Overriding placeholder/empty os.environ[{key}] with valid value from .env")
                    os.environ[key] = file_val

# Execute environment loading on module import
load_central_environment()

class Settings:
    """Centralized, documented settings access for AgriMind AI."""

    @staticmethod
    def get_gemini_api_key() -> Optional[str]:
        """
        Resolves the Gemini API key with documented precedence:
        1. GEMINI_API_KEY (environment or .env)
        2. GOOGLE_API_KEY (environment or .env)
        Discards leading/trailing whitespace and placeholder strings.
        Never reveals or prints secret credentials.
        """
        for var_name in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
            val = (os.getenv(var_name) or "").strip()
            if val and not is_placeholder(val):
                return val
        return None

    @staticmethod
    def get_gemini_model() -> str:
        return (os.getenv("GEMINI_MODEL") or "gemini-2.5-flash").strip() or "gemini-2.5-flash"

    @staticmethod
    def get_gemini_mode() -> str:
        return (os.getenv("GEMINI_MODE") or "").strip().upper()

    @staticmethod
    def get_gnani_api_key() -> Optional[str]:
        for var_name in ["GNANI_API_KEY", "GNANI_API_KEY_ID"]:
            val = (os.getenv(var_name) or "").strip()
            if val and not is_placeholder(val):
                return val
        return None

    @staticmethod
    def get_gnani_mode() -> str:
        return (os.getenv("GNANI_MODE") or "").strip().upper()

    @staticmethod
    def get_gnani_stt_connect_timeout() -> float:
        try:
            val = float(os.getenv("GNANI_STT_CONNECT_TIMEOUT", "10.0"))
            return max(1.0, min(val, 30.0))
        except ValueError:
            return 10.0

    @staticmethod
    def get_gnani_stt_timeout() -> float:
        try:
            val = float(os.getenv("GNANI_STT_TIMEOUT", "35.0"))
            return max(5.0, min(val, 120.0))
        except ValueError:
            return 35.0

    @staticmethod
    def get_gnani_stt_max_retries() -> int:
        try:
            val = int(os.getenv("GNANI_STT_MAX_RETRIES", "3"))
            return max(1, min(val, 5))
        except ValueError:
            return 3

    @staticmethod
    def get_database_url() -> str:
        return (os.getenv("DATABASE_URL") or "sqlite:///./agrimind.db").strip()

    @staticmethod
    def get_secret_key() -> str:
        return (os.getenv("SECRET_KEY") or "agrimind_production_jwt_secret_2026").strip()

settings = Settings()
