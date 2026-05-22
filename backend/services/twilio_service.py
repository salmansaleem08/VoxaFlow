"""
Twilio service — makes outbound calls and downloads recordings.

Auth priority:
  1. API Key auth (TWILIO_API_KEY + TWILIO_API_SECRET + TWILIO_ACCOUNT_SID)
  2. Account SID + Auth Token (TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN)
"""
import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from config import settings

logger = logging.getLogger(__name__)


def get_client() -> Client:
    if settings.using_api_key_auth:
        # API Key authentication: Client(api_key, api_secret, account_sid=AC...)
        return Client(
            settings.twilio_api_key,
            settings.twilio_api_secret,
            account_sid=settings.twilio_account_sid,
        )
    # Standard auth: Client(account_sid, auth_token)
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def make_outbound_call(to: str, call_id: str) -> str:
    """Initiate an outbound call. Returns the Twilio CallSid."""
    client = get_client()
    webhook_url = f"{settings.backend_url}/api/webhooks/answer/{call_id}"

    try:
        call = client.calls.create(
            to=to,
            from_=settings.twilio_phone_number,
            url=webhook_url,
            method="POST",
            status_callback=f"{settings.backend_url}/api/webhooks/status/{call_id}",
            status_callback_method="POST",
            status_callback_event=["initiated", "ringing", "answered", "completed"],
        )
        logger.info(f"Call initiated: {call.sid} → {to}")
        return call.sid
    except TwilioRestException as e:
        logger.error(f"Twilio error making call to {to}: {e}")
        raise


async def download_recording(recording_url: str, output_path: str) -> None:
    """
    Download a Twilio recording as WAV (PCM, 8 kHz).
    Appends '.wav' to get PCM format instead of MP3.
    """
    import httpx

    wav_url = recording_url.rstrip("/") + ".wav"

    # Auth: use API Key or Account SID depending on config
    if settings.using_api_key_auth:
        auth = (settings.twilio_api_key, settings.twilio_api_secret)
    else:
        auth = (settings.twilio_account_sid, settings.twilio_auth_token)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(wav_url, auth=auth)
        response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)

    logger.info(f"Recording saved → {output_path} ({len(response.content)} bytes)")
