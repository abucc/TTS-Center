from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import io
import json
import logging
import os
import soundfile as sf
import numpy as np
from kokoro_onnx import Kokoro
from kokoro_onnx.tokenizer import Tokenizer
import asyncio
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global TTS model and tokenizer
tts_model = None
tokenizer = None

# Pydantic models
class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "af_heart"
    speed: Optional[float] = 1.0
    pitch: Optional[float] = 1.0
    format: Optional[str] = "wav"
    language: Optional[str] = "en-us"

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

def ensure_kokoro_files():
    """Download kokoro model files if they don't exist"""
    import wget
    
    model_path = os.getenv("MODEL_PATH", "/app/models")
    os.makedirs(model_path, exist_ok=True)
    
    model_file = os.path.join(model_path, "kokoro-v1.0.onnx")
    voices_file = os.path.join(model_path, "voices-v1.0.bin")
    
    if not os.path.exists(model_file):
        logger.info("Downloading kokoro-v1.0.onnx...")
        wget.download(
            "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
            model_file
        )
        logger.info("Model file downloaded successfully")
        
    if not os.path.exists(voices_file):
        logger.info("Downloading voices-v1.0.bin...")
        wget.download(
            "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
            voices_file
        )
        logger.info("Voices file downloaded successfully")
        
    return model_file, voices_file

# Initialize TTS model
async def initialize_model():
    global tts_model, tokenizer
    try:
        logger.info("Initializing Kokoro TTS model...")
        model_file, voices_file = ensure_kokoro_files()
        
        tts_model = Kokoro(model_file, voices_file)
        tokenizer = Tokenizer()
        logger.info("Kokoro TTS model and tokenizer initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize TTS model: {e}")
        tts_model = None
        tokenizer = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await initialize_model()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Kokoro ONNX TTS Service",
    description="High-quality Text-to-Speech using Kokoro ONNX",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    if tts_model is None:
        raise HTTPException(status_code=503, detail="TTS model not initialized")
    
    try:
        voice_names = tts_model.get_voices()
        voices = []
        for voice in voice_names:
            # Extract basic info from voice name
            gender = "female" if "f_" in voice or voice.startswith("af_") else "male"
            locale = "en-US"  # Default locale for Kokoro voices
            
            voices.append(VoiceInfo(
                name=voice,
                gender=gender,
                locale=locale,
                engine="kokoro",
                description=f"Kokoro voice: {voice}",
                grade="A"
            ))
        
        return voices
    except Exception as e:
        logger.error(f"Error getting voices: {e}")
        raise HTTPException(status_code=500, detail="Failed to get available voices")

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    if tts_model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="TTS model not initialized")
    
    try:
        # Phonemize the text
        phonemes = tokenizer.phonemize(request.text, lang=request.language)
        
        # Generate speech
        samples, sample_rate = tts_model.create(
            phonemes,
            voice=request.voice,
            speed=request.speed,
            is_phonemes=True
        )
        
        # Convert to wav format
        buffer = io.BytesIO()
        sf.write(buffer, samples, sample_rate, format='WAV')
        buffer.seek(0)
        
        # Calculate audio length
        audio_length = len(samples) / sample_rate
        
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
