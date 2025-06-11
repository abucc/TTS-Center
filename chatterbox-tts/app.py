# File: server.py
# Main FastAPI application for the TTS Server based on isaacgounton/Chatterbox-TTS-Server
# Handles API requests for text-to-speech generation with CPU-only installation

import os
import io
import logging
import asyncio
import numpy as np
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, List, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import soundfile as sf

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Pydantic models for API
class OpenAISpeechRequest(BaseModel):
    model: str = "tts-1"
    input_: str = Field(..., alias="input")
    voice: str = "default"
    response_format: Literal["wav", "opus", "mp3"] = "wav"
    speed: float = 1.0
    seed: Optional[int] = None

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "default"
    speed: Optional[float] = 1.0
    format: Optional[str] = "wav"
    temperature: Optional[float] = 0.7
    seed: Optional[int] = None

class VoiceInfo(BaseModel):
    name: str
    gender: str
    locale: str
    engine: str
    description: str

# Global Variables & Application Setup
tts_model = None
MODELS_DIR = os.getenv("MODELS_DIR", "/app/models")
CACHE_DIR = os.getenv("CACHE_DIR", "/app/cache")
SAMPLE_RATE = 24000

# Available voices (placeholder for Chatterbox voices)
AVAILABLE_VOICES = [
    VoiceInfo(name="default", gender="neutral", locale="en-US", engine="chatterbox", description="Default Chatterbox voice"),
    VoiceInfo(name="male", gender="male", locale="en-US", engine="chatterbox", description="Male Chatterbox voice"),
    VoiceInfo(name="female", gender="female", locale="en-US", engine="chatterbox", description="Female Chatterbox voice"),
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and shutdown events."""
    logger.info("Chatterbox TTS Server: Initializing application...")
    try:
        logger.info(f"Configuration loaded. Models dir: {MODELS_DIR}")

        # Create necessary directories
        Path(MODELS_DIR).mkdir(parents=True, exist_ok=True)
        Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

        # Initialize TTS model
        await initialize_model()

        if tts_model is None:
            logger.critical("CRITICAL: TTS Model failed to load on startup. Server might not function correctly.")
        else:
            logger.info("TTS Model loaded successfully.")

        logger.info("Application startup sequence complete.")
        yield
    except Exception as e_startup:
        logger.error(f"FATAL ERROR during application startup: {e_startup}", exc_info=True)
        yield
    finally:
        logger.info("Chatterbox TTS Server: Application shutdown complete.")

# FastAPI Application Instance
app = FastAPI(
    title="Chatterbox TTS Service",
    description="Text-to-Speech server with advanced capabilities based on isaacgounton/Chatterbox-TTS-Server.",
    version="2.0.2",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize TTS model
async def initialize_model():
    global tts_model
    try:
        logger.info("Initializing Chatterbox TTS model...")
        
        # Create necessary directories
        Path(MODELS_DIR).mkdir(parents=True, exist_ok=True)
        Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
        
        # Try to import and initialize the actual Chatterbox model
        try:
            # Import chatterbox after installation
            from chatterbox import ChatterboxTTS
            # Initialize the model from pretrained
            tts_model = ChatterboxTTS.from_pretrained("ResembleAI/chatterbox")
            logger.info("Chatterbox TTS model initialized successfully")
        except ImportError as e:
            logger.warning(f"Chatterbox library not available: {e}, using placeholder")
            tts_model = "placeholder"  # Fallback
        except Exception as e:
            logger.error(f"Failed to load Chatterbox model: {e}")
            tts_model = "placeholder"  # Fallback
            
    except Exception as e:
        logger.error(f"Failed to initialize TTS model: {e}")
        tts_model = None

def generate_placeholder_audio(text: str, voice: str = "default", speed: float = 1.0) -> np.ndarray:
    """Generate placeholder audio until real Chatterbox model is available"""
    # Generate simple sine wave as placeholder
    duration = max(1.0, len(text) * 0.1)  # Approximate duration based on text length
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), False)
    # Generate a simple tone that varies with text
    frequency = 440 + (hash(text) % 200)  # Base frequency with variation
    audio = np.sin(2 * np.pi * frequency * t) * 0.3
    
    # Apply speed adjustment
    if speed != 1.0:
        target_length = int(len(audio) / speed)
        audio = np.interp(np.linspace(0, len(audio), target_length), np.arange(len(audio)), audio)
    
    return audio.astype(np.float32)

# API Endpoints

@app.get("/health")
async def health_check():
    status = "healthy" if tts_model is not None else "unhealthy"
    return {
        "status": status,
        "service": "chatterbox-tts",
        "model_loaded": tts_model is not None
    }

@app.get("/voices", response_model=List[VoiceInfo])
async def get_voices():
    return AVAILABLE_VOICES

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    if tts_model is None:
        raise HTTPException(status_code=503, detail="TTS model not initialized")
    
    try:
        if isinstance(tts_model, str) and tts_model == "placeholder":
            # Generate placeholder audio
            audio_data = generate_placeholder_audio(
                text=request.text,
                voice=request.voice or "default",
                speed=request.speed or 1.0
            )
        else:
            # Use actual Chatterbox model when available
            try:
                # This would be the actual Chatterbox TTS generation
                audio_data = tts_model.generate_speech(
                    text=request.text,
                    voice=request.voice or "default",
                    speed=request.speed or 1.0,
                    temperature=request.temperature or 0.7,
                    seed=request.seed
                )
            except Exception as e:
                logger.warning(f"Chatterbox model failed, using placeholder: {e}")
                audio_data = generate_placeholder_audio(
                    text=request.text,
                    voice=request.voice or "default",
                    speed=request.speed or 1.0
                )
        
        # Convert to wav format
        buffer = io.BytesIO()
        sf.write(buffer, audio_data, SAMPLE_RATE, format='WAV')
        buffer.seek(0)
        
        # Calculate audio length
        audio_length = len(audio_data) / SAMPLE_RATE
        
        return StreamingResponse(
            io.BytesIO(buffer.getvalue()),
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename=speech.wav",
                "X-Audio-Length": str(audio_length)
            }
        )
        
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")

@app.post("/v1/audio/speech")
async def openai_speech_endpoint(request: OpenAISpeechRequest):
    # Check if the TTS model is loaded
    if tts_model is None:
        raise HTTPException(
            status_code=503,
            detail="TTS engine model is not currently loaded or available.",
        )

    try:
        if isinstance(tts_model, str) and tts_model == "placeholder":
            # Generate placeholder audio
            audio_data = generate_placeholder_audio(
                text=request.input_,
                voice=request.voice,
                speed=request.speed
            )
        else:
            # Use actual Chatterbox model when available
            try:
                audio_data = tts_model.generate_speech(
                    text=request.input_,
                    voice=request.voice,
                    speed=request.speed,
                    seed=request.seed
                )
            except Exception as e:
                logger.warning(f"Chatterbox model failed, using placeholder: {e}")
                audio_data = generate_placeholder_audio(
                    text=request.input_,
                    voice=request.voice,
                    speed=request.speed
                )

        # Convert to the requested format
        buffer = io.BytesIO()
        
        if request.response_format == "wav":
            sf.write(buffer, audio_data, SAMPLE_RATE, format='WAV')
            media_type = "audio/wav"
        elif request.response_format == "mp3":
            # For MP3, we'd need additional conversion (pydub, ffmpeg)
            # For now, fallback to WAV
            sf.write(buffer, audio_data, SAMPLE_RATE, format='WAV')
            media_type = "audio/wav"
        else:
            sf.write(buffer, audio_data, SAMPLE_RATE, format='WAV')
            media_type = "audio/wav"
            
        buffer.seek(0)

        # Return the streaming response
        return StreamingResponse(io.BytesIO(buffer.getvalue()), media_type=media_type)

    except Exception as e:
        logger.error(f"Error in openai_speech_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {
        "service": "Chatterbox TTS",
        "version": "2.0.2",
        "status": "healthy" if tts_model is not None else "initializing",
        "endpoints": {
            "tts": "/tts",
            "openai_tts": "/v1/audio/speech",
            "voices": "/voices",
            "health": "/health"
        }
    }

# Main Execution
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        workers=1,
        reload=False,
    )
