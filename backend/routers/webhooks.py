"""
Twilio webhook handlers.

Flow:
  POST /webhooks/answer/{call_id}    — call answered; play greeting, then record
  POST /webhooks/recording/{call_id} — recording ready; STT → Gemini → TTS → TwiML
  POST /webhooks/status/{call_id}    — Twilio status callbacks (ringing, completed…)
"""
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import Response

from config import settings
from models.schemas import CallStatus, CallOutcome
from services import call_store, whisper_service, gemini_service, tts_service, twilio_service

router = APIRouter()
logger = logging.getLogger(__name__)

RECORD_TIMEOUT = 5    # seconds of silence before stopping recording
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


def _twiml_response(content: str) -> Response:
    return Response(content=content, media_type="application/xml")


def _play_and_record(audio_url: str, record_action: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Play>{audio_url}</Play>
  <Record
    action="{record_action}"
    method="POST"
    maxLength="{RECORD_MAX_LENGTH}"
    timeout="{RECORD_TIMEOUT}"
    finishOnKey="*"
    playBeep="false"
  />
</Response>"""


def _play_and_hangup(audio_url: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Play>{audio_url}</Play>
  <Pause length="1"/>
  <Hangup/>
</Response>"""


@router.post("/answer/{call_id}")
async def call_answered(call_id: str, request: Request):
    """Called by Twilio when the callee picks up."""
    session = call_store.get_session(call_id)
    if not session:
        return _twiml_response('<?xml version="1.0"?><Response><Say>System error.</Say><Hangup/></Response>')

    call_store.update_status(call_id, CallStatus.IN_PROGRESS)

    opening_audio = session.scenario_data.get("__opening_audio__")
    if not opening_audio:
        opening_text = session.transcript[0].text if session.transcript else "Hello, this is VoxaFlow calling."
        return _twiml_response(f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">{opening_text}</Say>
  <Record action="{settings.backend_url}/api/webhooks/recording/{call_id}"
          method="POST" maxLength="{RECORD_MAX_LENGTH}" timeout="{RECORD_TIMEOUT}"
          playBeep="false" />
</Response>""")

    audio_url = tts_service.media_url(opening_audio)
    record_action = f"{settings.backend_url}/api/webhooks/recording/{call_id}"
    return _twiml_response(_play_and_record(audio_url, record_action))


@router.post("/recording/{call_id}")
async def recording_received(
    call_id: str,
    RecordingUrl: str = Form(...),
    RecordingDuration: str = Form("0"),
    TwilioCallStatus: str = Form("in-progress", alias="CallStatus"),
):
    """
    Called by Twilio when a recording is ready.
    Downloads WAV → Whisper STT → Gemini → Google TTS → TwiML.
    """
    session = call_store.get_session(call_id)
    if not session:
        return _twiml_response('<?xml version="1.0"?><Response><Hangup/></Response>')

    duration = int(RecordingDuration or 0)
    if duration < 1:
        reprompt = "I'm sorry, I didn't catch that. Could you please repeat?"
        audio_file = await tts_service.generate_speech(reprompt)
        audio_url = tts_service.media_url(audio_file)
        record_action = f"{settings.backend_url}/api/webhooks/recording/{call_id}"
        return _twiml_response(_play_and_record(audio_url, record_action))

    # 1. Download the recording as WAV
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        await twilio_service.download_recording(RecordingUrl, tmp_path)
    except Exception as e:
        logger.error(f"Failed to download recording: {e}")
        error_audio = await tts_service.generate_speech("I'm having trouble hearing you. Please try again.")
        record_action = f"{settings.backend_url}/api/webhooks/recording/{call_id}"
        return _twiml_response(_play_and_record(tts_service.media_url(error_audio), record_action))

    # 2. Whisper STT
    try:
        transcript_text = await whisper_service.transcribe(tmp_path, settings.whisper_model)
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        transcript_text = "[inaudible]"
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if not transcript_text or transcript_text == "[inaudible]":
        reprompt_audio = await tts_service.generate_speech(
            "I'm sorry, I couldn't understand that. Could you please speak more clearly?"
        )
        record_action = f"{settings.backend_url}/api/webhooks/recording/{call_id}"
        return _twiml_response(_play_and_record(tts_service.media_url(reprompt_audio), record_action))

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
        fallback_audio = await tts_service.generate_speech(
            "I apologize, I'm experiencing a technical issue. Someone from our team will follow up. Thank you."
        )
        return _twiml_response(_play_and_hangup(tts_service.media_url(fallback_audio)))

    agent_text = gemini_result.response
    call_store.append_transcript(call_id, "agent", agent_text)
    call_store.append_conversation(call_id, "model", agent_text)

    if gemini_result.call_outcome and gemini_result.call_outcome.value != "in_progress":
        call_store.update_outcome(call_id, gemini_result.call_outcome)

    # 4. Google TTS
    try:
        agent_audio = await tts_service.generate_speech(agent_text)
        agent_audio_url = tts_service.media_url(agent_audio)
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return _twiml_response(f'<?xml version="1.0"?><Response><Say>{agent_text}</Say><Hangup/></Response>')

    # 5. Return TwiML
    if gemini_result.should_end_call:
        call_store.update_status(call_id, CallStatus.COMPLETED)
        return _twiml_response(_play_and_hangup(agent_audio_url))

    record_action = f"{settings.backend_url}/api/webhooks/recording/{call_id}"
    return _twiml_response(_play_and_record(agent_audio_url, record_action))


@router.post("/status/{call_id}")
async def call_status_callback(
    call_id: str,
    TwilioCallStatus: str = Form(..., alias="CallStatus"),
    CallSid: str = Form(""),
):
    """Twilio status callback — update session status."""
    new_status = TWILIO_STATUS_MAP.get(TwilioCallStatus.lower())
    if new_status:
        call_store.update_status(call_id, new_status, CallSid or None)
        logger.info(f"Call {call_id} Twilio status: {TwilioCallStatus}")

    return Response(content="", status_code=204)
