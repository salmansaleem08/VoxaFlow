"""
In-memory call session store.
Production replacement: Redis or a database.
"""
from typing import Optional, Dict
from datetime import datetime
from models.schemas import CallSession, CallStatus, CallOutcome, TranscriptEntry
import uuid


_store: Dict[str, CallSession] = {}


def create_session(
    phone_number: str,
    scenario: str,
    scenario_data: dict,
) -> CallSession:
    call_id = str(uuid.uuid4())
    session = CallSession(
        call_id=call_id,
        phone_number=phone_number,
        scenario=scenario,
        scenario_data=scenario_data,
    )
    _store[call_id] = session
    return session


def get_session(call_id: str) -> Optional[CallSession]:
    return _store.get(call_id)


def get_session_by_twilio_sid(twilio_call_sid: str) -> Optional[CallSession]:
    for session in _store.values():
        if session.twilio_call_sid == twilio_call_sid:
            return session
    return None


def update_status(call_id: str, status: CallStatus, twilio_call_sid: Optional[str] = None) -> None:
    session = _store.get(call_id)
    if session:
        session.status = status
        if twilio_call_sid:
            session.twilio_call_sid = twilio_call_sid
        session.updated_at = datetime.utcnow()


def update_outcome(call_id: str, outcome: CallOutcome) -> None:
    session = _store.get(call_id)
    if session:
        session.outcome = outcome
        session.updated_at = datetime.utcnow()


def append_transcript(call_id: str, speaker: str, text: str) -> None:
    session = _store.get(call_id)
    if session:
        session.transcript.append(
            TranscriptEntry(speaker=speaker, text=text, timestamp=datetime.utcnow())
        )
        session.updated_at = datetime.utcnow()


def update_language(call_id: str, language: str) -> None:
    session = _store.get(call_id)
    if session:
        session.call_language = language
        session.updated_at = datetime.utcnow()


def append_conversation(call_id: str, role: str, content: str) -> None:
    """Append to Gemini conversation history (role: 'user' or 'model')."""
    session = _store.get(call_id)
    if session:
        session.conversation_history.append({"role": role, "parts": [{"text": content}]})
        session.updated_at = datetime.utcnow()


def list_sessions(limit: int = 50) -> list:
    sessions = sorted(_store.values(), key=lambda s: s.created_at, reverse=True)
    return sessions[:limit]
