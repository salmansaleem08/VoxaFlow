from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum


class ScenarioType(str, Enum):
    APPOINTMENT_REMINDER = "appointment_reminder"
    LEAD_QUALIFICATION = "lead_qualification"
    CUSTOMER_SATISFACTION = "customer_satisfaction"


class CallStatus(str, Enum):
    PENDING = "pending"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"


class CallOutcome(str, Enum):
    CONFIRMED = "confirmed"
    RESCHEDULE_REQUESTED = "reschedule_requested"
    CANCELLED = "cancelled"
    QUALIFIED = "qualified"
    NOT_QUALIFIED = "not_qualified"
    CALLBACK_REQUESTED = "callback_requested"
    SURVEY_COMPLETED = "survey_completed"
    DECLINED = "declined"
    NO_ANSWER = "no_answer"
    IN_PROGRESS = "in_progress"


# ── Scenario-specific data ────────────────────────────────────────────────────

class AppointmentData(BaseModel):
    patient_name: str
    appointment_date: str
    appointment_time: str
    provider_name: str
    location: Optional[str] = "our main office"


class LeadData(BaseModel):
    lead_name: str
    company_name: Optional[str] = ""
    interest_area: str
    product_name: str = "VoxaFlow"


class SurveyData(BaseModel):
    customer_name: str
    product_name: str
    purchase_date: Optional[str] = "recently"


# ── API request/response models ───────────────────────────────────────────────

class InitiateCallRequest(BaseModel):
    phone_number: str = Field(..., description="Target phone number in E.164 format (+1xxxxxxxxxx)")
    scenario: ScenarioType
    scenario_data: dict = Field(..., description="Scenario-specific fields")


class TranscriptEntry(BaseModel):
    speaker: Literal["agent", "user"]
    text: str
    timestamp: datetime


class CallSession(BaseModel):
    call_id: str
    phone_number: str
    scenario: ScenarioType
    scenario_data: dict
    status: CallStatus = CallStatus.PENDING
    outcome: Optional[CallOutcome] = None
    twilio_call_sid: Optional[str] = None
    transcript: List[TranscriptEntry] = []
    conversation_history: List[dict] = []
    call_language: str = "en"          # detected via Deepgram; "en" or "ur"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CallStatusResponse(BaseModel):
    call_id: str
    status: CallStatus
    outcome: Optional[CallOutcome]
    transcript: List[TranscriptEntry]
    phone_number: str
    scenario: ScenarioType
    created_at: datetime
    updated_at: datetime


class InitiateCallResponse(BaseModel):
    call_id: str
    status: CallStatus
    message: str


class GeminiResponse(BaseModel):
    response: str
    should_end_call: bool = False
    call_outcome: CallOutcome = CallOutcome.IN_PROGRESS
