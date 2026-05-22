"""
Twilio service — makes outbound calls and provides helper functions.
"""
import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from config import settings

logger = logging.getLogger(__name__)


def get_client() -> Client:
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def make_outbound_call(to: str, call_id: str) -> str:
    """
    Initiate an outbound call to `to`.
    Returns the Twilio CallSid on success.
    """
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
        logger.error(f"Twilio error: {e}")
        raise


async def download_recording(recording_url: str, output_path: str) -> None:
    """
    Download a Twilio recording as WAV.
    Appends '.wav' to the URL to get PCM WAV instead of MP3.
    """
    import httpx

    wav_url = recording_url.rstrip("/") + ".wav"
    auth = (settings.twilio_account_sid, settings.twilio_auth_token)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(wav_url, auth=auth)
        response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)

    logger.info(f"Recording saved to {output_path} ({len(response.content)} bytes)")
