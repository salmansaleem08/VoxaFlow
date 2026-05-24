"""
VoxaFlow API — FastAPI backend
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from routers import calls, webhooks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _validate_config():
    errors = []
    warnings = []

    if not settings.gemini_api_key:
        errors.append("GEMINI_API_KEY is not set")
    if not settings.deepgram_api_key:
        errors.append("DEEPGRAM_API_KEY is not set")
    if not settings.twilio_account_sid:
        errors.append("TWILIO_ACCOUNT_SID is not set")
    if not settings.twilio_phone_number:
        errors.append("TWILIO_PHONE_NUMBER is not set")

    using_api_key = settings.using_api_key_auth
    if using_api_key:
        logger.info("Twilio auth: API Key (SK…)")
        if not settings.twilio_auth_token:
            errors.append(
                "TWILIO_AUTH_TOKEN is required even with API Key auth "
                "(used to download recordings from media.twilio.com)"
            )
    else:
        logger.info("Twilio auth: Account SID + Auth Token")
        if not settings.twilio_auth_token:
            errors.append("TWILIO_AUTH_TOKEN is not set")

    if "localhost" in settings.backend_url or "127.0.0.1" in settings.backend_url:
        errors.append(
            f"BACKEND_URL is '{settings.backend_url}' — Twilio cannot reach localhost. "
            "Run ngrok ('ngrok http 8000') and set BACKEND_URL to the https://xxxx.ngrok-free.app URL in your .env"
        )
    else:
        logger.info(f"Twilio webhooks → {settings.backend_url}")

    for w in warnings:
        logger.warning(f"CONFIG WARNING: {w}")
    for e in errors:
        logger.error(f"CONFIG ERROR: {e}")

    if errors:
        logger.error(
            "Fix the above configuration errors before placing calls. "
            "See .env.example for reference."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_config()
    logger.info("VoxaFlow API is ready.")
    yield
    logger.info("VoxaFlow API shutting down.")


app = FastAPI(
    title="VoxaFlow API",
    description="AI-powered outbound voice call platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated TTS audio files
app.mount("/media", StaticFiles(directory=str(settings.media_dir)), name="media")

# Routers
app.include_router(calls.router, prefix="/api/calls", tags=["Calls"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "1.0.0",
        "stt": "deepgram-nova-2",
        "backend_url": settings.backend_url,
    }


@app.get("/")
async def root():
    return {"message": "VoxaFlow API — visit /docs for the OpenAPI interface"}
