from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import io
import json
import logging
import os
import edge_tts
import asyncio
import tempfile
import aiofiles

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OpenAI Edge TTS Service",
    description="Text-to-Speech using OpenAI-style API with Edge TTS backend",
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
    voice: Optional[str] = "alloy"
    speed: Optional[float] = 1.0
    pitch: Optional[float] = 1.0
    format: Optional[str] = "wav"
    rate: Optional[str] = None  # Edge TTS rate parameter

class VoiceInfo(BaseModel):
    name: str
    gender: str
    locale: str
    engine: str

# OpenAI-style voice mapping to Edge TTS voices
VOICE_MAPPING = {
    "alloy": "en-US-AndrewNeural",
    "echo": "en-US-BrianNeural", 
    "fable": "en-GB-LibbyNeural",
    "onyx": "en-US-EricNeural",
    "nova": "en-US-EmmaNeural",
    "shimmer": "en-US-AvaNeural"
}

# Load voices from configuration
def load_voices() -> List[VoiceInfo]:
    voices_path = "/app/voices/openai_edge_tts_voices.json"
    if not os.path.exists(voices_path):
        # Fallback to basic OpenAI-style voices
        return [
            VoiceInfo(name="alloy", gender="female", locale="en-US", engine="openai-edge-tts"),
            VoiceInfo(name="echo", gender="male", locale="en-US", engine="openai-edge-tts"),
            VoiceInfo(name="fable", gender="female", locale="en-GB", engine="openai-edge-tts"),
            VoiceInfo(name="onyx", gender="male", locale="en-US", engine="openai-edge-tts"),
            VoiceInfo(name="nova", gender="male", locale="en-US", engine="openai-edge-tts"),
            VoiceInfo(name="shimmer", gender="female", locale="en-US", engine="openai-edge-tts"),
        ]
    
    try:
        with open(voices_path, 'r') as f:
            voices_data = json.load(f)
        return [VoiceInfo(**voice) for voice in voices_data]
    except Exception as e:
        logger.error(f"Error loading voices: {e}")
        return []

def get_edge_voice(openai_voice: str) -> str:
    """Map OpenAI voice name to Edge TTS voice"""
    return VOICE_MAPPING.get(openai_voice, "en-US-AriaNeural")

def calculate_rate(speed: float) -> str:
    """Convert speed multiplier to Edge TTS rate format"""
    if speed <= 0.5:
        return "-50%"
    elif speed <= 0.75:
        return "-25%"
    elif speed <= 1.25:
        return "+0%"
    elif speed <= 1.5:
        return "+25%"
    elif speed <= 2.0:
        return "+50%"
    else:
        return "+100%"

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "openai-edge-tts"
    }

@app.get("/voices", response_model=List[VoiceInfo])
async def get_voices():
    return load_voices()

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    try:
        # Map OpenAI voice to Edge TTS voice
        edge_voice = get_edge_voice(request.voice)
        
        # Calculate rate from speed
        rate = request.rate or calculate_rate(request.speed)
        
        # Create TTS communication
        communicate = edge_tts.Communicate(
            text=request.text,
            voice=edge_voice,
            rate=rate
        )
        
        # Generate audio to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            await communicate.save(tmp_path)
            
            # Read the generated audio file
            async with aiofiles.open(tmp_path, 'rb') as audio_file:
                audio_data = await audio_file.read()
            
            return StreamingResponse(
                io.BytesIO(audio_data),
                media_type="audio/wav",
                headers={
                    "Content-Disposition": f"attachment; filename=speech.wav"
                }
            )
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")

@app.post("/v1/audio/speech")
async def openai_compatible_tts(request: TTSRequest):
    """OpenAI-compatible endpoint"""
    return await text_to_speech(request)

@app.get("/v1/audio/speech/voices")
async def openai_compatible_voices():
    """OpenAI-compatible voices endpoint"""
    voices = load_voices()
    return {
        "data": [
            {
                "id": voice.name,
                "object": "voice",
                "name": voice.name,
                "preview_url": None
            }
            for voice in voices
            if voice.name in VOICE_MAPPING
        ]
    }

@app.get("/")
async def root():
    return {
        "service": "OpenAI Edge TTS",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": {
            "tts": "/tts",
            "openai_tts": "/v1/audio/speech",
            "voices": "/voices",
            "openai_voices": "/v1/audio/speech/voices",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
