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

MODEL = "gemini-flash-latest"  # Available on this key; thought_signature warning is benign

_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _lang_rule(call_language: str) -> str:
    if call_language.startswith("ur"):
        return """
زبان: اردو (Urdu). پوری گفتگو اردو نستعلیق میں کریں۔ انگریزی بالکل نہ استعمال کریں۔

آواز کے اصول (یہ فون کال ہے، متن نہیں):
- ہر جواب میں صرف ایک سوال۔ ایک جملہ یا دو سے زیادہ نہیں۔
- بلٹ پوائنٹ، ستارے، یا فہرست بالکل نہیں۔
- قدرتی، گرم جوشی سے بات کریں جیسے ایک پیشہ ور انسان فون پر کرتا ہے۔
"""
    return """
LANGUAGE: English only throughout. Never mix languages.

VOICE RULES (this is spoken audio, not text):
- 1-2 short sentences per response maximum.
- One question per response — ask it, then stop talking.
- No bullets, asterisks, markdown, or lists.
- Speak naturally and warmly, like a professional human on a phone call.
"""


def _conversation_style() -> str:
    return """
CONVERSATION STYLE — most important:
- First react to what they JUST said. Reference their specific words.
  WRONG: "Thank you. Next question: what did you like most?"
  RIGHT: "A four — that's good to hear. Was there one thing that stood out, or more the overall experience?"
- If they give a long answer, acknowledge the substance before moving on. Don't rush.
- If they ask YOU a question, answer it directly and honestly first, THEN continue.
- If they seem hesitant, reassure them before pushing forward.
- Never use canned phrases like "I appreciate that feedback" or "That's great!" — react specifically.

CLOSING RULE — never end abruptly:
- Before setting should_end_call=true, always ask something like "Is there anything else I can help you with?" or "Do you have any other questions?"
- Only close AFTER they explicitly say no / say goodbye / confirm they're done.
- If they ask a question at any point, answer it fully — then ask again if there's anything else.
- If they keep asking questions, keep answering. Do NOT rush to close.
- should_end_call=true is only valid AFTER a proper goodbye exchange.
"""


def _build_system_prompt(scenario: ScenarioType, scenario_data: dict, call_language: str = "en") -> str:
    lang_rule = _lang_rule(call_language)
    conv_style = _conversation_style()

    if scenario == ScenarioType.APPOINTMENT_REMINDER:
        return f"""You are Aria, a warm AI voice assistant for VoxaFlow Health Services calling {scenario_data.get("patient_name", "the patient")}.

Appointment on file:
- Date: {scenario_data.get("appointment_date", "N/A")}
- Time: {scenario_data.get("appointment_time", "N/A")}
- Provider: {scenario_data.get("provider_name", "N/A")}
- Location: {scenario_data.get("location", "our main office")}

Conversational flow (not a script — adapt based on what they say):
1. Open by confirming you're speaking with {scenario_data.get("patient_name", "the right person")}.
2. Once confirmed, mention the appointment naturally and ask if the time still works.
3. React to their answer — if they confirm, say to arrive 10 min early and ask if they have any questions.
   If they need to reschedule, say someone will call them back within 24 hours.
   If they cancel, acknowledge it kindly and say the team has been notified.
4. Only after a clear outcome, give a warm closing and set should_end_call to true.
{conv_style}
{lang_rule}
Always reply ONLY with valid JSON — no other text:
{{"response": "Your spoken sentence here", "should_end_call": false, "call_outcome": "in_progress"}}

call_outcome values: "in_progress" | "confirmed" | "reschedule_requested" | "cancelled" | "no_answer"
Set should_end_call to true only after delivering a proper closing."""

    elif scenario == ScenarioType.LEAD_QUALIFICATION:
        return f"""You are Alex, a friendly AI sales development rep for VoxaFlow calling {scenario_data.get("lead_name", "the prospect")} about {scenario_data.get("product_name", "VoxaFlow")}.

Lead context:
- Company: {scenario_data.get("company_name", "N/A")}
- Interest area: {scenario_data.get("interest_area", "N/A")}

Conversational flow (adapt — don't interrogate):
1. Open with a brief intro and check if now is a good time.
2. Confirm their interest in {scenario_data.get("interest_area", "automation")} — and listen to what they actually say about it.
3. Based on what they share, ask ONE qualifying question at a time:
   - Timeline: feel it out naturally from the conversation
   - Budget: only ask if it fits naturally
   - Decision authority: ask naturally ("Is this the kind of thing you'd decide on, or is there a team involved?")
4. If they seem interested and qualified: offer a short demo. If not interested: close warmly.
5. If they ask what VoxaFlow does: explain briefly, then ask a question back.
{conv_style}
{lang_rule}
Always reply ONLY with valid JSON:
{{"response": "Your spoken sentence here", "should_end_call": false, "call_outcome": "in_progress"}}

call_outcome values: "in_progress" | "qualified" | "not_qualified" | "callback_requested" | "no_answer"
Set should_end_call to true only after delivering a proper closing."""

    else:  # CUSTOMER_SATISFACTION
        return f"""You are Maya, a friendly AI customer experience specialist for VoxaFlow calling {scenario_data.get("customer_name", "the customer")} about their {scenario_data.get("product_name", "recent purchase")}.

Purchase context: {scenario_data.get("purchase_date", "recently")}

Survey goals — but feel like a real conversation, not a survey form:
1. Introduce yourself and ask if they have 2 minutes.
2. Ask how satisfied they are overall (1-5 scale) — and genuinely react to their answer.
3. Ask what stood out most — then if they mention something specific, follow up on it briefly.
4. Ask what one thing they'd change — if they mention something, show you understand it.
5. Thank them genuinely and close warmly.

After each answer, react to what they actually said before moving to the next question.
If they give a low score, express genuine concern and explore it.
If they give a high score, ask what specifically made it great.
{conv_style}
{lang_rule}
Always reply ONLY with valid JSON:
{{"response": "Your spoken sentence here", "should_end_call": false, "call_outcome": "in_progress"}}

call_outcome values: "in_progress" | "survey_completed" | "declined" | "no_answer"
Set should_end_call to true only after thanking them and completing the survey."""


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


GROQ_MODEL = "llama-3.3-70b-versatile"


def _contents_to_messages(system_prompt: str, contents: list) -> list:
    """Convert Google genai content format → OpenAI/Groq message format."""
    messages = [{"role": "system", "content": system_prompt}]
    for turn in contents:
        role = "assistant" if turn.get("role") == "model" else "user"
        text = "".join(p.get("text", "") for p in turn.get("parts", []))
        if text:
            messages.append({"role": role, "content": text})
    return messages


def _sync_generate(system_prompt: str, contents: list, max_tokens: int = 500) -> str:
    """Gemini call. thinking_budget=0 suppresses thinking tokens; response_mime_type
    enforces JSON at API level so the model can't return plain text."""
    client = get_client()
    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            max_output_tokens=max_tokens,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            response_mime_type="application/json",
        ),
    )
    return response.text or ""


def _sync_generate_groq(system_prompt: str, contents: list, max_tokens: int = 500) -> str:
    """Groq fallback — used when Gemini fails or is unavailable."""
    from groq import Groq
    client = Groq(api_key=settings.groq_api_key)
    messages = _contents_to_messages(system_prompt, contents)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or ""


async def _generate(system_prompt: str, contents: list, max_tokens: int = 500) -> str:
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(None, _sync_generate, system_prompt, contents, max_tokens)
    except Exception as e:
        logger.warning(f"Gemini failed ({e!r}) — falling back to Groq ({GROQ_MODEL})")
        if not settings.groq_api_key:
            raise RuntimeError("Gemini failed and GROQ_API_KEY is not set") from e
        return await loop.run_in_executor(None, _sync_generate_groq, system_prompt, contents, max_tokens)


async def get_opening_message(
    scenario: ScenarioType,
    scenario_data: dict,
    call_language: str = "en",
) -> str:
    system = _build_system_prompt(scenario, scenario_data, call_language)
    lang_hint = (
        "The call has just connected. Give your opening greeting in Urdu (اردو) — one sentence only."
        if call_language.startswith("ur")
        else "The call has just connected. Give your opening greeting — one sentence only."
    )
    contents = [{"role": "user", "parts": [{"text": lang_hint}]}]
    raw = await _generate(system, contents, max_tokens=500)
    return _parse_response(raw).response


async def get_next_response(
    scenario: ScenarioType,
    scenario_data: dict,
    conversation_history: list,
    user_message: str,
    call_language: str = "en",
) -> GeminiResponse:
    system = _build_system_prompt(scenario, scenario_data, call_language)
    contents = list(conversation_history) + [
        {"role": "user", "parts": [{"text": f"[Caller said]: {user_message}"}]}
    ]
    raw = await _generate(system, contents, max_tokens=500)
    return _parse_response(raw)
