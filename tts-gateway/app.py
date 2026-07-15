from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import os
import re
import shlex
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import bcrypt
import httpx
import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-hub")
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")

app = FastAPI(
    title="Voice Hub",
    description="Local-first TTS gateway for Qwen3-TTS with Aliyun fallback.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("SESSION_SECRET", "change-this-session-secret")
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD")
AUTH_PASSWORD_HASH = os.getenv(
    "AUTH_PASSWORD_HASH",
    "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBQ72SJWJzX4gS",
)
REQUIRE_API_KEY = os.getenv("REQUIRE_API_KEY", "false").lower() == "true"
API_KEY = os.getenv("API_KEY")

security = HTTPBearer(auto_error=False)

REDIS_KEY_PREFIX = os.getenv("REDIS_KEY_PREFIX", "voice_hub_")
memory_audio: Dict[str, bytes] = {}
generated_history: List[Dict[str, Any]] = []


class Voice(BaseModel):
    name: str
    display_name: str


class ProviderInfo(BaseModel):
    id: str
    name: str
    kind: str
    description: str
    default_voice: Optional[str] = None
    format: str = "wav"
    chain: List[str] = []


class TTSRequest(BaseModel):
    text: str
    provider: str = "local-first"
    voice: Optional[str] = None
    speed: float = 1.0
    pitch: float = 1.0
    format: str = "wav"
    cache: bool = True


class TTSResponse(BaseModel):
    success: bool
    provider: str
    actual_provider: Optional[str] = None
    duration: Optional[float] = None
    generation_duration: Optional[float] = None
    cached: bool = False
    audio_url: Optional[str] = None
    error: Optional[str] = None
    history_id: Optional[str] = None


class ServiceStatus(BaseModel):
    service: str
    status: str
    latency: Optional[float] = None
    error: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: Optional[str] = None


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    kind: str
    description: str
    default_voice: str = ""
    output_format: str = "wav"
    url: str = ""
    command: str = ""
    chain: tuple[str, ...] = ()
    timeout: float = 60.0


QWEN_URL = os.getenv("QWEN_URL", "http://host.docker.internal:7861").rstrip("/")
CONFIG_DIR = Path(os.getenv("VOICE_HUB_CONFIG_DIR", "/app/config"))
FALLBACK_CHAINS_PATH = CONFIG_DIR / "fallback-chains.json"
VOICE_STYLE_PATH = Path(os.getenv("VOICE_STYLE_PATH", "/opt/data/voice_styles.json"))
TARGET_TTS_CHARS = int(os.getenv("VOICE_HUB_TARGET_TTS_CHARS", "80"))
MAX_TTS_CHARS = int(os.getenv("VOICE_HUB_MAX_TTS_CHARS", "120"))
ALIYUN_COMMAND = os.getenv(
    "ALIYUN_TTS_COMMAND",
    "/usr/local/bin/python "
    "/opt/data/skills/aliyun-tts/scripts/aliyun_tts.py "
    "{text} {output_path} --voice {voice} --format {format}",
)
ALIYUN_DEFAULT_VOICE = os.getenv("ALIYUN_DEFAULT_VOICE", "zhimi_emo")
DEFAULT_VOICE_STYLES: Dict[str, Any] = {
    "\u6817\u5b50": {
        "enabled": True,
        "max_sentence_chars": 24,
        "prefix": "",
        "common_words": ["\u55ef\u5450", "\u563f\u563f", "\u54ce\u5440", "\u54e5\u54e5"],
        "forbidden": ["\u4f5c\u4e3aAI", "\u4f5c\u4e3a\u4e00\u4e2aAI", "\u6211\u662fAI", "\u6211\u65e0\u6cd5"],
        "replacements": {
            "\u7528\u6237": "\u54e5\u54e5",
            "\u597d\u7684": "\u597d\u561b",
            "\u660e\u767d\u4e86": "\u77e5\u9053\u5566",
            "\u6ca1\u95ee\u9898": "\u6ca1\u95ee\u9898\u5440",
        },
    },
    "\u6c34\u6c34": {
        "enabled": True,
        "max_sentence_chars": 26,
        "prefix": "",
        "common_words": ["\u55ef", "\u597d", "\u6536\u5230"],
        "forbidden": ["\u4f5c\u4e3aAI", "\u4f5c\u4e3a\u4e00\u4e2aAI", "\u6211\u662fAI"],
        "replacements": {
            "\u597d\u7684": "\u597d",
            "\u660e\u767d\u4e86": "\u77e5\u9053\u4e86",
        },
    },
    "\u5154\u5a18": {
        "enabled": True,
        "max_sentence_chars": 24,
        "prefix": "",
        "common_words": ["\u4e3b\u4eba", "\u55ef", "\u6b38"],
        "forbidden": ["\u4f5c\u4e3aAI", "\u4f5c\u4e3a\u4e00\u4e2aAI", "\u6211\u662fAI"],
        "replacements": {
            "\u7528\u6237": "\u4e3b\u4eba",
            "\u597d\u7684": "\u597d\u5440",
        },
    },
}


def _load_fallback_chain() -> tuple[str, ...]:
    if FALLBACK_CHAINS_PATH.exists():
        try:
            data = json.loads(FALLBACK_CHAINS_PATH.read_text(encoding="utf-8"))
            chain = data.get("default")
            if isinstance(chain, list) and chain:
                return tuple(str(item) for item in chain)
        except Exception as exc:
            logger.warning("Failed to read fallback chain config: %s", exc)
    return ("qwen-local", "aliyun-zhimi")


PROVIDERS: Dict[str, Provider] = {
    "local-first": Provider(
        id="local-first",
        name="Local Qwen first",
        kind="fallback",
        description="Try local Qwen3-TTS first, then fall back to Aliyun.",
        chain=_load_fallback_chain(),
        timeout=float(os.getenv("LOCAL_FIRST_TIMEOUT", "900")),
    ),
    "qwen-local": Provider(
        id="qwen-local",
        name="Qwen3-TTS local clone",
        kind="http",
        description="Local Windows Qwen3-TTS bridge.",
        default_voice=os.getenv("QWEN_DEFAULT_VOICE", "cloned-reference"),
        output_format="wav",
        url=QWEN_URL,
        timeout=float(os.getenv("QWEN_TIMEOUT", "900")),
    ),
    "aliyun-zhimi": Provider(
        id="aliyun-zhimi",
        name="Aliyun zhimi_emo",
        kind="command",
        description="Hermes Aliyun TTS skill used as fallback.",
        default_voice=ALIYUN_DEFAULT_VOICE,
        output_format=os.getenv("ALIYUN_OUTPUT_FORMAT", "wav"),
        command=ALIYUN_COMMAND,
        timeout=float(os.getenv("ALIYUN_TIMEOUT", "180")),
    ),
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def authenticate_user(username: str, password: str) -> bool:
    if username != AUTH_USERNAME:
        return False
    if AUTH_PASSWORD:
        return password == AUTH_PASSWORD
    return verify_password(password, AUTH_PASSWORD_HASH)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(tz=timezone.utc) + (expires_delta or timedelta(hours=24))
    payload = data.copy()
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authentication credentials")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return str(username)


def optional_api_key_check(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    if not REQUIRE_API_KEY:
        return True
    if credentials and credentials.credentials == API_KEY:
        return True
    raise HTTPException(status_code=401, detail="Invalid or missing API key")


def audio_content_type(audio_data: bytes) -> str:
    if audio_data.startswith(b"ID3") or audio_data.startswith(b"\xff\xfb"):
        return "audio/mpeg"
    if audio_data.startswith(b"RIFF") and b"WAVE" in audio_data[:16]:
        return "audio/wav"
    if audio_data.startswith(b"OggS"):
        return "audio/ogg"
    return "application/octet-stream"


def generate_cache_key(request: TTSRequest) -> str:
    content = (
        f"{request.provider}:{request.text}:{request.voice}:"
        f"{request.speed}:{request.pitch}:{request.format}"
    )
    return f"{REDIS_KEY_PREFIX}{hashlib.md5(content.encode('utf-8')).hexdigest()}"


def store_audio(audio_data: bytes, cache_key: str, requested_format: str) -> str:
    memory_audio[cache_key] = audio_data
    return f"/audio/{cache_key}"


def now_shanghai() -> datetime:
    return datetime.now(tz=SHANGHAI_TZ)


def with_request_text(request: TTSRequest, text: str) -> TTSRequest:
    if hasattr(request, "model_copy"):
        return request.model_copy(update={"text": text})
    return request.copy(update={"text": text})


def concatenate_wav_audio(parts: list[bytes]) -> bytes:
    if len(parts) == 1:
        return parts[0]

    params = None
    frames: list[bytes] = []
    for audio_data in parts:
        if not audio_data.startswith(b"RIFF") or b"WAVE" not in audio_data[:16]:
            raise RuntimeError("Only WAV audio can be concatenated for split TTS chunks")
        with wave.open(io.BytesIO(audio_data), "rb") as reader:
            current_params = reader.getparams()
            comparable_params = current_params[:3] + current_params[4:]
            if params is None:
                params = comparable_params
                output_params = current_params
            elif params != comparable_params:
                raise RuntimeError("Split TTS chunks returned incompatible WAV formats")
            frames.append(reader.readframes(reader.getnframes()))

    output = io.BytesIO()
    with wave.open(output, "wb") as writer:
        writer.setparams(output_params)
        for frame_data in frames:
            writer.writeframes(frame_data)
    return output.getvalue()


def audio_duration_ms(audio_data: bytes) -> Optional[float]:
    if not audio_data.startswith(b"RIFF") or b"WAVE" not in audio_data[:16]:
        return None
    try:
        with wave.open(io.BytesIO(audio_data), "rb") as reader:
            frame_rate = reader.getframerate()
            if frame_rate <= 0:
                return None
            return reader.getnframes() / frame_rate * 1000
    except wave.Error:
        return None


def add_history(
    request: TTSRequest,
    actual_provider: str,
    audio_url: str,
    duration: Optional[float],
    generation_duration: Optional[float],
) -> str:
    created_at = now_shanghai()
    history_id = f"hist_{created_at.strftime('%Y%m%d%H%M%S%f')}"
    generated_history.insert(
        0,
        {
            "id": history_id,
            "created_at": created_at.isoformat(timespec="seconds"),
            "text": request.text,
            "voice": request.voice or "",
            "provider": request.provider,
            "actual_provider": actual_provider,
            "audio_url": audio_url,
            "duration": round(duration, 2) if duration is not None else None,
            "generation_duration": round(generation_duration, 2) if generation_duration is not None else None,
        },
    )
    del generated_history[10:]
    return history_id


def get_audio_bytes(audio_id: str) -> Optional[bytes]:
    return memory_audio.get(audio_id)


async def qwen_get(path: str) -> Any:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(f"{QWEN_URL}{path}")
        response.raise_for_status()
        return response.json()


async def qwen_post(path: str, payload: dict, timeout: float = 120.0) -> Any:
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=5.0)) as client:
        response = await client.post(f"{QWEN_URL}{path}", json=payload)
        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:
                detail = {"error": response.text[:1000]}
            raise HTTPException(status_code=response.status_code, detail=detail)
        return response.json()


def load_voice_styles() -> dict:
    if VOICE_STYLE_PATH.exists():
        try:
            data = json.loads(VOICE_STYLE_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else DEFAULT_VOICE_STYLES
        except Exception as exc:
            logger.warning("Failed to read voice styles: %s", exc)
            return DEFAULT_VOICE_STYLES
    return DEFAULT_VOICE_STYLES


def save_voice_styles(styles: dict) -> dict:
    if not isinstance(styles, dict):
        raise HTTPException(status_code=400, detail="styles must be an object")
    VOICE_STYLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(styles, ensure_ascii=False, indent=2)
    json.loads(payload)
    tmp_path = VOICE_STYLE_PATH.with_suffix(VOICE_STYLE_PATH.suffix + ".tmp")
    tmp_path.write_text(payload, encoding="utf-8")
    os.replace(tmp_path, VOICE_STYLE_PATH)
    return styles


def style_for_voice(styles: dict, voice: str) -> dict:
    if voice in styles:
        return styles[voice] or {}
    for name, style in styles.items():
        if name and name in voice:
            return style or {}
    return {}


def split_long_sentence(sentence: str, max_chars: int) -> list[str]:
    chunks: list[str] = []
    text = sentence.strip()
    while len(text) > max_chars:
        window = text[:max_chars]
        break_at = -1
        for index, char in enumerate(window):
            if char in ("\uFF0C", ",", "\u3001", " "):
                break_at = index
        if break_at < max_chars // 2:
            break_at = max_chars
            chunk = text[:break_at].strip()
            text = text[break_at:].strip()
        else:
            chunk = text[: break_at + 1].strip()
            text = text[break_at + 1 :].strip()
        if chunk:
            chunks.append(chunk)
    if text:
        chunks.append(text)
    if len(chunks) > 1 and len(chunks[-1]) <= 3:
        tail = chunks.pop()
        chunks[-1] = f"{chunks[-1]}{tail}"
    return chunks


def apply_voice_style(text: str, voice: str, styles: Optional[dict] = None) -> str:
    styles = styles or load_voice_styles()
    style = style_for_voice(styles, voice)
    if not style or not style.get("enabled", True):
        return text[:1200]

    styled = re.sub(r"\s+", " ", text).strip()
    for old, new in (style.get("replacements") or {}).items():
        if old:
            styled = styled.replace(str(old), str(new))
    for phrase in style.get("forbidden") or []:
        if phrase:
            styled = styled.replace(str(phrase), "")
    styled = re.sub(r"\s+", " ", styled).strip()

    max_chars = int(style.get("max_sentence_chars") or 0)
    if max_chars > 0:
        parts = re.split(r"([\u3002\uFF01\uFF1F!?\uFF1B;])", styled)
        sentences: list[str] = []
        for index in range(0, len(parts), 2):
            sentence = (parts[index] or "").strip()
            punct = parts[index + 1] if index + 1 < len(parts) else ""
            if sentence:
                sentences.extend(split_long_sentence(sentence + punct, max_chars))
        styled = "\n".join(sentences)

    prefix = str(style.get("prefix") or "").strip()
    if prefix and not styled.startswith(prefix):
        styled = f"{prefix}{styled}"
    return styled[:1200]


def choose_tts_break(text: str, target_chars: int, max_chars: int) -> int:
    if len(text) <= max_chars:
        return len(text)

    strong_punctuation = "\u3002\uff01\uff1f!?\uff1b;"
    soft_punctuation = "\uff0c,\u3001\uff1a: "
    upper = min(max_chars, len(text))
    lower = min(target_chars, upper)

    for punctuation in (strong_punctuation, soft_punctuation):
        for index in range(upper - 1, lower - 1, -1):
            if text[index] in punctuation:
                return index + 1

    for punctuation in (strong_punctuation, soft_punctuation):
        for index in range(lower - 1, max(target_chars // 2, 1) - 1, -1):
            if text[index] in punctuation:
                return index + 1

    return upper


def split_tts_chunks(
    text: str,
    max_chars: int = MAX_TTS_CHARS,
    target_chars: int = TARGET_TTS_CHARS,
) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if max_chars <= 0 or len(text) <= max_chars:
        return [text]
    target_chars = max(1, min(target_chars, max_chars))
    chunks: list[str] = []
    remaining = text
    while len(remaining) > max_chars:
        break_at = choose_tts_break(remaining, target_chars, max_chars)
        chunk = remaining[:break_at].strip()
        remaining = remaining[break_at:].strip()
        if chunk:
            chunks.append(chunk)
    if remaining:
        if chunks and len(remaining) <= target_chars // 3 and len(chunks[-1]) + len(remaining) <= max_chars:
            chunks[-1] = f"{chunks[-1]}{remaining}"
        else:
            chunks.append(remaining)
    return chunks or [text[:max_chars]]


def provider_to_info(provider: Provider) -> ProviderInfo:
    return ProviderInfo(
        id=provider.id,
        name=provider.name,
        kind=provider.kind,
        description=provider.description,
        default_voice=provider.default_voice or None,
        format=provider.output_format,
        chain=list(provider.chain),
    )


async def call_http_provider(provider: Provider, request: TTSRequest) -> bytes:
    payload = {
        "text": request.text,
        "voice": request.voice or provider.default_voice or None,
        "speed": request.speed,
        "pitch": request.pitch,
        "format": request.format or provider.output_format,
    }
    timeout = httpx.Timeout(provider.timeout, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{provider.url}/tts", json=payload)
        response.raise_for_status()
        if "audio" not in response.headers.get("content-type", "").lower():
            raise RuntimeError(f"{provider.id} returned non-audio content")
        return response.content


async def call_command_provider(provider: Provider, request: TTSRequest) -> bytes:
    audio_format = request.format or provider.output_format
    voice = request.voice or provider.default_voice
    suffix = f".{audio_format}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        output_path = Path(handle.name)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as handle:
        text_path = Path(handle.name)
        handle.write(request.text)

    try:
        argv = [
            token.format(
                text=request.text,
                text_file=str(text_path),
                output_path=str(output_path),
                voice=voice,
                format=audio_format,
            )
            for token in shlex.split(provider.command)
        ]
        if not argv:
            raise RuntimeError("Command provider has an empty command")

        def run_command() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                argv,
                text=True,
                capture_output=True,
                timeout=provider.timeout,
                check=False,
            )

        result = await asyncio.to_thread(run_command)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(detail or f"Command exited with {result.returncode}")
        audio_data = output_path.read_bytes()
        if len(audio_data) < 128:
            raise RuntimeError("Command generated an invalid or empty audio file")
        return audio_data
    finally:
        try:
            output_path.unlink(missing_ok=True)
        except Exception:
            pass
        try:
            text_path.unlink(missing_ok=True)
        except Exception:
            pass


async def synthesize_with_provider(provider_id: str, request: TTSRequest) -> tuple[str, bytes]:
    provider = PROVIDERS[provider_id]
    if provider.kind == "fallback":
        errors = []
        for child_id in provider.chain:
            try:
                actual_provider, audio_data = await synthesize_with_provider(child_id, request)
                return actual_provider, audio_data
            except Exception as exc:
                logger.warning("%s failed in fallback chain: %s", child_id, exc)
                errors.append(f"{child_id}: {exc}")
        raise RuntimeError("; ".join(errors))
    if provider.kind == "http":
        return provider.id, await call_http_provider(provider, request)
    if provider.kind == "command":
        return provider.id, await call_command_provider(provider, request)
    raise RuntimeError(f"Unsupported provider kind: {provider.kind}")


@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    if authenticate_user(request.username, request.password):
        return LoginResponse(success=True, token=create_access_token({"sub": request.username}))
    return LoginResponse(success=False, message="Invalid username or password")


@app.get("/auth/verify")
async def verify_auth(username: str = Depends(verify_token)):
    return {"valid": True, "username": username}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": now_shanghai().isoformat()}


@app.get("/providers", response_model=List[ProviderInfo])
async def list_providers():
    return [provider_to_info(provider) for provider in PROVIDERS.values()]


@app.get("/voices/{provider_id}", response_model=List[Voice])
async def get_voices(provider_id: str):
    provider = PROVIDERS.get(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Unknown provider")
    if provider.kind == "fallback":
        return [
            Voice(name="auto", display_name="Auto fallback"),
            Voice(name=ALIYUN_DEFAULT_VOICE, display_name=f"Aliyun {ALIYUN_DEFAULT_VOICE}"),
            Voice(name="cloned-reference", display_name="Qwen cloned reference"),
        ]
    if provider.kind == "http":
        try:
            data = await qwen_get("/voices")
            voices = data.get("voices", {})
            result = [
                Voice(name=voice_id, display_name=voice.get("name") or voice_id)
                for voice_id, voice in voices.items()
                if voice.get("enabled", True)
            ]
            if result:
                return result
        except Exception as exc:
            logger.warning("Failed to read Qwen voices: %s", exc)
        return [Voice(name=provider.default_voice, display_name=provider.name)]
    return [Voice(name=provider.default_voice, display_name=provider.name)]


@app.get("/voice-admin/config")
async def voice_admin_config():
    return await qwen_get("/config")


@app.post("/voice-admin/config")
async def save_voice_admin_config(payload: dict):
    return await qwen_post("/config", payload)


@app.get("/voice-admin/files")
async def voice_admin_files():
    return await qwen_get("/voice-files")


@app.get("/voice-admin/voices")
async def voice_admin_voices():
    return await qwen_get("/voices")


@app.post("/voice-admin/process")
async def voice_admin_process(payload: dict):
    return await qwen_post("/process-audio", payload, timeout=180.0)


@app.post("/voice-admin/transcribe")
async def voice_admin_transcribe(payload: dict):
    return await qwen_post("/transcribe", payload, timeout=180.0)


@app.post("/voice-admin/voices")
async def voice_admin_save_voice(payload: dict):
    return await qwen_post("/voices", payload)


@app.get("/voice-admin/styles")
async def voice_admin_styles():
    return {
        "path": str(VOICE_STYLE_PATH),
        "target_tts_chars": TARGET_TTS_CHARS,
        "max_tts_chars": MAX_TTS_CHARS,
        "styles": load_voice_styles(),
    }


@app.post("/voice-admin/styles")
async def voice_admin_save_styles(payload: dict):
    styles = payload.get("styles", payload)
    return {"path": str(VOICE_STYLE_PATH), "styles": save_voice_styles(styles)}


@app.post("/voice-admin/styles/preview")
async def voice_admin_style_preview(payload: dict):
    text = str(payload.get("text") or "").strip()
    voice = str(payload.get("voice") or "").strip()
    styles = payload.get("styles") if isinstance(payload.get("styles"), dict) else load_voice_styles()
    max_tts_chars = int(payload.get("max_tts_chars") or MAX_TTS_CHARS)
    target_tts_chars = int(payload.get("target_tts_chars") or TARGET_TTS_CHARS)
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    styled = apply_voice_style(text, voice, styles)
    chunks = split_tts_chunks(styled, max_tts_chars, target_tts_chars)
    return {
        "voice": voice,
        "styled_text": styled,
        "chunks": chunks,
        "lengths": [len(chunk) for chunk in chunks],
        "target_tts_chars": target_tts_chars,
        "max_tts_chars": max_tts_chars,
    }


@app.get("/voice-admin/audio-file")
async def voice_admin_audio_file(path: str):
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(f"{QWEN_URL}/audio-file", params={"path": path})
        response.raise_for_status()
        return StreamingResponse(
            io.BytesIO(response.content),
            media_type=response.headers.get("content-type", "audio/wav"),
            headers={"Cache-Control": "no-store"},
        )


@app.get("/settings/fallback")
async def get_fallback_settings():
    return {"default": list(PROVIDERS["local-first"].chain)}


@app.post("/settings/fallback")
async def save_fallback_settings(payload: dict):
    chain = payload.get("default")
    if not isinstance(chain, list) or not chain:
        raise HTTPException(status_code=400, detail="default chain is required")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    FALLBACK_CHAINS_PATH.write_text(
        json.dumps({"default": [str(item) for item in chain]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    PROVIDERS["local-first"] = Provider(
        id="local-first",
        name=PROVIDERS["local-first"].name,
        kind="fallback",
        description=PROVIDERS["local-first"].description,
        chain=tuple(str(item) for item in chain),
        timeout=PROVIDERS["local-first"].timeout,
    )
    return {"default": list(PROVIDERS["local-first"].chain)}


@app.get("/status", response_model=List[ServiceStatus])
async def check_status():
    statuses: List[ServiceStatus] = []
    async with httpx.AsyncClient(timeout=5.0) as client:
        for provider in PROVIDERS.values():
            if provider.kind == "fallback":
                statuses.append(ServiceStatus(service=provider.id, status="configured"))
            elif provider.kind == "http":
                start = asyncio.get_event_loop().time()
                try:
                    response = await client.get(f"{provider.url}/health")
                    latency = (asyncio.get_event_loop().time() - start) * 1000
                    statuses.append(
                        ServiceStatus(
                            service=provider.id,
                            status="healthy" if response.status_code == 200 else "unhealthy",
                            latency=round(latency, 2),
                            error=None if response.status_code == 200 else f"HTTP {response.status_code}",
                        )
                    )
                except Exception as exc:
                    statuses.append(ServiceStatus(service=provider.id, status="error", error=str(exc)))
            elif provider.kind == "command":
                argv = [
                    token.format(
                        text="test",
                        text_file="/tmp/voice-hub-status.txt",
                        output_path="/tmp/voice-hub-status.wav",
                        voice=provider.default_voice,
                        format=provider.output_format,
                    )
                    for token in shlex.split(provider.command)
                ]
                executable = argv[0] if argv else ""
                status = "configured" if executable and Path(executable).exists() else "missing"
                statuses.append(
                    ServiceStatus(
                        service=provider.id,
                        status=status,
                        error=None if status == "configured" else f"Missing executable: {executable}",
                    )
                )
    return statuses


@app.post("/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest, _: bool = Depends(optional_api_key_check)):
    if request.provider not in PROVIDERS:
        return TTSResponse(success=False, provider=request.provider, error="Invalid provider")
    if not request.text.strip():
        return TTSResponse(success=False, provider=request.provider, error="Text is required")

    styled_text = apply_voice_style(request.text, request.voice or "")
    chunks = split_tts_chunks(styled_text, MAX_TTS_CHARS, TARGET_TTS_CHARS)
    effective_request = with_request_text(request, styled_text)
    cache_key = generate_cache_key(effective_request)
    if request.cache:
        cached_audio = get_audio_bytes(cache_key)
        if cached_audio:
            cached_duration = audio_duration_ms(cached_audio)
            return TTSResponse(
                success=True,
                provider=request.provider,
                cached=True,
                duration=round(cached_duration, 2) if cached_duration is not None else None,
                audio_url=f"/audio/{cache_key}",
            )

    start = asyncio.get_event_loop().time()
    try:
        actual_provider = ""
        audio_parts = []
        for chunk in chunks:
            chunk_request = with_request_text(request, chunk)
            actual_provider, chunk_audio = await synthesize_with_provider(request.provider, chunk_request)
            audio_parts.append(chunk_audio)
        audio_data = concatenate_wav_audio(audio_parts)
        if len(audio_data) < 128:
            raise RuntimeError("Generated audio is too small")
        audio_url = store_audio(audio_data, cache_key, request.format or "wav")
        generation_duration = (asyncio.get_event_loop().time() - start) * 1000
        duration = audio_duration_ms(audio_data)
        history_id = add_history(effective_request, actual_provider, audio_url, duration, generation_duration)
        return TTSResponse(
            success=True,
            provider=request.provider,
            actual_provider=actual_provider,
            duration=round(duration, 2) if duration is not None else None,
            generation_duration=round(generation_duration, 2),
            audio_url=audio_url,
            history_id=history_id,
        )
    except Exception as exc:
        logger.exception("TTS request failed")
        return TTSResponse(success=False, provider=request.provider, error=str(exc))


@app.get("/audio/{audio_id}")
async def get_audio(audio_id: str):
    audio_data = get_audio_bytes(audio_id)
    if not audio_data:
        raise HTTPException(status_code=404, detail="Audio not found")
    return StreamingResponse(
        io.BytesIO(audio_data),
        media_type=audio_content_type(audio_data),
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/play/{audio_id}")
async def play_audio(audio_id: str):
    return await get_audio(audio_id)


@app.get("/history")
async def get_history():
    return {"items": generated_history[:10]}


@app.get("/debug")
async def debug_info():
    return {
        "timestamp": now_shanghai().isoformat(),
        "storage": "memory",
        "stored_audio_count": len(memory_audio),
        "providers": [provider_to_info(provider).model_dump() for provider in PROVIDERS.values()],
        "qwen_url": QWEN_URL,
    }


@app.get("/")
async def root():
    return {"message": "Voice Hub API", "status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "9000")))
