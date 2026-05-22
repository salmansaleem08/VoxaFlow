"""
Gemini LLM service — manages conversation state and generates agent responses.
"""
import json
import re
import logging
import google.generativeai as genai
from models.schemas import ScenarioType, GeminiResponse, CallOutcome
from config import settings

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.gemini_api_key)

_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash-latest",
    generation_config=genai.GenerationConfig(
        temperature=0.7,
        max_output_tokens=300,
        response_mime_type="application/json",
    ),
)


# ── System prompts per scenario ───────────────────────────────────────────────

def _build_system_prompt(scenario: ScenarioType, scenario_data: dict) -> str:
    if scenario == ScenarioType.APPOINTMENT_REMINDER:
        return f"""You are Aria, a warm and professional AI voice assistant for VoxaFlow Health Services.
You are calling {scenario_data.get("patient_name", "the patient")} to remind them about their appointment.

Appointment details:
- Patient: {scenario_data.get("patient_name", "N/A")}
- Date: {scenario_data.get("appointment_date", "N/A")}
- Time: {scenario_data.get("appointment_time", "N/A")}
- Provider: {scenario_data.get("provider_name", "N/A")}
- Location: {scenario_data.get("location", "our main office")}

Your conversation goals (in order):
1. Verify you're speaking with {scenario_data.get("patient_name", "the patient")}
2. Remind them of the appointment and ask for confirmation
3. Handle their response: confirm, reschedule, or cancel
4. Politely close the call

Critical rules for VOICE calls:
- Keep each response to 1-3 sentences maximum — this is spoken audio
- Be natural, warm, and conversational
- Do NOT use bullet points, markdown, or lists in responses
- If they confirm: thank them, remind them to arrive 10 minutes early
- If they want to reschedule: acknowledge, say your scheduling team will call back within 24 hours
- If they want to cancel: acknowledge politely, inform the team will note it
- After the main goal is achieved, wrap up gracefully

Always respond with valid JSON:
{{
  "response": "Your exact spoken words here",
  "should_end_call": false,
  "call_outcome": "in_progress"
}}

call_outcome options: "in_progress", "confirmed", "reschedule_requested", "cancelled", "no_answer"
Set should_end_call to true when the conversation is naturally complete."""

    elif scenario == ScenarioType.LEAD_QUALIFICATION:
        return f"""You are Alex, a professional AI sales development representative for VoxaFlow.
You are calling {scenario_data.get("lead_name", "the prospect")} regarding {scenario_data.get("product_name", "VoxaFlow")}.

Lead details:
- Name: {scenario_data.get("lead_name", "N/A")}
- Company: {scenario_data.get("company_name", "N/A")}
- Interest area: {scenario_data.get("interest_area", "N/A")}

Your goals:
1. Introduce yourself and VoxaFlow briefly
2. Confirm their interest in {scenario_data.get("interest_area", "our solution")}
3. Ask 2-3 qualifying questions (budget, timeline, decision-making authority)
4. If qualified: schedule a follow-up demo. If not: end politely.

Rules: Keep responses to 1-3 sentences. Voice call — no bullet points or markdown.

Always respond with valid JSON:
{{
  "response": "Your exact spoken words here",
  "should_end_call": false,
  "call_outcome": "in_progress"
}}

call_outcome options: "in_progress", "qualified", "not_qualified", "callback_requested", "no_answer"
Set should_end_call to true when the conversation is complete."""

    else:  # CUSTOMER_SATISFACTION
        return f"""You are Maya, a friendly AI customer experience specialist for VoxaFlow.
You are calling {scenario_data.get("customer_name", "the customer")} for a brief satisfaction survey about {scenario_data.get("product_name", "their recent purchase")}.

Customer details:
- Name: {scenario_data.get("customer_name", "N/A")}
- Product/service: {scenario_data.get("product_name", "N/A")}
- Purchase date: {scenario_data.get("purchase_date", "recently")}

Your goals:
1. Introduce yourself and explain this is a quick 2-minute survey
2. Ask for overall satisfaction (scale of 1-5)
3. Ask one follow-up question about what they liked most
4. Ask if there's anything that could be improved
5. Thank them and close

Rules: Keep responses to 1-3 sentences. Voice call — no bullet points or markdown.

Always respond with valid JSON:
{{
  "response": "Your exact spoken words here",
  "should_end_call": false,
  "call_outcome": "in_progress"
}}

call_outcome options: "in_progress", "survey_completed", "declined", "no_answer"
Set should_end_call to true when the survey is complete or declined."""


def _parse_response(raw: str) -> GeminiResponse:
    """Parse Gemini JSON response, with fallback for malformed output."""
    try:
        # Strip markdown code fences if present
        clean = re.sub(r"```(?:json)?\n?", "", raw).strip()
        data = json.loads(clean)
        return GeminiResponse(
            response=data.get("response", "I apologize, I'm having trouble processing that. Could you repeat that?"),
            should_end_call=bool(data.get("should_end_call", False)),
            call_outcome=CallOutcome(data.get("call_outcome", "in_progress")),
        )
    except Exception as e:
        logger.warning(f"Failed to parse Gemini JSON response: {e}\nRaw: {raw[:200]}")
        return GeminiResponse(
            response="I apologize, could you repeat that? I want to make sure I understand correctly.",
            should_end_call=False,
            call_outcome=CallOutcome.IN_PROGRESS,
        )


async def get_opening_message(scenario: ScenarioType, scenario_data: dict) -> str:
    """Generate the initial greeting for the call."""
    system = _build_system_prompt(scenario, scenario_data)
    prompt = f"{system}\n\nThe call has just connected. Generate ONLY the opening greeting."

    response = _model.generate_content(prompt)
    parsed = _parse_response(response.text)
    return parsed.response


async def get_next_response(
    scenario: ScenarioType,
    scenario_data: dict,
    conversation_history: list,
    user_message: str,
) -> GeminiResponse:
    """Generate the next agent response given the conversation history."""
    system = _build_system_prompt(scenario, scenario_data)

    # Build full conversation for Gemini
    messages = [{"role": "user", "parts": [{"text": system + "\n\nBegin the conversation now. The call just connected — say your opening greeting."}]}]

    # Replay history
    for entry in conversation_history:
        messages.append(entry)

    # Add new user message
    messages.append({"role": "user", "parts": [{"text": f"[Caller said]: {user_message}"}]})

    chat = _model.start_chat(history=messages[:-1])
    response = chat.send_message(messages[-1]["parts"][0]["text"])
    return _parse_response(response.text)
