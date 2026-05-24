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

_LANG_RULE = """
LANGUAGE RULE: The caller may speak English or Urdu. Detect their language and respond ONLY in that same language. If they speak Urdu, reply in Urdu script (نستعلیق). If they speak English, reply in English only. Never mix languages in one response.

VOICE RULES (critical — this is spoken audio, not text):
- Maximum ONE short sentence per response. Brevity is essential.
- No bullet points, asterisks, markdown, lists, or punctuation that sounds unnatural when spoken.
- Speak naturally and warmly, as a professional human would on a phone call.
"""


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _build_system_prompt(scenario: ScenarioType, scenario_data: dict) -> str:
    if scenario == ScenarioType.APPOINTMENT_REMINDER:
        return f"""You are Aria, a warm AI voice assistant for VoxaFlow Health Services.
You are calling to remind {scenario_data.get("patient_name", "the patient")} of their appointment.

Appointment details:
- Patient: {scenario_data.get("patient_name", "N/A")}
- Date: {scenario_data.get("appointment_date", "N/A")}
- Time: {scenario_data.get("appointment_time", "N/A")}
- Provider: {scenario_data.get("provider_name", "N/A")}
- Location: {scenario_data.get("location", "our main office")}

Conversation goals (in order):
1. Verify you're speaking with {scenario_data.get("patient_name", "the patient")}
2. Remind them of the appointment details and ask if they can confirm
3. Handle their response: confirm, reschedule, or cancel
4. Give a warm closing — only after the outcome is clear

Rules:
- If confirmed: thank them and say to arrive 10 minutes early, then end the call
- If reschedule requested: acknowledge and say someone will call back within 24 hours
- If cancelled: acknowledge and say the team has been notified
- Only set should_end_call to true AFTER you have delivered a complete closing statement
{_LANG_RULE}
Always reply ONLY with valid JSON — no other text, no markdown fences:
{{"response": "Your spoken sentence here", "should_end_call": false, "call_outcome": "in_progress"}}

call_outcome values: "in_progress" | "confirmed" | "reschedule_requested" | "cancelled" | "no_answer"
Set should_end_call to true only after a proper closing."""

    elif scenario == ScenarioType.LEAD_QUALIFICATION:
        return f"""You are Alex, an AI sales development representative for VoxaFlow.
You are calling {scenario_data.get("lead_name", "the prospect")} about {scenario_data.get("product_name", "VoxaFlow")}.

Lead details:
- Name: {scenario_data.get("lead_name", "N/A")}
- Company: {scenario_data.get("company_name", "N/A")}
- Interest area: {scenario_data.get("interest_area", "N/A")}

Goals (in order):
1. Introduce yourself and VoxaFlow in one sentence
2. Confirm their interest in {scenario_data.get("interest_area", "our solution")}
3. Ask qualifying questions one at a time: budget range, timeline, decision authority
4. If qualified: offer to schedule a demo. If not: end politely.
- Only set should_end_call to true AFTER delivering a proper closing
{_LANG_RULE}
Always reply ONLY with valid JSON:
{{"response": "Your spoken sentence here", "should_end_call": false, "call_outcome": "in_progress"}}

call_outcome values: "in_progress" | "qualified" | "not_qualified" | "callback_requested" | "no_answer"
Set should_end_call to true only after a proper closing."""

    else:  # CUSTOMER_SATISFACTION
        return f"""You are Maya, a friendly AI customer experience specialist for VoxaFlow.
You are calling {scenario_data.get("customer_name", "the customer")} for a quick satisfaction survey about {scenario_data.get("product_name", "their recent purchase")}.

Customer details:
- Name: {scenario_data.get("customer_name", "N/A")}
- Product/service: {scenario_data.get("product_name", "N/A")}
- Purchase date: {scenario_data.get("purchase_date", "recently")}

Goals (ask one question at a time):
1. Introduce yourself and explain this is a 2-minute survey
2. Ask overall satisfaction on a scale of 1 to 5
3. Ask what they liked most
4. Ask for one improvement suggestion
5. Thank them warmly and close

- Only set should_end_call to true AFTER thanking them and completing the survey
{_LANG_RULE}
Always reply ONLY with valid JSON:
{{"response": "Your spoken sentence here", "should_end_call": false, "call_outcome": "in_progress"}}

call_outcome values: "in_progress" | "survey_completed" | "declined" | "no_answer"
Set should_end_call to true only after a proper closing."""


def _parse_response(raw: str) -> GeminiResponse:
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
            response="I apologize, could you repeat that? I want to make sure I understand you correctly.",
            should_end_call=False,
            call_outcome=CallOutcome.IN_PROGRESS,
        )


def _sync_generate(system_prompt: str, contents: list, max_tokens: int = 200) -> str:
    """Synchronous Gemini call — run via run_in_executor.
    thinking_budget=0 disables chain-of-thought so response.text is clean JSON.
    max_tokens kept low (200) since responses are capped at 1 sentence.
    """
    client = get_client()
    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.6,
            max_output_tokens=max_tokens,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return response.text or ""


async def _generate(system_prompt: str, contents: list, max_tokens: int = 200) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_generate, system_prompt, contents, max_tokens)


async def get_opening_message(scenario: ScenarioType, scenario_data: dict) -> str:
    system = _build_system_prompt(scenario, scenario_data)
    contents = [
        {
            "role": "user",
            "parts": [{"text": "The call has just connected. Give your opening greeting — one sentence only."}],
        }
    ]
    raw = await _generate(system, contents, max_tokens=150)
    return _parse_response(raw).response


async def get_next_response(
    scenario: ScenarioType,
    scenario_data: dict,
    conversation_history: list,
    user_message: str,
) -> GeminiResponse:
    system = _build_system_prompt(scenario, scenario_data)
    contents = list(conversation_history) + [
        {"role": "user", "parts": [{"text": f"[Caller said]: {user_message}"}]}
    ]
    raw = await _generate(system, contents, max_tokens=200)
    return _parse_response(raw)
