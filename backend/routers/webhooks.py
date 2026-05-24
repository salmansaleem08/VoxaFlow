"""
Twilio webhook handlers.

Flow:
  POST /webhooks/answer/{call_id}    — call answered; deliver greeting via <Say>, start <Record>
  POST /webhooks/recording/{call_id} — recording ready; Deepgram → Gemini → TwiML <Say>
  POST /webhooks/status/{call_id}    — Twilio status callbacks (ringing, completed…)

Latency design:
  English responses: Twilio <Say voice="Polly.Joanna"> — zero file generation, instant delivery.
  Urdu responses:    gTTS → MP3 → <Play> — file generation (~700 ms) is unavoidable for Urdu.
"""
import html
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import Response

from config import settings
from models.schemas import CallStatus
from services import call_store, deepgram_service, gemini_service, tts_service, twilio_service

router = APIRouter()
logger = logging.getLogger(__name__)

RECORD_TIMEOUT = 3      # seconds of silence before recording stops (3 = natural pauses, fast enough)
RECORD_MAX_LENGTH = 30  # max recording length in seconds

TWILIO_STATUS_MAP = {
    "initiated":   CallStatus.PENDING,
    "ringing":     CallStatus.RINGING,
    "in-progress": CallStatus.IN_PROGRESS,
    "completed":   CallStatus.COMPLETED,
    "busy":        CallStatus.FAILED,
    "failed":      CallStatus.FAILED,
    "no-answer":   CallStatus.NO_ANSWER,
    "canceled":    CallStatus.FAILED,
}


def _twiml(content: str) -> Response:
    return Response(content=content, media_type="application/xml")


def _x(text: str) -> str:
    """Escape text so it's safe inside TwiML XML elements."""
    return html.escape(text)


def _record_tag(action: str) -> str:
    return (
        f'<Record action="{action}" method="POST" '
        f'maxLength="{RECORD_MAX_LENGTH}" timeout="{RECORD_TIMEOUT}" '
        'finishOnKey="" playBeep="false" />'
    )


# ── TwiML builders ────────────────────────────────────────────────────────────

def _say_record(text: str, record_action: str) -> str:
    """English: Twilio speaks text via Amazon Polly — no file generation."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?><Response>'
        f'<Say voice="Polly.Joanna" language="en-US">{_x(text)}</Say>'
        f'{_record_tag(record_action)}'
        '</Response>'
    )


def _play_record(audio_url: str, record_action: str) -> str:
    """Urdu: play gTTS audio file, then record."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?><Response>'
        f'<Play>{audio_url}</Play>'
        f'{_record_tag(record_action)}'
        '</Response>'
    )


def _say_hangup(text: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?><Response>'
        f'<Say voice="Polly.Joanna" language="en-US">{_x(text)}</Say>'
        '<Pause length="1"/><Hangup/>'
        '</Response>'
    )


def _play_hangup(audio_url: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?><Response>'
        f'<Play>{audio_url}</Play>'
        '<Pause length="1"/><Hangup/>'
        '</Response>'
    )


async def _respond_record(text: str, lang: str, record_action: str) -> str:
    """Choose TwiML based on language: <Say> for EN, gTTS+<Play> for UR."""
    if lang.startswith("ur"):
        audio = await tts_service.generate_speech(text, lang="ur")
        return _play_record(tts_service.media_url(audio), record_action)
    return _say_record(text, record_action)


async def _respond_hangup(text: str, lang: str) -> str:
    if lang.startswith("ur"):
        audio = await tts_service.generate_speech(text, lang="ur")
        return _play_hangup(tts_service.media_url(audio))
    return _say_hangup(text)


# ── Webhook handlers ──────────────────────────────────────────────────────────

@router.post("/answer/{call_id}")
async def call_answered(call_id: str, request: Request):
    """Called by Twilio when the callee picks up."""
    session = call_store.get_session(call_id)
    if not session:
        return _twiml('<?xml version="1.0"?><Response><Say>System error.</Say><Hangup/></Response>')

    call_store.update_status(call_id, CallStatus.IN_PROGRESS)
    record_action = f"{settings.backend_url}/api/webhooks/recording/{call_id}"

    # Opening text was pre-generated in the background task before the call was placed
    opening_text = session.scenario_data.get("__opening_text__")
    if not opening_text:
        # Fallback if background task hasn't finished yet
        opening_text = (
            session.transcript[0].text
            if session.transcript
            else "Hello, this is VoxaFlow calling. How are you today?"
        )

    return _twiml(_say_record(opening_text, record_action))


@router.post("/recording/{call_id}")
async def recording_received(
    call_id: str,
    RecordingUrl: str = Form(...),
    RecordingDuration: str = Form("0"),
    TwilioCallStatus: str = Form("in-progress", alias="CallStatus"),
):
    """
    Called by Twilio when a recording is ready.
    Pipeline: WAV download → Deepgram STT (language detection) → Gemini → TwiML.
    English path: ~2-3 s total. Urdu path: ~3-4 s (includes gTTS generation).
    """
    session = call_store.get_session(call_id)
    if not session:
        return _twiml('<?xml version="1.0"?><Response><Hangup/></Response>')

    record_action = f"{settings.backend_url}/api/webhooks/recording/{call_id}"
    lang = session.call_language  # "en" or "ur"

    # 1. Download WAV from Twilio
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        await twilio_service.download_recording(RecordingUrl, tmp_path)
    except Exception as e:
        logger.error(f"Recording download failed: {e}")
        Path(tmp_path).unlink(missing_ok=True)
        return _twiml(_say_record(
            "I'm having trouble with the connection. Please go ahead and speak.",
            record_action,
        ))

    # 2. Deepgram STT with language detection
    try:
        transcript_text, detected_lang = await deepgram_service.transcribe(tmp_path)
    except Exception as e:
        logger.error(f"Deepgram transcription failed: {e}")
        transcript_text, detected_lang = "", lang
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # Persist detected language (first non-English detection wins; keeps session consistent)
    if detected_lang and detected_lang != lang:
        call_store.update_language(call_id, detected_lang)
        lang = detected_lang

    if not transcript_text:
        return _twiml(_say_record(
            "I didn't quite catch that — could you say that again please?",
            record_action,
        ))

    call_store.append_transcript(call_id, "user", transcript_text)
    call_store.append_conversation(call_id, "user", transcript_text)

    # 3. Gemini LLM
    try:
        gemini_result = await gemini_service.get_next_response(
            scenario=session.scenario,
            scenario_data=session.scenario_data,
            conversation_history=session.conversation_history[:-1],
            user_message=transcript_text,
        )
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return _twiml(_say_hangup(
            "I apologize for the technical difficulty. Our team will follow up shortly. Thank you."
        ))

    agent_text = gemini_result.response
    call_store.append_transcript(call_id, "agent", agent_text)
    call_store.append_conversation(call_id, "model", agent_text)

    if gemini_result.call_outcome and gemini_result.call_outcome.value != "in_progress":
        call_store.update_outcome(call_id, gemini_result.call_outcome)

    # 4. Return TwiML — English uses <Say> (instant), Urdu uses gTTS+<Play>
    if gemini_result.should_end_call:
        call_store.update_status(call_id, CallStatus.COMPLETED)
        return _twiml(await _respond_hangup(agent_text, lang))

    return _twiml(await _respond_record(agent_text, lang, record_action))


@router.post("/status/{call_id}")
async def call_status_callback(
    call_id: str,
    TwilioCallStatus: str = Form(..., alias="CallStatus"),
    CallSid: str = Form(""),
):
    new_status = TWILIO_STATUS_MAP.get(TwilioCallStatus.lower())
    if new_status:
        call_store.update_status(call_id, new_status, CallSid or None)
        logger.info(f"Call {call_id} → {TwilioCallStatus}")
    return Response(content="", status_code=204)
