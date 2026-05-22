"""
Gemini LLM service — manages conversation state and generates agent responses.
Uses the google-genai SDK (replacement for deprecated google-generativeai).
"""
import json
import re
import logging
import asyncio
from typing import Optional

from google import genai
from google.genai import types

from models.schemas import ScenarioType, GeminiResponse, CallOutcome
from config import settings

logger = logging.getLogger(__name__)

MODEL = "gemini-flash-latest"

_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


# ── System prompts per scenario ───────────────────────────────────────────────

def _build_system_prompt(scenario: ScenarioType, scenario_data: dict) -> str:
    if scenario == ScenarioType.APPOINTMENT_REMINDER:
        return f"""You are Aria, a warm and professional AI voice assistant for VoxaFlow Health Services.
You are calling to remind {scenario_data.get("patient_name", "the patient")} about their appointment.

Appointment details:
- Patient: {scenario_data.get("patient_name", "N/A")}
- Date: {scenario_data.get("appointment_date", "N/A")}
- Time: {scenario_data.get("appointment_time", "N/A")}
- Provider: {scenario_data.get("provider_name", "N/A")}
- Location: {scenario_data.get("location", "our main office")}

Conversation goals (in order):
1. Verify you are speaking with {scenario_data.get("patient_name", "the patient")}
2. Remind them of the appointment and ask for confirmation
3. Handle their response: confirm, reschedule, or cancel
4. Politely close the call

IMPORTANT RULES for a VOICE call:
- Keep responses to 1-2 sentences maximum — this is spoken audio
- Be natural, warm, and conversational
- Never use bullet points, markdown, lists, or asterisks in responses
- If they confirm: thank them and remind them to arrive 10 minutes early, then end the call
- If they want to reschedule: acknowledge, say a scheduling team member will call back within 24 hours
- If they want to cancel: acknowledge politely, say the team has been notified
- Once the main goal is resolved, wrap up and set should_end_call to true

Always reply ONLY with valid JSON (no other text):
{{"response": "Your exact spoken words here", "should_end_call": false, "call_outcome": "in_progress"}}

call_outcome values: "in_progress" | "confirmed" | "reschedule_requested" | "cancelled" | "no_answer"
Set should_end_call to true when the conversation is naturally complete."""

    elif scenario == ScenarioType.LEAD_QUALIFICATION:
        return f"""You are Alex, a professional AI sales development representative for VoxaFlow.
You are calling {scenario_data.get("lead_name", "the prospect")} about {scenario_data.get("product_name", "VoxaFlow")}.

Lead details:
- Name: {scenario_data.get("lead_name", "N/A")}
- Company: {scenario_data.get("company_name", "N/A")}
- Interest area: {scenario_data.get("interest_area", "N/A")}

Goals:
1. Introduce yourself and VoxaFlow briefly
2. Confirm their interest in {scenario_data.get("interest_area", "our solution")}
3. Ask 2-3 qualifying questions (budget range, timeline, decision authority)
4. If qualified: offer to schedule a demo. If not: end politely.

IMPORTANT: Keep each response to 1-2 sentences. Voice call — no bullet points or markdown.

Always reply ONLY with valid JSON (no other text):
{{"response": "Your spoken words here", "should_end_call": false, "call_outcome": "in_progress"}}

call_outcome values: "in_progress" | "qualified" | "not_qualified" | "callback_requested" | "no_answer"
Set should_end_call to true when complete."""

    else:  # CUSTOMER_SATISFACTION
        return f"""You are Maya, a friendly AI customer experience specialist for VoxaFlow.
You are calling {scenario_data.get("customer_name", "the customer")} for a brief satisfaction survey about {scenario_data.get("product_name", "their recent purchase")}.

Customer details:
- Name: {scenario_data.get("customer_name", "N/A")}
- Product/service: {scenario_data.get("product_name", "N/A")}
- Purchase date: {scenario_data.get("purchase_date", "recently")}

Goals:
1. Introduce yourself and explain this is a quick 2-minute survey
2. Ask overall satisfaction on a scale of 1 to 5
3. Ask what they liked most
4. Ask for any improvement suggestions
5. Thank them and close

IMPORTANT: Keep responses to 1-2 sentences. Voice call — no bullet points or markdown.

Always reply ONLY with valid JSON (no other text):
{{"response": "Your spoken words here", "should_end_call": false, "call_outcome": "in_progress"}}

call_outcome values: "in_progress" | "survey_completed" | "declined" | "no_answer"
Set should_end_call to true when complete."""


def _parse_response(raw: str) -> GeminiResponse:
    """Parse Gemini JSON response with fallback for malformed output."""
    try:
        clean = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        data = json.loads(clean)
        return GeminiResponse(
            response=data.get("response", "I apologize, could you please repeat that?"),
            should_end_call=bool(data.get("should_end_call", False)),
            call_outcome=CallOutcome(data.get("call_outcome", "in_progress")),
        )
    except Exception as e:
        logger.warning(f"Failed to parse Gemini response: {e!r} | raw={raw[:200]!r}")
        return GeminiResponse(
            response="I apologize, could you repeat that? I want to make sure I understand correctly.",
            should_end_call=False,
            call_outcome=CallOutcome.IN_PROGRESS,
        )


def _sync_generate(system_prompt: str, contents: list, max_tokens: int = 500) -> str:
    """Synchronous Gemini call — run via run_in_executor to stay non-blocking.
    thinking_budget=0 disables chain-of-thought output so response.text is clean JSON.
    """
    client = get_client()
    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            max_output_tokens=max_tokens,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return response.text or ""


async def _generate(system_prompt: str, contents: list, max_tokens: int = 500) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_generate, system_prompt, contents, max_tokens)


async def get_opening_message(scenario: ScenarioType, scenario_data: dict) -> str:
    """Generate the initial greeting for the call."""
    system = _build_system_prompt(scenario, scenario_data)
    contents = [
        {
            "role": "user",
            "parts": [{"text": "The call has just connected. Generate your opening greeting only."}],
        }
    ]
    raw = await _generate(system, contents, max_tokens=300)
    return _parse_response(raw).response


async def get_next_response(
    scenario: ScenarioType,
    scenario_data: dict,
    conversation_history: list,
    user_message: str,
) -> GeminiResponse:
    """Generate the next agent response given the conversation history."""
    system = _build_system_prompt(scenario, scenario_data)

    contents = list(conversation_history) + [
        {"role": "user", "parts": [{"text": f"[Caller said]: {user_message}"}]}
    ]

    raw = await _generate(system, contents, max_tokens=500)
    return _parse_response(raw)
