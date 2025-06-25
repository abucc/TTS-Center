from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Depends
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import httpx
import asyncio
import os
import json
import logging
from datetime import datetime, timedelta, timezone
import redis
import hashlib
import io
import jwt
import bcrypt
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Import our storage module
from storage import StorageManager

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

# Use single API key for all services
API_KEY = os.getenv("API_KEY")

# Authentication configuration
SECRET_KEY = os.getenv("SESSION_SECRET", "your-secret-key-change-this")
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD")  # Plain text password (optional)
AUTH_PASSWORD_HASH = os.getenv("AUTH_PASSWORD_HASH", "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBQ72SJWJzX4gS")  # default: "password"

# Security
security = HTTPBearer()

# Initialize Redis and Storage Manager
redis_client = None
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

# Initialize the storage manager with Redis client
storage_manager = StorageManager(redis_client if REDIS_AVAILABLE else None)

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

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: Optional[str] = None

# Authentication functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def authenticate_user(username: str, password: str) -> bool:
    """Authenticate user with either plain text password or hash."""
    # Check username first
    if username != AUTH_USERNAME:
        return False
    
    # If plain text password is set, use it directly
    if AUTH_PASSWORD:
        return password == AUTH_PASSWORD
    
    # Otherwise, use the password hash
    return verify_password(password, AUTH_PASSWORD_HASH)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(tz=timezone.utc) + expires_delta
    else:
        expire = datetime.now(tz=timezone.utc) + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token from Authorization header."""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# API key check for endpoints (used for /tts)
def optional_api_key_check(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Optional API key check that allows requests without Authorization header if REQUIRE_API_KEY is false."""
    REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "false").lower() == "true"
    API_KEY = os.getenv("API_KEY")
    if not REQUIRE_API_KEY:
        return True  # API key not required
    if not credentials:
        raise HTTPException(status_code=401, detail="API key required")
    if credentials.credentials == API_KEY:
        return True
    raise HTTPException(status_code=401, detail="Invalid API key")

# Authentication endpoints
@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    if authenticate_user(request.username, request.password):
        access_token = create_access_token(data={"sub": request.username})
        return LoginResponse(success=True, token=access_token)
    else:
        return LoginResponse(success=False, message="Invalid username or password")

@app.get("/auth/verify")
async def verify_auth(username: str = Depends(verify_token)):
    """Verify JWT token."""
    return {"valid": True, "username": username}

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
        "redis": {
            "available": REDIS_AVAILABLE,
            "url": REDIS_URL or f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
            "key_prefix": REDIS_KEY_PREFIX
        },
        "environment": {
            "service_urls": SERVICES,
            "api_key_configured": bool(API_KEY)
        }
    }
    
    # Test each service with detailed error reporting
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, service_url in SERVICES.items():
            service_info = {
                "url": service_url,
                "health_status": None,
                "latency_ms": None,
                "error": None,
                "response": None,
                "voices_available": False,
                "voices_count": 0
            }
            
            try:
                # Health check
                start_time = asyncio.get_event_loop().time()
                try:
                    health_response = await client.get(f"{service_url}/health")
                    service_info["health_status"] = health_response.status_code
                    service_info["latency_ms"] = round((asyncio.get_event_loop().time() - start_time) * 1000, 2)
                    
                    if health_response.status_code == 200:
                        try:
                            service_info["response"] = health_response.json()
                        except:
                            service_info["response"] = health_response.text[:200]
                    else:
                        service_info["error"] = f"HTTP {health_response.status_code}: {health_response.text[:200]}"
                except Exception as e:
                    service_info["error"] = f"Health check failed: {str(e)}"
                    service_info["health_status"] = "unreachable"
                
                # Voice check (only if health check passed)
                if service_info["health_status"] == 200:
                    try:
                        headers = {}
                        if service_name == "openai-edge-tts":
                            if not API_KEY:
                                service_info["voices_error"] = "API_KEY not configured"
                            else:
                                headers["Authorization"] = f"Bearer {API_KEY}"
                        
                        voices_response = await client.get(
                            f"{service_url}/voices",
                            headers=headers,
                            timeout=10.0
                        )
                        
                        if voices_response.status_code == 200:
                            voices_data = voices_response.json()
                            service_info["voices_available"] = True
                            if isinstance(voices_data, list):
                                service_info["voices_count"] = len(voices_data)
                            elif isinstance(voices_data, dict) and "voices" in voices_data:
                                service_info["voices_count"] = len(voices_data["voices"])
                        else:
                            service_info["voices_error"] = f"HTTP {voices_response.status_code}: {voices_response.text[:200]}"
                    except Exception as e:
                        service_info["voices_error"] = f"Voices check failed: {str(e)}"
                
            except Exception as e:
                service_info["error"] = f"Service check failed: {str(e)}"
            
            debug_info["services"][service_name] = service_info
    
    # Detailed Redis check
    if REDIS_AVAILABLE:
        try:
            redis_client.ping()
            debug_info["redis"]["status"] = "connected"
            debug_info["redis"]["info"] = {
                "version": redis_client.info("server").get("redis_version"),
                "memory_used": redis_client.info("memory").get("used_memory_human"),
                "keys": redis_client.dbsize()
            }
        except Exception as e:
            debug_info["redis"]["status"] = "error"
            debug_info["redis"]["error"] = str(e)
            debug_info["redis"]["info"] = None
    
    # Add debug logging
    logger.info(f"Debug endpoint called - returning: {debug_info}")
    
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
        if not API_KEY:
            logger.error("API_KEY is not set in environment for tts-gateway.")
            raise HTTPException(status_code=500, detail="API key not configured for gateway")
        headers["Authorization"] = f"Bearer {API_KEY}"
            
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
async def text_to_speech(request: TTSRequest, api_auth: bool = Depends(optional_api_key_check)):
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
            cached_audio = storage_manager.get_audio(cache_key)
            if cached_audio:
                logger.info(f"Cache hit for key: {cache_key}")
                audio_url = storage_manager.get_audio_url(cache_key, request.format or "wav")
                return TTSResponse(
                    success=True,
                    provider=request.provider,
                    cached=True,
                    audio_url=audio_url
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
                if not API_KEY:
                    logger.error("API_KEY is not set in environment for tts-gateway.")
                    return TTSResponse(
                        success=False,
                        provider=request.provider,
                        error="API key not configured for gateway"
                    )
                headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
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
                
                # Store the audio data using the storage manager
                audio_format = request.format or "wav"
                success, audio_url = storage_manager.store_audio(audio_data, cache_key, audio_format)
                
                if not success:
                    logger.warning(f"Failed to store audio with key: {cache_key}")
                
                # Detect the actual format to inform the client
                actual_format = storage_manager.detect_audio_format(audio_data)
                
                duration = (asyncio.get_event_loop().time() - start_time) * 1000
                
                response_data = TTSResponse(
                    success=True,
                    provider=request.provider,
                    duration=round(duration, 2),
                    audio_url=audio_url
                )
                
                # Add actual format information if different from requested
                if actual_format != audio_format:
                    logger.info(f"Format conversion status: Requested {audio_format}, got {actual_format}")
                
                return response_data
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
    if not REDIS_AVAILABLE and not storage_manager.s3_enabled:
        raise HTTPException(status_code=404, detail="Audio not found - storage unavailable")
    
    try:
        # Get raw binary data from Redis
        audio_data = storage_manager.get_audio(audio_id)
        if not audio_data:
            logger.error(f"Audio not found in storage for ID: {audio_id}")
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
    if not REDIS_AVAILABLE and not storage_manager.s3_enabled:
        raise HTTPException(status_code=404, detail="Audio not found - storage unavailable")
    
    try:
        # Get raw binary data from storage
        audio_data = storage_manager.get_audio(audio_id)
        if not audio_data:
            logger.error(f"Audio not found in storage for playback ID: {audio_id}")
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
