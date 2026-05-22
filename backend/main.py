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
from services import whisper_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up Whisper model at startup to avoid first-call latency
    logger.info("Warming up Whisper model...")
    await whisper_service.preload_model(settings.whisper_model)
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
        "whisper_model": settings.whisper_model,
        "backend_url": settings.backend_url,
    }


@app.get("/")
async def root():
    return {"message": "VoxaFlow API — visit /docs for the OpenAPI interface"}
