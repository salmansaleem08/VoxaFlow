"""
Twilio webhook handlers.

Flow:
  POST /webhooks/answer/{call_id}  — call answered; speak greeting via <Gather>
  POST /webhooks/speech/{call_id}  — Twilio STT result → Gemini → new <Gather>
  POST /webhooks/status/{call_id}  — Twilio status callbacks

Architecture: <Gather input="speech"> instead of <Record> + Deepgram.
  • Barge-in: caller can interrupt agent mid-sentence, Twilio captures immediately
  • Latency: eliminates recording download (~300ms) + Deepgram API (~2s) per turn
  • Urdu: Twilio Gather supports ur-PK natively; Deepgram does not support Urdu at all

English: ~2.5s/turn (2s silence timeout + Gemini). Urdu adds gTTS (~700ms).
"""
import html
import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import Response

from config import settings
from models.schemas import CallStatus
from services import call_store, gemini_service, tts_service

router = APIRouter()
logger = logging.getLogger(__name__)

SPEECH_TIMEOUT = 2  # seconds of silence after speech before Twilio POSTs SpeechResult

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
    """Escape text for safe use inside TwiML XML elements."""
    return html.escape(text)


def _twilio_lang(lang: str) -> str:
    return "ur-PK" if lang.startswith("ur") else "en-US"


# ── TwiML builders ────────────────────────────────────────────────────────────

def _gather_say(text: str, lang: str, action: str) -> str:
    """English: <Say> inside <Gather> — zero file generation, barge-in supported."""
    twilio_lang = _twilio_lang(lang)
    return (
        '<?xml version="1.0" encoding="UTF-8"?><Response>'
        f'<Gather input="speech" action="{action}" method="POST" '
        f'speechTimeout="{SPEECH_TIMEOUT}" language="{twilio_lang}" actionOnEmptyResult="true">'
        f'<Say voice="Polly.Joanna" language="en-US">{_x(text)}</Say>'
        '</Gather>'
        '</Response>'
    )


async def _gather_play(text: str, lang: str, action: str) -> str:
    """Urdu: gTTS <Play> inside <Gather> — barge-in supported."""
    audio = await tts_service.generate_speech(text, lang="ur")
    audio_url = tts_service.media_url(audio)
    twilio_lang = _twilio_lang(lang)
    return (
        '<?xml version="1.0" encoding="UTF-8"?><Response>'
        f'<Gather input="speech" action="{action}" method="POST" '
        f'speechTimeout="{SPEECH_TIMEOUT}" language="{twilio_lang}" actionOnEmptyResult="true">'
        f'<Play>{audio_url}</Play>'
        '</Gather>'
        '</Response>'
    )


async def _respond_gather(text: str, lang: str, action: str) -> str:
    if lang.startswith("ur"):
        return await _gather_play(text, lang, action)
    return _gather_say(text, lang, action)


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
    speech_action = f"{settings.backend_url}/api/webhooks/speech/{call_id}"
    lang = session.call_language

    opening_text = session.scenario_data.get("__opening_text__")
    if not opening_text:
        opening_text = (
            session.transcript[0].text
            if session.transcript
            else "Hello, this is VoxaFlow calling. How are you today?"
        )

    return _twiml(await _respond_gather(opening_text, lang, speech_action))


@router.post("/speech/{call_id}")
async def speech_received(
    call_id: str,
    SpeechResult: str = Form(""),
    Confidence: str = Form("0"),
):
    """
    Called by Twilio after <Gather> captures speech (or actionOnEmptyResult fires).
    SpeechResult is Twilio's inline transcription — no recording download or Deepgram needed.
    """
    session = call_store.get_session(call_id)
    if not session:
        return _twiml('<?xml version="1.0"?><Response><Hangup/></Response>')

    speech_action = f"{settings.backend_url}/api/webhooks/speech/{call_id}"
    lang = session.call_language
    transcript_text = SpeechResult.strip()

    logger.info(f"Twilio STT [{lang}] confidence={Confidence}: '{transcript_text[:100]}'")

    if not transcript_text:
        reprompt = "Sorry, I didn't catch that — could you say that again?"
        return _twiml(await _respond_gather(reprompt, lang, speech_action))

    call_store.append_transcript(call_id, "user", transcript_text)
    call_store.append_conversation(call_id, "user", transcript_text)

    try:
        gemini_result = await gemini_service.get_next_response(
            scenario=session.scenario,
            scenario_data=session.scenario_data,
            conversation_history=session.conversation_history[:-1],
            user_message=transcript_text,
            call_language=lang,
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

    if gemini_result.should_end_call:
        call_store.update_status(call_id, CallStatus.COMPLETED)
        return _twiml(await _respond_hangup(agent_text, lang))

    return _twiml(await _respond_gather(agent_text, lang, speech_action))


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
