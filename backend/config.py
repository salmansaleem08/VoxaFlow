from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import os
from pathlib import Path
import tempfile


class Settings(BaseSettings):
    # Gemini
    gemini_api_key: str = ""

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # Server
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # Whisper
    whisper_model: str = "base"

    # Media storage (temp dir for audio files)
    media_dir: Path = Path(tempfile.gettempdir()) / "voxaflow_media"

    model_config = {"env_file": "../.env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def model_post_init(self, __context):
        self.media_dir.mkdir(parents=True, exist_ok=True)

    @property
    def cors_origins(self) -> List[str]:
        return [self.frontend_url, "http://localhost:3000", "http://localhost:3001"]


settings = Settings()
