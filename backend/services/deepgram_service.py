"""
Deepgram STT service — telephony-optimised, language-explicit.
Language is set explicitly per session (passed from call initiation) rather than
auto-detected, because nova-2 language detection on short telephony utterances
is unreliable and produces wrong transcripts.
"""
import logging
from typing import Tuple
import httpx
from config import settings

logger = logging.getLogger(__name__)

_DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"

# Language code mapping: session lang → Deepgram language code
_LANG_CODES = {
    "en": "en-US",
    "ur": "ur",
}


async def transcribe(audio_path: str, lang: str = "en") -> str:
    """
    Transcribe WAV audio using Deepgram nova-2.
    lang: "en" (English) or "ur" (Urdu) — matches session call_language.
    Returns transcript string, or "" if nothing detected.
    """
    deepgram_lang = _LANG_CODES.get(lang, "en-US")

    params = {
        "model": "nova-2",
        "language": deepgram_lang,
        "smart_format": "true",
        "punctuate": "true",
        "filler_words": "false",
    }

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
            params=params,
        )
        response.raise_for_status()

    data = response.json()
    try:
        transcript = data["results"]["channels"][0]["alternatives"][0]["transcript"].strip()
    except (KeyError, IndexError):
        logger.warning(f"Unexpected Deepgram response: {str(data)[:300]}")
        return ""

    logger.info(f"Deepgram [{deepgram_lang}]: '{transcript[:120]}'" + ("..." if len(transcript) > 120 else ""))
    return transcript
