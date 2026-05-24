from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List
import tempfile
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # ── Gemini (primary LLM) ─────────────────────────────────────────────────
    gemini_api_key: str = ""

    # ── Groq (fallback LLM) ───────────────────────────────────────────────────
    groq_api_key: str = ""

    # ── Deepgram (STT) ────────────────────────────────────────────────────────
    deepgram_api_key: str = ""

    # ── Twilio ────────────────────────────────────────────────────────────────
    # Option A (recommended): Account SID (AC...) + Auth Token
    twilio_account_sid: str = ""   # AC... Account SID
    twilio_auth_token: str = ""    # Auth Token

    # Option B: API Key auth — use when you only have an API Key (SK...)
    # Set TWILIO_API_KEY=SK..., TWILIO_API_SECRET=..., and TWILIO_ACCOUNT_SID=AC...
    twilio_api_key: str = ""       # SK... API Key SID (optional)
    twilio_api_secret: str = ""    # API Key Secret (optional)

    twilio_phone_number: str = ""

    # ── Server ────────────────────────────────────────────────────────────────
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # ── Media storage ─────────────────────────────────────────────────────────
    media_dir: Path = Path(tempfile.gettempdir()) / "voxaflow_media"

    model_config = {
        "env_file": "../.env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def model_post_init(self, __context):
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self._warn_twilio_config()

    def _warn_twilio_config(self):
        sid = self.twilio_account_sid
        if sid.startswith("SK"):
            logger.warning(
                "TWILIO_ACCOUNT_SID starts with 'SK' — this is an API Key SID, not your Account SID. "
                "For API Key authentication you must ALSO set TWILIO_API_KEY=SK..., "
                "TWILIO_API_SECRET=<secret>, and TWILIO_ACCOUNT_SID=AC... (your real Account SID). "
                "See backend/.env.example for details."
            )

    @property
    def cors_origins(self) -> List[str]:
        return [self.frontend_url, "http://localhost:3000", "http://localhost:3001"]

    @property
    def using_api_key_auth(self) -> bool:
        """True when the user has configured API Key authentication."""
        return bool(self.twilio_api_key.startswith("SK") and self.twilio_api_secret)


settings = Settings()
