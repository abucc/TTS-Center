from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import httpx
import asyncio
import os
import json
import logging
from datetime import datetime
import redis
import hashlib
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Awesome TTS",
    description="Multi-provider TTS API Gateway with Advanced Features",
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

# Redis client for caching (optional)
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"
REDIS_URL = os.getenv("REDIS_URL")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "1"))  # Use DB 1 to avoid conflicts
REDIS_KEY_PREFIX = os.getenv("REDIS_KEY_PREFIX", "tts_")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # Get the API key from environment

if REDIS_ENABLED:
    try:
        # Support both Redis URL and individual parameters
        if REDIS_URL:
            # Use Redis URL (for Coolify)
            redis_client = redis.from_url(REDIS_URL, decode_responses=False)
            logger.info(f"Redis connection via URL: {REDIS_URL[:20]}...")
        else:
            # Use individual parameters
            redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=False
            )
            logger.info(f"Redis connection at {REDIS_HOST}:{REDIS_PORT} DB:{REDIS_DB}")
        
        redis_client.ping()
        REDIS_AVAILABLE = True
        logger.info(f"Redis connected successfully with prefix: '{REDIS_KEY_PREFIX}'")
    except Exception as e:
        REDIS_AVAILABLE = False
        logger.warning(f"Redis connection failed: {e}. Caching disabled.")
else:
    REDIS_AVAILABLE = False
    logger.info("Redis caching disabled via environment variable")

# Service URLs with correct default ports
SERVICES = {
    "kokoro": os.getenv("KOKORO_URL", "http://kokoro-onnx:9002"),
    "chatterbox": os.getenv("CHATTERBOX_URL", "http://chatterbox-tts:9001"),
    "openai-edge-tts": os.getenv("OPENAI_EDGE_TTS_URL", "http://openai-edge-tts:5050")
}

# Pydantic models
class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    provider: str = "kokoro"  # kokoro, chatterbox, openai-edge-tts
    speed: Optional[float] = 1.0
    pitch: Optional[float] = 1.0
    format: Optional[str] = "wav"
    cache: Optional[bool] = True

class ServiceStatus(BaseModel):
    service: str
    status: str
    latency: Optional[float] = None
    error: Optional[str] = None

class TTSResponse(BaseModel):
    success: bool
    provider: str
    duration: Optional[float] = None
    cached: Optional[bool] = False
    audio_url: Optional[str] = None
    error: Optional[str] = None

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Debug endpoint for troubleshooting
@app.get("/debug")
async def debug_info():
    """Comprehensive debug information for troubleshooting"""
    debug_info = {
        "timestamp": datetime.now().isoformat(),
        "services": {},
        "redis": {"available": REDIS_AVAILABLE},
        "environment": {
            "service_urls": SERVICES
        }
    }
    
    # Test each service
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, service_url in SERVICES.items():
            try:
                start_time = asyncio.get_event_loop().time()
                health_response = await client.get(f"{service_url}/health")
                latency = (asyncio.get_event_loop().time() - start_time) * 1000
                
                service_info = {
                    "url": service_url,
                    "health_status": health_response.status_code,
                    "latency_ms": round(latency, 2),
                    "response": None,
                    "voices_available": False,
                    "voices_count": 0
                }
                
                if health_response.status_code == 200:
                    try:
                        service_info["response"] = health_response.json()
                    except:
                        service_info["response"] = health_response.text[:200]
                    
                    # Try to get voices
                    try:
                        if service_name == "openai-edge-tts":
                            headers = {"Authorization": "Bearer your_api_key_here"}
                            voices_response = await client.get(f"{service_url}/voices", headers=headers)
                        else:
                            voices_response = await client.get(f"{service_url}/voices")
                        
                        if voices_response.status_code == 200:
                            voices_data = voices_response.json()
                            service_info["voices_available"] = True
                            if isinstance(voices_data, list):
                                service_info["voices_count"] = len(voices_data)
                            elif isinstance(voices_data, dict) and "voices" in voices_data:
                                service_info["voices_count"] = len(voices_data["voices"])
                    except Exception as e:
                        service_info["voices_error"] = str(e)
                
                debug_info["services"][service_name] = service_info
                
            except Exception as e:
                debug_info["services"][service_name] = {
                    "url": service_url,
                    "error": str(e),
                    "health_status": "unreachable"
                }
    
    # Test Redis if available
    if REDIS_AVAILABLE:
        try:
            redis_client.ping()
            debug_info["redis"]["status"] = "connected"
            debug_info["redis"]["info"] = redis_client.info("memory")
        except Exception as e:
            debug_info["redis"]["status"] = "error"
            debug_info["redis"]["error"] = str(e)
    
    return debug_info

# Service status check
@app.get("/status", response_model=List[ServiceStatus])
async def check_services_status():
    logger.info("Received request to check services status")
    statuses = []
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, service_url in SERVICES.items():
            try:
                start_time = asyncio.get_event_loop().time()
                response = await client.get(f"{service_url}/health")
                latency = (asyncio.get_event_loop().time() - start_time) * 1000
                
                if response.status_code == 200:
                    logger.info(f"Service {service_name} is healthy with latency {round(latency, 2)}ms")
                    statuses.append(ServiceStatus(
                        service=service_name,
                        status="healthy",
                        latency=round(latency, 2)
                    ))
                else:
                    logger.warning(f"Service {service_name} is unhealthy - status code: {response.status_code}")
                    statuses.append(ServiceStatus(
                        service=service_name,
                        status="unhealthy",
                        error=f"HTTP {response.status_code}"
                    ))
            except Exception as e:
                statuses.append(ServiceStatus(
                    service=service_name,
                    status="error",
                    error=str(e)
                ))
    
    return statuses

# Get available voices for a provider
@app.get("/voices/{provider}")
async def get_voices(provider: str):
    logger.info(f"Received voice request for provider: {provider}")
    if provider not in SERVICES:
        logger.error(f"Invalid provider requested: {provider}")
        raise HTTPException(status_code=400, detail="Invalid provider")
    
    logger.info(f"Using service URL: {SERVICES[provider]}")
    
    headers = {}
    if provider == "openai-edge-tts":
        if not OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY is not set in environment for tts-gateway.")
            raise HTTPException(status_code=500, detail="OpenAI API key not configured for gateway")
        headers["Authorization"] = f"Bearer {OPENAI_API_KEY}"
            
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            logger.info(f"Making request to {SERVICES[provider]}/voices")
            if provider == "openai-edge-tts":
                # Fetch ALL voices from the openai-edge-tts service (not just English)
                response = await client.get(f"{SERVICES[provider]}/voices/all", headers=headers) # Pass headers
                response.raise_for_status() # Raise an exception for bad status codes
                voices_data = response.json()
                actual_voices_list = voices_data.get("voices", []) if isinstance(voices_data, dict) else voices_data
                return [{"name": voice.get("name"), "display_name": voice.get("name")} for voice in actual_voices_list if voice.get("name")]
            
            elif provider == "chatterbox":
                response = await client.get(f"{SERVICES[provider]}/voices")
                response.raise_for_status() # Raise an exception for bad status codes
                result = response.json()
                # Add debug logging
                logger.info(f"Raw response from chatterbox: {result}")
                # Chatterbox now returns: List[Dict{"name": "filename.wav", "display_name": "Filename"}]
                if isinstance(result, list):
                    voice_list = [{"name": voice.get("name"), "display_name": voice.get("display_name", voice.get("name", "").split('.')[0])} for voice in result if voice.get("name")]
                    logger.info(f"Processed voice list for chatterbox: {voice_list}")
                    return voice_list
                logger.warning(f"Unexpected voice format from chatterbox: {result}")
                return []
            
            elif provider == "kokoro":
                response = await client.get(f"{SERVICES[provider]}/voices")
                
                if response.status_code != 200:
                    logger.error(f"Kokoro service returned status {response.status_code}")
                    raise HTTPException(status_code=response.status_code, detail="Kokoro service error")
                
                result = response.json()
                # Kokoro returns list of VoiceInfo objects
                if isinstance(result, list):
                    return [{"name": v.get("name", v), "display_name": v.get("name", v)}
                           for v in result]
                return []
            
            else:
                response = await client.get(f"{SERVICES[provider]}/voices")
                
                if response.status_code != 200:
                    logger.error(f"{provider} service returned status {response.status_code}")
                    raise HTTPException(status_code=response.status_code, detail=f"{provider} service error")
                
                result = response.json()
                # Generic handling
                if isinstance(result, list):
                    return [{"name": v.get("name", v), "display_name": v.get("display_name", v.get("name", v))}
                           for v in result]
                return []
                
    except httpx.ConnectError as e:
        logger.error(f"Connection error to {provider} service: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Cannot connect to {provider} service")
    except httpx.TimeoutException as e:
        logger.error(f"Timeout error to {provider} service: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Timeout connecting to {provider} service")
    except Exception as e:
        logger.error(f"Error getting voices for {provider}: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

# Generate cache key
def generate_cache_key(request: TTSRequest) -> str:
    content = f"{request.provider}:{request.text}:{request.voice}:{request.speed}:{request.pitch}:{request.format}"
    key = hashlib.md5(content.encode()).hexdigest()
    return f"{REDIS_KEY_PREFIX}{key}" if REDIS_KEY_PREFIX else key

# Main TTS endpoint
@app.post("/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    if request.provider not in SERVICES:
        return TTSResponse(
            success=False,
            provider=request.provider,
            error="Invalid provider"
        )
    
    # Generate cache key
    cache_key = generate_cache_key(request)
    
    # Check cache first
    if request.cache and REDIS_AVAILABLE:
        try:
            cached_audio = redis_client.get(f"audio:{cache_key}")
            if cached_audio:
                logger.info(f"Cache hit for key: {cache_key}")
                return TTSResponse(
                    success=True,
                    provider=request.provider,
                    cached=True,
                    audio_url=f"/audio/{cache_key}"
                )
        except Exception as e:
            logger.warning(f"Cache check failed: {e}")
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Prepare request for specific provider
        provider_request = await prepare_provider_request(request)
        
        # Make request to provider with extended timeout for chatterbox
        timeout_duration = 1800.0 if request.provider == "chatterbox" else 60.0  # 30 minutes for chatterbox, 1 minute for others
        async with httpx.AsyncClient(timeout=timeout_duration) as client:
            # Different endpoints for different providers
            if request.provider == "openai-edge-tts":
                endpoint = f"{SERVICES[request.provider]}/v1/audio/speech"
                if not OPENAI_API_KEY:
                    logger.error("OPENAI_API_KEY is not set in environment for tts-gateway.")
                    return TTSResponse(
                        success=False,
                        provider=request.provider,
                        error="OpenAI API key not configured for gateway"
                    )
                headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
                response = await client.post(
                    endpoint,
                    json=provider_request,
                    headers=headers
                )
            else:
                response = await client.post(
                    f"{SERVICES[request.provider]}/tts",
                    json=provider_request
                )
            
            if response.status_code != 200:
                error_detail = f"Provider error: HTTP {response.status_code}"
                try:
                    error_body = response.text
                    if error_body:
                        error_detail += f" - {error_body}"
                except:
                    pass
                
                return TTSResponse(
                    success=False,
                    provider=request.provider,
                    error=error_detail
                )
            
            # Handle response based on content type
            content_type = response.headers.get("content-type", "").lower()
            
            if content_type.startswith("audio/") or "audio" in content_type:
                # Direct audio response
                audio_data = response.content
                
                if len(audio_data) < 100:  # Very small file, likely an error
                    return TTSResponse(
                        success=False,
                        provider=request.provider,
                        error="Generated audio file is too small, likely corrupted"
                    )
                
                # Cache the audio data
                if REDIS_AVAILABLE:
                    try:
                        redis_client.setex(f"audio:{cache_key}", 3600, audio_data)  # 1 hour cache
                        logger.info(f"Cached audio with key: {cache_key}")
                    except Exception as e:
                        logger.warning(f"Failed to cache audio: {e}")
                
                duration = (asyncio.get_event_loop().time() - start_time) * 1000
                
                return TTSResponse(
                    success=True,
                    provider=request.provider,
                    duration=round(duration, 2),
                    audio_url=f"/audio/{cache_key}"
                )
            else:
                # JSON response - try to handle it
                try:
                    result = response.json()
                    duration = (asyncio.get_event_loop().time() - start_time) * 1000
                    
                    # If the result contains audio_url, use it
                    if "audio_url" in result:
                        return TTSResponse(
                            success=True,
                            provider=request.provider,
                            duration=round(duration, 2),
                            audio_url=result["audio_url"]
                        )
                    else:
                        return TTSResponse(
                            success=False,
                            provider=request.provider,
                            error="Provider returned JSON without audio content"
                        )
                except Exception as e:
                    return TTSResponse(
                        success=False,
                        provider=request.provider,
                        error=f"Failed to parse provider response: {str(e)}"
                    )
                
    except httpx.ConnectError as e:
        logger.error(f"Connection error to {request.provider}: {str(e)}")
        return TTSResponse(
            success=False,
            provider=request.provider,
            error=f"Cannot connect to {request.provider} service"
        )
    except httpx.TimeoutException as e:
        logger.error(f"Timeout error to {request.provider}: {str(e)}")
        return TTSResponse(
            success=False,
            provider=request.provider,
            error=f"Timeout connecting to {request.provider} service"
        )
    except Exception as e:
        logger.error(f"TTS request failed: {str(e)}")
        return TTSResponse(
            success=False,
            provider=request.provider,
            error=str(e)
        )

# Prepare provider-specific request
async def prepare_provider_request(request: TTSRequest) -> dict:
    base_request = {
        "text": request.text,
        "speed": request.speed,
        "format": request.format
    }
    
    if request.provider == "kokoro":
        if request.voice:
            base_request["voice"] = request.voice
        return base_request
    
    elif request.provider == "chatterbox":
        # Chatterbox TTS works without voice parameter for default neural voice
        # Only include voice if one is specifically requested
        if request.voice:
            base_request["voice"] = request.voice
        base_request["pitch"] = request.pitch
        return base_request
    
    elif request.provider == "openai-edge-tts":
        # OpenAI Edge TTS expects different format
        openai_request = {
            "input": request.text,
            "voice": request.voice or "en-US-AvaNeural",
            "response_format": "mp3" if request.format == "mp3" else "wav",
            "speed": request.speed
        }
        return openai_request
    
    return base_request

# Serve cached audio files
@app.get("/audio/{audio_id}")
async def get_audio(audio_id: str):
    if not REDIS_AVAILABLE:
        raise HTTPException(status_code=404, detail="Audio not found - caching disabled")
    
    try:
        # Get raw binary data from Redis
        audio_data = redis_client.get(f"audio:{audio_id}")
        if not audio_data:
            logger.error(f"Audio not found in Redis for ID: {audio_id}")
            raise HTTPException(status_code=404, detail="Audio not found or expired")
        
        # With decode_responses=False, Redis should return bytes directly
        if not isinstance(audio_data, bytes):
            logger.error(f"Expected bytes, got {type(audio_data)} for audio {audio_id}")
            raise HTTPException(status_code=500, detail="Invalid audio data type from cache")
        
        if len(audio_data) < 44:  # WAV header is at least 44 bytes
            logger.error(f"Audio data too small: {len(audio_data)} bytes for {audio_id}")
            raise HTTPException(status_code=500, detail="Invalid audio data size")
        
        # Determine content type based on audio file magic bytes
        content_type = "audio/wav"
        file_extension = "wav"
        
        # Check for MP3 magic bytes
        if audio_data.startswith(b'ID3') or audio_data.startswith(b'\xff\xfb'):
            content_type = "audio/mpeg"
            file_extension = "mp3"
        # Check for WAV magic bytes
        elif audio_data.startswith(b'RIFF') and b'WAVE' in audio_data[:12]:
            content_type = "audio/wav"
            file_extension = "wav"
        # Check for OGG magic bytes
        elif audio_data.startswith(b'OggS'):
            content_type = "audio/ogg"
            file_extension = "ogg"
        else:
            logger.warning(f"Unknown audio format for {audio_id}, assuming WAV")
        
        logger.info(f"Serving audio {audio_id}: {len(audio_data)} bytes as {content_type}")
        
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={audio_id}.{file_extension}",
                "Content-Type": content_type,
                "Cache-Control": "public, max-age=3600",
                "Content-Length": str(len(audio_data)),
                "Accept-Ranges": "bytes"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving audio {audio_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error serving audio file: {str(e)}")

# Play audio directly in browser (inline, not download)
@app.get("/play/{audio_id}")
async def play_audio(audio_id: str):
    if not REDIS_AVAILABLE:
        raise HTTPException(status_code=404, detail="Audio not found - caching disabled")
    
    try:
        # Get raw binary data from Redis
        audio_data = redis_client.get(f"audio:{audio_id}")
        if not audio_data:
            logger.error(f"Audio not found in Redis for playback ID: {audio_id}")
            raise HTTPException(status_code=404, detail="Audio not found or expired")
        
        # With decode_responses=False, Redis should return bytes directly
        if not isinstance(audio_data, bytes):
            logger.error(f"Expected bytes for playback, got {type(audio_data)} for audio {audio_id}")
            raise HTTPException(status_code=500, detail="Invalid audio data type from cache")
        
        # Determine content type
        content_type = "audio/wav"
        if audio_data.startswith(b'ID3') or audio_data.startswith(b'\xff\xfb'):
            content_type = "audio/mpeg"
        elif audio_data.startswith(b'RIFF') and b'WAVE' in audio_data[:12]:
            content_type = "audio/wav"
        elif audio_data.startswith(b'OggS'):
            content_type = "audio/ogg"
        
        logger.info(f"Playing audio {audio_id}: {len(audio_data)} bytes as {content_type}")
        
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type=content_type,
            headers={
                "Content-Disposition": "inline",
                "Content-Type": content_type,
                "Cache-Control": "public, max-age=3600",
                "Accept-Ranges": "bytes",
                "Content-Length": str(len(audio_data))
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error playing audio {audio_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error playing audio file: {str(e)}")

# Health check for root path (removing web interface to avoid conflicts)
@app.get("/")
async def root():
    return {"message": "Awesome TTS API", "version": "1.0.0", "status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 9000))
    uvicorn.run(app, host="0.0.0.0", port=port)
