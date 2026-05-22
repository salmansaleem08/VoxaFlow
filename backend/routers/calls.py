"""
Call management REST endpoints.
"""
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from models.schemas import (
    InitiateCallRequest, InitiateCallResponse, CallStatusResponse,
    CallStatus, ScenarioType,
)
from services import call_store, twilio_service, tts_service, gemini_service

router = APIRouter()
logger = logging.getLogger(__name__)


async def _prepare_and_call(call_id: str, phone_number: str, scenario: ScenarioType, scenario_data: dict):
    """Background task: generate opening TTS audio, then make the Twilio call."""
    try:
        # Generate opening message via Gemini
        opening_text = await gemini_service.get_opening_message(scenario, scenario_data)

        # Convert to audio
        audio_file = await tts_service.generate_speech(opening_text)

        # Store opening in conversation history
        call_store.append_transcript(call_id, "agent", opening_text)
        call_store.append_conversation(call_id, "model", opening_text)

        # Stash audio filename in session so the webhook can reference it
        session = call_store.get_session(call_id)
        if session:
            session.scenario_data["__opening_audio__"] = audio_file

        # Make the Twilio call
        twilio_sid = twilio_service.make_outbound_call(phone_number, call_id)
        call_store.update_status(call_id, CallStatus.RINGING, twilio_sid)

    except Exception as e:
        logger.error(f"Failed to initiate call {call_id}: {e}")
        call_store.update_status(call_id, CallStatus.FAILED)


@router.post("/initiate", response_model=InitiateCallResponse)
async def initiate_call(request: InitiateCallRequest, background_tasks: BackgroundTasks):
    """
    Initiate an outbound AI voice call.
    Returns immediately with a call_id; use GET /calls/{call_id}/status to poll.
    """
    session = call_store.create_session(
        phone_number=request.phone_number,
        scenario=request.scenario,
        scenario_data=request.scenario_data,
    )

    background_tasks.add_task(
        _prepare_and_call,
        session.call_id,
        request.phone_number,
        request.scenario,
        request.scenario_data,
    )

    return InitiateCallResponse(
        call_id=session.call_id,
        status=CallStatus.PENDING,
        message="Call is being prepared. Use the call_id to track status.",
    )


@router.get("/{call_id}/status", response_model=CallStatusResponse)
async def get_call_status(call_id: str):
    session = call_store.get_session(call_id)
    if not session:
        raise HTTPException(status_code=404, detail="Call not found")

    return CallStatusResponse(
        call_id=session.call_id,
        status=session.status,
        outcome=session.outcome,
        transcript=session.transcript,
        phone_number=session.phone_number,
        scenario=session.scenario,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/", response_model=list)
async def list_calls():
    sessions = call_store.list_sessions(limit=20)
    return [
        {
            "call_id": s.call_id,
            "phone_number": s.phone_number,
            "scenario": s.scenario,
            "status": s.status,
            "outcome": s.outcome,
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]
