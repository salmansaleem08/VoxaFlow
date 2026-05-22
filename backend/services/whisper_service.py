"""
Whisper STT service.
Loads WAV audio without ffmpeg by converting to numpy arrays via scipy,
then passes the array directly to whisper.transcribe().

On Apple Silicon (M4) this uses MPS for hardware acceleration when available.
"""
import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_model = None
_device = "cpu"


def _init_model(model_size: str = "base"):
    global _model, _device
    if _model is not None:
        return _model

    import torch
    import whisper

    if torch.backends.mps.is_available():
        _device = "cpu"  # Whisper MPS support is experimental; cpu is more stable
        logger.info("Apple Silicon detected — using CPU for Whisper (MPS experimental)")
    elif torch.cuda.is_available():
        _device = "cuda"
        logger.info("CUDA GPU detected — using GPU for Whisper")
    else:
        logger.info("Using CPU for Whisper")

    logger.info(f"Loading Whisper model '{model_size}'...")
    _model = whisper.load_model(model_size, device=_device)
    logger.info("Whisper model loaded successfully")
    return _model


def _load_wav_as_array(wav_path: str) -> np.ndarray:
    """
    Load a WAV file and return a float32 numpy array resampled to 16 kHz.
    Uses scipy — no ffmpeg required.
    """
    from scipy.io import wavfile
    from scipy.signal import resample as scipy_resample

    rate, data = wavfile.read(wav_path)

    # Convert integer PCM to float32 in [-1, 1]
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 2147483648.0
    elif data.dtype == np.uint8:
        data = (data.astype(np.float32) - 128.0) / 128.0
    elif data.dtype == np.float32:
        pass
    else:
        data = data.astype(np.float32)

    # Stereo → mono
    if data.ndim == 2:
        data = data.mean(axis=1).astype(np.float32)

    # Resample to 16 kHz (Whisper requirement)
    if rate != 16000:
        target_length = int(len(data) * 16000 / rate)
        data = scipy_resample(data, target_length).astype(np.float32)

    return data


def _transcribe_sync(audio_path: str, model_size: str) -> str:
    import whisper

    model = _init_model(model_size)

    # Load and preprocess audio without ffmpeg
    audio_array = _load_wav_as_array(audio_path)

    result = model.transcribe(audio_array, language="en", fp16=False)
    text = result["text"].strip()
    logger.info(f"Transcription: '{text[:100]}...' " if len(text) > 100 else f"Transcription: '{text}'")
    return text


async def transcribe(audio_path: str, model_size: str = "base") -> str:
    """Transcribe a WAV file asynchronously using Whisper."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _transcribe_sync, audio_path, model_size)


async def preload_model(model_size: str = "base") -> None:
    """Warm up the Whisper model at startup to avoid cold-start latency."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _init_model, model_size)
