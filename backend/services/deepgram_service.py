"""
Deepgram STT service — cloud transcription with auto language detection.
Supports English and Urdu. Uses httpx (already a dependency, no extra SDK).
"""
import logging
from typing import Tuple
import httpx
from config import settings

logger = logging.getLogger(__name__)

_DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"
_PARAMS = {
    "model": "nova-2",
    "detect_language": "true",   # auto-detect EN / UR
    "smart_format": "true",
    "punctuate": "true",
    "filler_words": "false",
}


async def transcribe(audio_path: str) -> Tuple[str, str]:
    """
    Transcribe WAV audio via Deepgram nova-2.
    Returns (transcript, language_code) — e.g. ("Hello", "en") or ("آپ کا شکریہ", "ur").
    On any error returns ("", "en") so the caller can reprompt gracefully.
    """
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            _DEEPGRAM_URL,
            headers={
                "Authorization": f"Token {settings.deepgram_api_key}",
                "Content-Type": "audio/wav",
            },
            content=audio_bytes,
            params=_PARAMS,
        )
        response.raise_for_status()

    data = response.json()
    try:
        channel = data["results"]["channels"][0]
        transcript = channel["alternatives"][0]["transcript"].strip()
        detected_lang = channel.get("detected_language", "en") or "en"
    except (KeyError, IndexError):
        logger.warning(f"Unexpected Deepgram response structure: {str(data)[:300]}")
        return "", "en"

    logger.info(f"Deepgram [{detected_lang}]: '{transcript[:120]}'" + ("..." if len(transcript) > 120 else ""))
    return transcript, detected_lang
