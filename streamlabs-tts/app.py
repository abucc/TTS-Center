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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Streamlabs TTS Service",
    description="Text-to-Speech using Streamlabs Polly API",
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

# Load voices from configuration
def load_voices() -> List[VoiceInfo]:
    voices_path = "/app/voices/streamlabs_voices.json"
    if not os.path.exists(voices_path):
        # Fallback to basic voice list
        return [
            VoiceInfo(name="Brian", gender="male", locale="en-US", engine="streamlabs-polly", description="Brian voice"),
            VoiceInfo(name="Emma", gender="female", locale="en-US", engine="streamlabs-polly", description="Emma voice"),
            VoiceInfo(name="Russell", gender="male", locale="en-AU", engine="streamlabs-polly", description="Russell Australian voice"),
            VoiceInfo(name="Joey", gender="male", locale="en-US", engine="streamlabs-polly", description="Joey voice"),
            VoiceInfo(name="Matthew", gender="male", locale="en-US", engine="streamlabs-polly", description="Matthew voice"),
            VoiceInfo(name="Joanna", gender="female", locale="en-US", engine="streamlabs-polly", description="Joanna voice"),
            VoiceInfo(name="Kimberly", gender="female", locale="en-US", engine="streamlabs-polly", description="Kimberly voice"),
            VoiceInfo(name="Amy", gender="female", locale="en-GB", engine="streamlabs-polly", description="Amy British voice"),
            VoiceInfo(name="Geraint", gender="male", locale="en-GB", engine="streamlabs-polly", description="Geraint Welsh voice"),
            VoiceInfo(name="Nicole", gender="female", locale="en-AU", engine="streamlabs-polly", description="Nicole Australian voice"),
        ]
    
    try:
        with open(voices_path, 'r') as f:
            voices_data = json.load(f)
        return [VoiceInfo(**voice) for voice in voices_data]
    except Exception as e:
        logger.error(f"Error loading voices: {e}")
        return []

# Streamlabs TTS API configuration
STREAMLABS_API_URL = "https://streamlabs.com/polly/speak"

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "streamlabs-tts"
    }

@app.get("/voices", response_model=List[VoiceInfo])
async def get_voices():
    return load_voices()

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    try:
        # Prepare request for Streamlabs API
        payload = {
            "voice": request.voice,
            "text": request.text,
            "service": "polly"
        }
        
        # Make request to Streamlabs TTS API
        response = requests.post(
            STREAMLABS_API_URL,
            data=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Streamlabs API error: {response.status_code}")
            raise HTTPException(
                status_code=500,
                detail=f"Streamlabs API error: {response.status_code}"
            )
        
        # Check if response is JSON (error) or audio
        content_type = response.headers.get("content-type", "")
        
        if "application/json" in content_type:
            # Error response
            try:
                error_data = response.json()
                error_msg = error_data.get("error", "Unknown error")
                logger.error(f"Streamlabs TTS generation failed: {error_msg}")
                raise HTTPException(status_code=500, detail=f"TTS generation failed: {error_msg}")
            except json.JSONDecodeError:
                raise HTTPException(status_code=500, detail="Invalid response from Streamlabs API")
        
        # Successful audio response
        audio_data = response.content
        
        if not audio_data:
            raise HTTPException(status_code=500, detail="Empty audio response")
        
        # Apply basic speed adjustment (placeholder)
        if request.speed != 1.0:
            # For more advanced speed adjustment, we'd need audio processing
            # This is a placeholder - in practice, you'd use librosa or similar
            logger.warning("Speed adjustment not implemented for Streamlabs TTS")
        
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"attachment; filename=speech.wav"
            }
        )
        
    except requests.RequestException as e:
        logger.error(f"Request error: {e}")
        raise HTTPException(status_code=503, detail="Streamlabs TTS service unavailable")
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")

@app.get("/")
async def root():
    return {
        "service": "Streamlabs TTS",
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
