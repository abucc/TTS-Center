from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import io
import json
import logging
import os
import requests
import soundfile as sf
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ChatterboxTTS Service",
    description="Text-to-Speech using ChatterboxTTS API",
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

# Pydantic models
class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "Brian"
    speed: Optional[float] = 1.0
    pitch: Optional[float] = 1.0
    format: Optional[str] = "wav"

class VoiceInfo(BaseModel):
    name: str
    gender: str
    locale: str
    engine: str
    description: str

# Available voices (basic Streamlabs voices for ChatterboxTTS compatibility)
AVAILABLE_VOICES = [
    VoiceInfo(name="Brian", gender="male", locale="en-US", engine="chatterbox", description="Brian voice"),
    VoiceInfo(name="Emma", gender="female", locale="en-US", engine="chatterbox", description="Emma voice"),
    VoiceInfo(name="Russell", gender="male", locale="en-AU", engine="chatterbox", description="Russell Australian voice"),
    VoiceInfo(name="Joey", gender="male", locale="en-US", engine="chatterbox", description="Joey voice"),
    VoiceInfo(name="Matthew", gender="male", locale="en-US", engine="chatterbox", description="Matthew voice"),
    VoiceInfo(name="Joanna", gender="female", locale="en-US", engine="chatterbox", description="Joanna voice"),
    VoiceInfo(name="Kimberly", gender="female", locale="en-US", engine="chatterbox", description="Kimberly voice"),
    VoiceInfo(name="Amy", gender="female", locale="en-GB", engine="chatterbox", description="Amy British voice"),
    VoiceInfo(name="Geraint", gender="male", locale="en-GB", engine="chatterbox", description="Geraint Welsh voice"),
    VoiceInfo(name="Nicole", gender="female", locale="en-AU", engine="chatterbox", description="Nicole Australian voice"),
]

# ChatterboxTTS API configuration
CHATTERBOX_API_URL = "https://lazypy.ro/tts/request_tts.php"

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "chatterbox-tts"
    }

@app.get("/voices", response_model=List[VoiceInfo])
async def get_voices():
    return AVAILABLE_VOICES

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    try:
        # Prepare request for ChatterboxTTS API
        payload = {
            "text": request.text,
            "voice": request.voice,
            "service": "Polly"  # ChatterboxTTS uses Polly backend
        }
        
        # Make request to ChatterboxTTS API
        response = requests.post(
            CHATTERBOX_API_URL,
            data=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"ChatterboxTTS API error: {response.status_code}")
            raise HTTPException(
                status_code=500,
                detail=f"ChatterboxTTS API error: {response.status_code}"
            )
        
        # Parse response
        result = response.json()
        
        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            logger.error(f"ChatterboxTTS generation failed: {error_msg}")
            raise HTTPException(status_code=500, detail=f"TTS generation failed: {error_msg}")
        
        # Get audio URL
        audio_url = result.get("audio_url")
        if not audio_url:
            raise HTTPException(status_code=500, detail="No audio URL in response")
        
        # Download audio file
        audio_response = requests.get(audio_url, timeout=30)
        if audio_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to download audio")
        
        # Apply speed adjustment if needed (basic implementation)
        audio_data = audio_response.content
        
        if request.speed != 1.0:
            # For more advanced speed adjustment, we'd need audio processing
            # This is a placeholder - in practice, you'd use librosa or similar
            logger.warning("Speed adjustment not implemented for ChatterboxTTS")
        
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename=speech.wav"
            }
        )
        
    except requests.RequestException as e:
        logger.error(f"Request error: {e}")
        raise HTTPException(status_code=503, detail="ChatterboxTTS service unavailable")
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")

@app.get("/")
async def root():
    return {
        "service": "ChatterboxTTS",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": {
            "tts": "/tts",
            "voices": "/voices",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
