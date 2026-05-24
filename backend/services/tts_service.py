"""
Google TTS service (gTTS) — used for Urdu responses.
English responses use Twilio's built-in <Say> TwiML verb to skip file generation entirely.
"""
import asyncio
import uuid
import logging
from pathlib import Path
from gtts import gTTS
from config import settings

logger = logging.getLogger(__name__)


def _write_tts(text: str, output_path: Path, lang: str) -> None:
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save(str(output_path))


async def generate_speech(text: str, lang: str = "en") -> str:
    """
    Convert text to speech and save to media directory.
    Returns the filename for building the public URL.
    lang: "en" for English, "ur" for Urdu.
    """
    tts_lang = "ur" if lang.startswith("ur") else "en"
    filename = f"{uuid.uuid4()}.mp3"
    output_path = settings.media_dir / filename

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, _write_tts, text, output_path, tts_lang)
        logger.info(f"TTS [{tts_lang}]: {filename} ({len(text)} chars)")
        return filename
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        raise


def media_url(filename: str) -> str:
    return f"{settings.backend_url}/media/{filename}"
