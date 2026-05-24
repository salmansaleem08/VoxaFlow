"""
Call management REST endpoints.
"""
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from models.schemas import (
    InitiateCallRequest, InitiateCallResponse, CallStatusResponse,
    CallStatus, ScenarioType,
)
from services import call_store, twilio_service, gemini_service

router = APIRouter()
logger = logging.getLogger(__name__)


async def _prepare_and_call(
    call_id: str,
    phone_number: str,
    scenario: ScenarioType,
    scenario_data: dict,
    call_language: str = "en",
):
    """
    Background task:
    1. Generate opening greeting (in the right language) via Gemini
    2. Store it so the answer webhook can deliver it
    3. Initiate the Twilio call
    """
    try:
        opening_text = await gemini_service.get_opening_message(scenario, scenario_data, call_language)

        call_store.append_transcript(call_id, "agent", opening_text)
        # Gemini requires conversations to start with a user turn
        call_store.append_conversation(call_id, "user", "The call just connected. Please begin with your opening greeting.")
        call_store.append_conversation(call_id, "model", opening_text)

        session = call_store.get_session(call_id)
        if session:
            session.scenario_data["__opening_text__"] = opening_text

        twilio_sid = twilio_service.make_outbound_call(phone_number, call_id)
        call_store.update_status(call_id, CallStatus.PENDING, twilio_sid)

    except Exception as e:
        logger.error(f"Failed to initiate call {call_id}: {e}")
        call_store.update_status(call_id, CallStatus.FAILED, error=str(e))


@router.post("/initiate", response_model=InitiateCallResponse)
async def initiate_call(request: InitiateCallRequest, background_tasks: BackgroundTasks):
    """
    Initiate an outbound AI voice call.
    Returns immediately with a call_id; poll GET /calls/{call_id}/status for updates.
    """
    session = call_store.create_session(
        phone_number=request.phone_number,
        scenario=request.scenario,
        scenario_data=request.scenario_data,
        call_language=request.call_language,
    )

    background_tasks.add_task(
        _prepare_and_call,
        session.call_id,
        request.phone_number,
        request.scenario,
        request.scenario_data,
        request.call_language,
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
        error=session.error,
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
