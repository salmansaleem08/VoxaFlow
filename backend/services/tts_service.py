"""
Google TTS service using gTTS.
Generates MP3 audio files served by FastAPI StaticFiles.
"""
import asyncio
import uuid
import logging
from pathlib import Path
from gtts import gTTS
from config import settings

logger = logging.getLogger(__name__)


def _write_tts(text: str, output_path: Path) -> None:
    """Blocking gTTS call — run in executor."""
    tts = gTTS(text=text, lang="en", slow=False, tld="com")
    tts.save(str(output_path))


async def generate_speech(text: str) -> str:
    """
    Convert text to speech and save to media directory.
    Returns the filename (e.g. 'abc123.mp3') for building the public URL.
    """
    filename = f"{uuid.uuid4()}.mp3"
    output_path = settings.media_dir / filename

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, _write_tts, text, output_path)
        logger.info(f"TTS generated: {filename} ({len(text)} chars)")
        return filename
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        raise


def media_url(filename: str) -> str:
    """Build the full public URL for a media file."""
    return f"{settings.backend_url}/media/{filename}"
