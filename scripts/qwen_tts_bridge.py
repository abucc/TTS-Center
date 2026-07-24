import json
import os
import shutil
import subprocess
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen

from gradio_client import Client, handle_file


QWEN_URL = "http://127.0.0.1:7860"
HOST = "0.0.0.0"
PORT = 7861

BASE_DIR = Path(r"D:\aiData")
CONFIG_PATH = BASE_DIR / "voice_bridge_config.json"
DEFAULT_VOICES_DIR = BASE_DIR / "voices"
PROCESSED_DIR_NAME = "processed"

DEFAULT_REF_AUDIO = BASE_DIR / "qwen_ref_clean_20s.wav"
DEFAULT_REF_TEXT = (
    "大家可以早点去睡觉因为我就是我就是今天晚上睡不着然后就给大家开个直播"
    "想同你们聊聊天谢谢你们就是关注我但是我就是第一次直播然后那么大半夜"
)

LANGUAGE = "Chinese"
MODEL_SIZE = os.getenv("QWEN_TTS_MODEL_SIZE", "1.7B")
QWEN_START_SCRIPT = Path(os.getenv("QWEN_TTS_START_SCRIPT", str(BASE_DIR / "start_qwen3_tts_stack.ps1")))
QWEN_APP_ROOT = Path(os.getenv("QWEN_TTS_APP_ROOT", r"D:\models\pinokio\api\Qwen3-TTS-Pinokio.git\app"))
QWEN_PYTHON = Path(os.getenv("QWEN_TTS_PYTHON", str(QWEN_APP_ROOT / "venv" / "Scripts" / "python.exe")))
QWEN_PYTHONW = Path(os.getenv("QWEN_TTS_PYTHONW", str(QWEN_APP_ROOT / "venv" / "Scripts" / "pythonw.exe")))
QWEN_APP = Path(os.getenv("QWEN_TTS_APP", str(QWEN_APP_ROOT / "app.py")))
QWEN_OUT_LOG = BASE_DIR / "qwen3_tts_lan.out.log"
QWEN_ERR_LOG = BASE_DIR / "qwen3_tts_lan.err.log"
MAX_CHUNK_CHARS = 120
CHUNK_GAP = 0.12
SEED = int(os.getenv("QWEN_TTS_SEED", "20260722"))
SUPPORTED_AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}
FFMPEG = os.getenv("FFMPEG_PATH") or shutil.which("ffmpeg") or r"D:\models\pinokio\bin\miniforge\Library\bin\ffmpeg.exe"
TRADITIONAL_TO_SIMPLIFIED = str.maketrans(
    {
        "這": "这",
        "個": "个",
        "們": "们",
        "來": "来",
        "說": "说",
        "話": "话",
        "聽": "听",
        "聲": "声",
        "音": "音",
        "語": "语",
        "識": "识",
        "別": "别",
        "實": "实",
        "際": "际",
        "對": "对",
        "應": "应",
        "裏": "里",
        "裡": "里",
        "還": "还",
        "會": "会",
        "讓": "让",
        "為": "为",
        "後": "后",
        "開": "开",
        "關": "关",
        "過": "过",
        "時": "时",
        "間": "间",
        "點": "点",
        "麼": "么",
        "嗎": "吗",
        "妳": "你",
        "與": "与",
        "寫": "写",
        "讀": "读",
        "選": "选",
        "擇": "择",
        "參": "参",
        "錄": "录",
        "檔": "档",
        "測": "测",
        "試": "试",
        "啟": "启",
        "動": "动",
        "狀": "状",
        "態": "态",
        "錯": "错",
        "誤": "误",
        "發": "发",
        "現": "现",
        "簡": "简",
        "體": "体",
        "雲": "云",
        "阿": "阿",
        "貝": "贝",
        "貓": "猫",
        "邊": "边",
        "幫": "帮",
        "幾": "几",
        "剛": "刚",
        "剛": "刚",
        "級": "级",
        "麼": "么",
        "們": "们",
        "當": "当",
        "從": "从",
        "將": "将",
        "導": "导",
        "並": "并",
        "無": "无",
        "電": "电",
        "腦": "脑",
        "機": "机",
        "網": "网",
        "頁": "页",
        "顯": "显",
        "示": "示",
        "檢": "检",
        "查": "查",
        "嗎": "吗",
        "長": "长",
        "幹": "干",
        "乾": "干",
        "淨": "净",
        "標": "标",
        "準": "准",
        "轉": "转",
        "換": "换",
        "處": "处",
        "理": "理",
        "萬": "万",
        "葉": "叶",
        "裏": "里",
        "體": "体",
    }
)


def to_simplified(text: str) -> str:
    try:
        from opencc import OpenCC

        return OpenCC("t2s").convert(text)
    except Exception:
        return text.translate(TRADITIONAL_TO_SIMPLIFIED)


def _safe_id(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or "voice"


def _is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def download_audio(url: str) -> Path:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix not in SUPPORTED_AUDIO_EXTS:
        suffix = ".wav"
    request = Request(url, headers={"User-Agent": "QwenTTSBridge/1.2"})
    with urlopen(request, timeout=60) as response:
        data = response.read()
    if len(data) < 128:
        raise RuntimeError(f"远程音频为空或无效: {url}")
    target = Path(tempfile.gettempdir()) / f"qwen_tts_bridge_ref_{next(tempfile._get_candidate_names())}{suffix}"
    target.write_bytes(data)
    return target


def materialize_audio(path_value: str, url_value: str = "") -> tuple[Path, bool]:
    url_value = str(url_value or "").strip()
    path_value = str(path_value or "").strip()
    if url_value:
        return download_audio(url_value), True
    if _is_url(path_value):
        return download_audio(path_value), True
    return Path(path_value), False


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"voices_dir": str(DEFAULT_VOICES_DIR)}


def _save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def voices_dir() -> Path:
    path = Path(_load_config().get("voices_dir") or DEFAULT_VOICES_DIR)
    path.mkdir(parents=True, exist_ok=True)
    (path / PROCESSED_DIR_NAME).mkdir(parents=True, exist_ok=True)
    return path


def voices_json_path() -> Path:
    return voices_dir() / "voices.json"


def load_voices() -> dict:
    path = voices_json_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("voices", data) if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_voices(voices: dict) -> None:
    voices_json_path().write_text(
        json.dumps({"voices": voices}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def list_audio_files() -> list[dict]:
    root = voices_dir()
    voices = load_voices()
    configured_by_audio = {Path(v.get("source_audio", "")).name: vid for vid, v in voices.items()}
    items = []
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_AUDIO_EXTS:
            continue
        voice_id = configured_by_audio.get(path.name) or _safe_id(path.stem)
        items.append(
            {
                "file_name": path.name,
                "path": str(path),
                "id": voice_id,
                "configured": voice_id in voices,
                "config": voices.get(voice_id),
            }
        )
    return items


def resolve_voice(voice_id: str | None) -> tuple[str, str, str]:
    if voice_id:
        voice = load_voices().get(voice_id)
        if voice and voice.get("enabled", True):
            return (
                str(voice.get("reference_audio") or ""),
                str(voice.get("reference_text") or ""),
                str(voice.get("reference_audio_url") or ""),
            )
    return str(DEFAULT_REF_AUDIO), DEFAULT_REF_TEXT, ""


def synthesize(text: str, voice_id: str | None = None) -> Path:
    ref_audio_value, ref_text, ref_audio_url = resolve_voice(voice_id)
    ref_audio, cleanup_ref = materialize_audio(ref_audio_value, ref_audio_url)
    if not ref_audio.exists():
        raise RuntimeError(f"参考音频不存在: {ref_audio}")
    if not ref_text.strip():
        raise RuntimeError("参考文本为空")

    try:
        client = Client(QWEN_URL)
        generated_audio, status = client.predict(
            handle_file(str(ref_audio)),
            ref_text,
            text,
            LANGUAGE,
            False,
            MODEL_SIZE,
            MAX_CHUNK_CHARS,
            CHUNK_GAP,
            SEED,
            api_name="/generate_voice_clone",
        )
        if not generated_audio:
            raise RuntimeError(f"Qwen returned no audio: {status}")
        src = Path(generated_audio)
        dst = Path(tempfile.gettempdir()) / f"qwen_tts_bridge_{next(tempfile._get_candidate_names())}.wav"
        shutil.copy2(src, dst)
        return dst
    finally:
        if cleanup_ref:
            try:
                ref_audio.unlink(missing_ok=True)
            except OSError:
                pass


def transcribe_audio(audio_path: Path) -> str:
    client = Client(QWEN_URL)
    result = client.predict(handle_file(str(audio_path)), api_name="/transcribe_audio")
    if isinstance(result, (list, tuple)):
        result = result[0] if result else ""
    return to_simplified(str(result or "").strip())


def process_audio(source_path: Path, voice_id: str, start: float = 0, duration: float = 20) -> Path:
    if not source_path.exists():
        raise RuntimeError(f"音频不存在: {source_path}")
    if not Path(FFMPEG).exists():
        raise RuntimeError(f"ffmpeg 不存在: {FFMPEG}")
    out = voices_dir() / PROCESSED_DIR_NAME / f"{_safe_id(voice_id)}.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    filters = "highpass=f=80,lowpass=f=9000,afftdn=nf=-25,loudnorm=I=-18:TP=-1.5:LRA=11"
    cmd = [
        FFMPEG,
        "-y",
        "-ss",
        str(max(0, start)),
        "-t",
        str(max(1, duration)),
        "-i",
        str(source_path),
        "-af",
        filters,
        "-ar",
        "16000",
        "-ac",
        "1",
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or b"").decode("utf-8", errors="ignore")
        raise RuntimeError(detail[-1000:] or "ffmpeg 清洗失败")
    return out


def save_voice(payload: dict) -> dict:
    voice_id = _safe_id(str(payload.get("id") or payload.get("name") or "voice"))
    name = str(payload.get("name") or voice_id).strip()
    source_audio = Path(str(payload.get("source_audio") or ""))
    reference_audio_value = str(payload.get("reference_audio") or source_audio)
    reference_audio_url = str(payload.get("reference_audio_url") or "").strip()
    source_audio_url = str(payload.get("source_audio_url") or "").strip()
    reference_audio, cleanup_ref = materialize_audio(reference_audio_value, reference_audio_url)
    reference_text = str(payload.get("reference_text") or "").strip()
    try:
        if not reference_audio.exists():
            raise RuntimeError(f"参考音频不存在: {reference_audio}")
        if not reference_text:
            raise RuntimeError("参考文本不能为空")
    finally:
        if cleanup_ref:
            try:
                reference_audio.unlink(missing_ok=True)
            except OSError:
                pass
    voices = load_voices()
    voices[voice_id] = {
        "id": voice_id,
        "name": name,
        "source_audio": str(source_audio) if source_audio else "",
        "source_audio_url": source_audio_url,
        "reference_audio": reference_audio_value,
        "reference_audio_url": reference_audio_url,
        "reference_text": reference_text,
        "enabled": bool(payload.get("enabled", True)),
    }
    save_voices(voices)
    return voices[voice_id]


def qwen_pid() -> int | None:
    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            text=True,
            encoding="gbk",
            errors="ignore",
            capture_output=True,
            timeout=5,
            check=False,
            **hidden_subprocess_kwargs(),
        )
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[1].endswith(":7860") and parts[3].upper() == "LISTENING":
                return int(parts[-1])
    except Exception:
        return None
    return None


def hidden_subprocess_kwargs() -> dict:
    if os.name != "nt":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags |= subprocess.CREATE_NO_WINDOW
    return {"startupinfo": startupinfo, "creationflags": creationflags}


def wait_for_qwen(timeout_seconds: int = 120) -> int | None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        pid = qwen_pid()
        if pid:
            return pid
        time.sleep(1)
    return qwen_pid()


def start_qwen_service() -> dict:
    pid = qwen_pid()
    if pid:
        status = gpu_status()
        status.update({"action": "start", "message": "Qwen3-TTS 已经在运行", "started": False})
        return status

    launch_python = QWEN_PYTHONW if QWEN_PYTHONW.exists() else QWEN_PYTHON
    if not launch_python.exists():
        raise RuntimeError(f"Qwen Python 不存在: {launch_python}")
    if not QWEN_APP.exists():
        raise RuntimeError(f"Qwen app.py 不存在: {QWEN_APP}")

    creationflags = 0
    startupinfo = None
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            creationflags |= subprocess.CREATE_NO_WINDOW
        if hasattr(subprocess, "DETACHED_PROCESS"):
            creationflags |= subprocess.DETACHED_PROCESS
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

    env = os.environ.copy()
    env.update(
        {
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "HF_ENDPOINT": env.get("HF_ENDPOINT", "https://hf-mirror.com"),
            "HF_HUB_ENABLE_HF_TRANSFER": env.get("HF_HUB_ENABLE_HF_TRANSFER", "0"),
            "QWEN_TTS_MODEL_SIZE": MODEL_SIZE,
        }
    )
    stdout = QWEN_OUT_LOG.open("ab")
    stderr = QWEN_ERR_LOG.open("ab")
    subprocess.Popen(
        [str(launch_python), str(QWEN_APP)],
        cwd=str(QWEN_APP_ROOT),
        stdout=stdout,
        stderr=stderr,
        env=env,
        creationflags=creationflags,
        startupinfo=startupinfo,
    )
    stdout.close()
    stderr.close()

    pid = wait_for_qwen(120)
    status = gpu_status()
    status.update(
        {
            "action": "start",
            "started": bool(pid),
            "message": "Qwen3-TTS 已启动" if pid else "已发送启动命令，Qwen3-TTS 还在启动中",
        }
    )
    return status


def stop_qwen_service() -> dict:
    pid = qwen_pid()
    if not pid:
        status = gpu_status()
        status.update({"action": "stop", "stopped": False, "message": "Qwen3-TTS 当前没有运行"})
        return status

    if os.name == "nt":
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            text=True,
            encoding="gbk",
            errors="ignore",
            capture_output=True,
            timeout=20,
            check=False,
            **hidden_subprocess_kwargs(),
        )
    else:
        result = subprocess.run(
            ["kill", "-TERM", str(pid)],
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "停止 Qwen3-TTS 失败").strip())

    time.sleep(1)
    status = gpu_status()
    status.update({"action": "stop", "stopped": True, "message": "Qwen3-TTS 已关闭"})
    return status


def nvidia_smi_query(args: list[str]) -> str:
    result = subprocess.run(
        ["nvidia-smi", *args],
        text=True,
        encoding="gbk",
        errors="ignore",
        capture_output=True,
        timeout=8,
        check=False,
        **hidden_subprocess_kwargs(),
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "nvidia-smi failed").strip())
    return result.stdout.strip()


def gpu_status() -> dict:
    pid = qwen_pid()
    status = {
        "model_type": "Base",
        "model_size": MODEL_SIZE,
        "qwen_pid": pid,
        "loaded": False,
        "loaded_status": "",
        "gpu_available": False,
        "gpu_memory_used_mb": None,
        "gpu_memory_free_mb": None,
        "qwen_gpu_memory_mb": None,
        "error": "",
    }
    try:
        gpu_line = nvidia_smi_query(
            ["--query-gpu=memory.used,memory.free", "--format=csv,noheader,nounits"]
        ).splitlines()[0]
        used, free = [int(part.strip()) for part in gpu_line.split(",")[:2]]
        status.update({"gpu_available": True, "gpu_memory_used_mb": used, "gpu_memory_free_mb": free})
    except Exception as exc:
        status["error"] = str(exc)

    if pid:
        try:
            apps = nvidia_smi_query(
                ["--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"]
            )
            for line in apps.splitlines():
                parts = [part.strip() for part in line.split(",")]
                if len(parts) >= 2 and parts[0].isdigit() and int(parts[0]) == pid and parts[1].isdigit():
                    status["qwen_gpu_memory_mb"] = int(parts[1])
                    break
        except Exception:
            pass

    try:
        loaded_status = Client(QWEN_URL).predict(api_name="/get_loaded_models_status")
        status["loaded_status"] = str(loaded_status)
        status["loaded"] = f"Base ({MODEL_SIZE})" in status["loaded_status"]
    except Exception as exc:
        status["loaded_status"] = f"读取模型加载状态失败: {exc}"
    return status


def load_model_to_gpu() -> dict:
    client = Client(QWEN_URL)
    load_status, loaded_status = client.predict("Base", MODEL_SIZE, api_name="/load_model_manual")
    status = gpu_status()
    status["load_status"] = str(load_status)
    status["loaded_status"] = str(loaded_status)
    status["loaded"] = f"Base ({MODEL_SIZE})" in status["loaded_status"]
    return status


class Handler(BaseHTTPRequestHandler):
    server_version = "QwenTTSBridge/1.1"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"ok": True, "voices_dir": str(voices_dir())})
        elif parsed.path == "/gpu-status":
            self._send_json(200, gpu_status())
        elif parsed.path == "/config":
            self._send_json(200, _load_config())
        elif parsed.path == "/voice-files":
            self._send_json(200, {"voices_dir": str(voices_dir()), "files": list_audio_files()})
        elif parsed.path == "/voices":
            self._send_json(200, {"voices_dir": str(voices_dir()), "voices": load_voices()})
        elif parsed.path == "/audio-file":
            params = parse_qs(parsed.query)
            path = Path(unquote(params.get("path", [""])[0]))
            self._send_file(path)
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            payload = self._read_json()
            if parsed.path == "/config":
                directory = Path(str(payload.get("voices_dir") or "")).expanduser()
                directory.mkdir(parents=True, exist_ok=True)
                config = _load_config()
                config["voices_dir"] = str(directory)
                _save_config(config)
                self._send_json(200, config)
            elif parsed.path == "/voices":
                self._send_json(200, save_voice(payload))
            elif parsed.path == "/qwen-start":
                self._send_json(200, start_qwen_service())
            elif parsed.path == "/qwen-stop":
                self._send_json(200, stop_qwen_service())
            elif parsed.path == "/gpu-load":
                self._send_json(200, load_model_to_gpu())
            elif parsed.path == "/process-audio":
                source, cleanup_source = materialize_audio(
                    str(payload.get("source_audio") or ""),
                    str(payload.get("source_audio_url") or ""),
                )
                voice_id = str(payload.get("id") or source.stem)
                try:
                    out = process_audio(
                        source,
                        voice_id,
                        float(payload.get("start") or 0),
                        float(payload.get("duration") or 20),
                    )
                finally:
                    if cleanup_source:
                        try:
                            source.unlink(missing_ok=True)
                        except OSError:
                            pass
                self._send_json(200, {"reference_audio": str(out)})
            elif parsed.path == "/transcribe":
                audio_path, cleanup_audio = materialize_audio(
                    str(payload.get("audio_path") or ""),
                    str(payload.get("audio_url") or ""),
                )
                try:
                    self._send_json(200, {"text": transcribe_audio(audio_path)})
                finally:
                    if cleanup_audio:
                        try:
                            audio_path.unlink(missing_ok=True)
                        except OSError:
                            pass
            elif parsed.path == "/tts":
                text = str(payload.get("text") or "").strip()
                voice = str(payload.get("voice") or "").strip() or None
                if not text:
                    self._send_json(400, {"error": "text is required"})
                    return
                wav_path = synthesize(text[:1200], voice)
                data = wav_path.read_bytes()
                try:
                    wav_path.unlink()
                except OSError:
                    pass
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self._send_json(404, {"error": "not found"})
        except Exception as exc:
            self._send_json(502, {"error": str(exc)})

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _send_file(self, path: Path) -> None:
        root = voices_dir().resolve()
        resolved = path.resolve()
        if root not in resolved.parents and resolved != root:
            self._send_json(403, {"error": "path outside voices directory"})
            return
        if not resolved.exists() or not resolved.is_file():
            self._send_json(404, {"error": "file not found"})
            return
        data = resolved.read_bytes()
        content_type = "audio/wav" if resolved.suffix.lower() == ".wav" else "audio/mpeg"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)

    def _send_json(self, status: int, payload: dict):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    voices_dir()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Qwen TTS bridge listening on http://{HOST}:{PORT}", flush=True)
    print(f"Voices directory: {voices_dir()}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
