from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import io
import json
import logging
import os
import soundfile as sf
import numpy as np
from kokoro_onnx import Kokoro
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Kokoro ONNX TTS Service",
    description="High-quality Text-to-Speech using Kokoro ONNX",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global TTS model
tts_model = None

# Pydantic models
class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "af_heart"
    speed: Optional[float] = 1.0
    pitch: Optional[float] = 1.0
    format: Optional[str] = "wav"

class VoiceInfo(BaseModel):
    name: str
    gender: str
    locale: str
    engine: str
    description: str
    grade: Optional[str] = None

class TTSResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    audio_length: Optional[float] = None

# Load voices configuration
def load_voices() -> List[VoiceInfo]:
    voices_path = "/app/voices/kokoro_voices.json"
    if not os.path.exists(voices_path):
        # Fallback to a basic voice list
        return [
            VoiceInfo(
                name="af_heart",
                gender="female",
                locale="en-US",
                engine="kokoro",
                description="American Female - Heart (Grade A)",
                grade="A"
            ),
            VoiceInfo(
                name="am_michael",
                gender="male",
                locale="en-US",
                engine="kokoro",
                description="American Male - Michael (Grade C+)",
                grade="C+"
            )
        ]
    
    try:
        with open(voices_path, 'r') as f:
            voices_data = json.load(f)
        return [VoiceInfo(**voice) for voice in voices_data]
    except Exception as e:
        logger.error(f"Error loading voices: {e}")
        return []

# Initialize TTS model
async def initialize_model():
    global tts_model
    try:
        model_path = os.getenv("MODEL_PATH", "/app/models")
        
        # Check if model files exist
        model_file = os.path.join(model_path, "kokoro-v1.0.onnx")
        voices_file = os.path.join(model_path, "voices-v1.0.bin")
        
        if not os.path.exists(model_file) or not os.path.exists(voices_file):
            logger.warning("Model files not found, downloading...")
            # Download will be handled by download_models.py
            
        tts_model = Kokoro(
            model_path=model_file,
            voices_path=voices_file
        )
        logger.info("Kokoro TTS model initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize TTS model: {e}")
        tts_model = None

@app.on_event("startup")
async def startup_event():
    await initialize_model()

@app.get("/health")
async def health_check():
    status = "healthy" if tts_model is not None else "unhealthy"
    return {
        "status": status,
        "service": "kokoro-onnx",
        "model_loaded": tts_model is not None
    }

@app.get("/voices", response_model=List[VoiceInfo])
async def get_voices():
    return load_voices()

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    if tts_model is None:
        raise HTTPException(status_code=503, detail="TTS model not initialized")
    
    try:
        # Generate speech
        audio = tts_model.create(
            text=request.text,
            voice=request.voice,
            speed=request.speed
        )
        
        # Convert to wav format
        buffer = io.BytesIO()
        sf.write(buffer, audio, 22050, format='WAV')
        buffer.seek(0)
        
        # Calculate audio length
        audio_length = len(audio) / 22050  # Sample rate is 22050
        
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

@app.get("/")
async def root():
    return {
        "service": "Kokoro ONNX TTS",
        "version": "1.0.0",
        "status": "healthy" if tts_model is not None else "initializing",
        "endpoints": {
            "tts": "/tts",
            "voices": "/voices",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
