# server.py

from flask import Flask, request, send_file, jsonify
from gevent.pywsgi import WSGIServer
from dotenv import load_dotenv
import os
import traceback
import edge_tts
import asyncio
import tempfile
import subprocess
from pathlib import Path
import re
import emoji
from functools import wraps

app = Flask(__name__)
load_dotenv()

# Configuration with defaults
DEFAULT_CONFIGS = {
    "API_KEY": 'your_api_key_here',
    "PORT": 8000,
    "DEFAULT_VOICE": 'en-US-AvaNeural',
    "DEFAULT_RESPONSE_FORMAT": 'mp3',
    "DEFAULT_SPEED": 1.0,
    "DEFAULT_LANGUAGE": 'en-US',
    "REQUIRE_API_KEY": False,
    "REMOVE_FILTER": False,
    "EXPAND_API": True,
    "DETAILED_ERROR_LOGGING": True
}

# Load environment variables
API_KEY = os.getenv('API_KEY', DEFAULT_CONFIGS["API_KEY"])
PORT = int(os.getenv('PORT', str(DEFAULT_CONFIGS["PORT"])))
DEFAULT_VOICE = os.getenv('DEFAULT_VOICE', DEFAULT_CONFIGS["DEFAULT_VOICE"])
DEFAULT_RESPONSE_FORMAT = os.getenv('DEFAULT_RESPONSE_FORMAT', DEFAULT_CONFIGS["DEFAULT_RESPONSE_FORMAT"])
DEFAULT_SPEED = float(os.getenv('DEFAULT_SPEED', str(DEFAULT_CONFIGS["DEFAULT_SPEED"])))

def getenv_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in ("yes", "y", "true", "1", "t")

REQUIRE_API_KEY = getenv_bool('REQUIRE_API_KEY', DEFAULT_CONFIGS["REQUIRE_API_KEY"])
REMOVE_FILTER = getenv_bool('REMOVE_FILTER', DEFAULT_CONFIGS["REMOVE_FILTER"])
EXPAND_API = getenv_bool('EXPAND_API', DEFAULT_CONFIGS["EXPAND_API"])
DETAILED_ERROR_LOGGING = getenv_bool('DETAILED_ERROR_LOGGING', DEFAULT_CONFIGS["DETAILED_ERROR_LOGGING"])

# Audio format MIME types
AUDIO_FORMAT_MIME_TYPES = {
    "mp3": "audio/mpeg",
    "opus": "audio/ogg",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "wav": "audio/wav",
    "pcm": "audio/L16"
}

# OpenAI voice names mapped to edge-tts equivalents
voice_mapping = {
    'alloy': 'en-US-AvaNeural',
    'echo': 'en-US-AndrewNeural',
    'fable': 'en-GB-SoniaNeural',
    'onyx': 'en-US-EricNeural',
    'nova': 'en-US-SteffanNeural',
    'shimmer': 'en-US-EmmaNeural'
}

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not REQUIRE_API_KEY:
            return f(*args, **kwargs)
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing or invalid API key"}), 401
        token = auth_header.split('Bearer ')[1]
        if token != API_KEY:
            return jsonify({"error": "Invalid API key"}), 401
        return f(*args, **kwargs)
    return decorated_function

def prepare_tts_input_with_context(text: str) -> str:
    """Prepares text for TTS by cleaning and formatting"""
    # Remove emojis
    text = emoji.replace_emoji(text, replace='')
    
    # Add context for headers
    def header_replacer(match):
        level = len(match.group(1))
        header_text = match.group(2).strip()
        if level == 1:
            return f"Title — {header_text}\n"
        elif level == 2:
            return f"Section — {header_text}\n"
        else:
            return f"Subsection — {header_text}\n"
    
    text = re.sub(r"^(#{1,6})\s+(.*)", header_replacer, text, flags=re.MULTILINE)
    
    # Remove links while keeping the link text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    
    # Describe inline code
    text = re.sub(r"`([^`]+)`", r"code snippet: \1", text)
    
    # Remove bold/italic symbols but keep the content
    text = re.sub(r"(\*\*|__|\*|_)", '', text)
    
    # Remove code blocks
    text = re.sub(r"```([\s\S]+?)```", r"(code block omitted)", text)
    
    # Remove image syntax but add alt text
    text = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"Image: \1", text)
    
    # Remove HTML tags
    text = re.sub(r"</?[^>]+(>|$)", '', text)
    
    # Normalize line breaks
    text = re.sub(r"\n{2,}", '\n\n', text)
    text = re.sub(r" {2,}", ' ', text)
    
    return text.strip()

def is_ffmpeg_installed():
    """Check if FFmpeg is installed and accessible."""
    try:
        subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def speed_to_rate(speed: float) -> str:
    """Converts a multiplicative speed value to the edge-tts "rate" format."""
    if speed < 0 or speed > 2:
        raise ValueError("Speed must be between 0 and 2 (inclusive).")
    
    percentage_change = (speed - 1) * 100
    return f"{percentage_change:+.0f}%"

async def _generate_audio(text, voice, response_format, speed):
    """Generate TTS audio and optionally convert to a different format."""
    # Determine if the voice is an OpenAI-compatible voice or a direct edge-tts voice
    edge_tts_voice = voice_mapping.get(voice, voice)
    
    # Generate the TTS output in mp3 format first
    temp_mp3_file_obj = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_mp3_path = temp_mp3_file_obj.name
    
    try:
        speed_rate = speed_to_rate(speed)
    except Exception as e:
        print(f"Error converting speed: {e}. Defaulting to +0%.")
        speed_rate = "+0%"
    
    # Generate the MP3 file
    communicator = edge_tts.Communicate(text=text, voice=edge_tts_voice, rate=speed_rate)
    await communicator.save(temp_mp3_path)
    temp_mp3_file_obj.close()
    
    # If the requested format is mp3, return the generated file directly
    if response_format == "mp3":
        return temp_mp3_path
    
    # Check if FFmpeg is installed
    if not is_ffmpeg_installed():
        print("FFmpeg is not available. Returning unmodified mp3 file.")
        return temp_mp3_path
    
    # Create a new temporary file for the converted output
    converted_file_obj = tempfile.NamedTemporaryFile(delete=False, suffix=f".{response_format}")
    converted_path = converted_file_obj.name
    converted_file_obj.close()
    
    # Build the FFmpeg command
    ffmpeg_command = [
        "ffmpeg",
        "-i", temp_mp3_path,
        "-c:a", {
            "aac": "aac",
            "mp3": "libmp3lame",
            "wav": "pcm_s16le",
            "opus": "libopus",
            "flac": "flac"
        }.get(response_format, "aac"),
    ]
    
    if response_format != "wav":
        ffmpeg_command.extend(["-b:a", "192k"])
    
    ffmpeg_command.extend([
        "-f", {
            "aac": "mp4",
            "mp3": "mp3",
            "wav": "wav",
            "opus": "ogg",
            "flac": "flac"
        }.get(response_format, response_format),
        "-y",
        converted_path
    ])
    
    try:
        subprocess.run(ffmpeg_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        Path(converted_path).unlink(missing_ok=True)
        Path(temp_mp3_path).unlink(missing_ok=True)
        
        if DETAILED_ERROR_LOGGING:
            error_message = f"FFmpeg error during audio conversion. Command: '{' '.join(e.cmd)}'. Stderr: {e.stderr.decode('utf-8', 'ignore')}"
            print(error_message)
        else:
            error_message = f"FFmpeg error during audio conversion: {e}"
            print(error_message)
        raise RuntimeError(f"FFmpeg error during audio conversion: {e}")
    
    # Clean up the original temporary file
    Path(temp_mp3_path).unlink(missing_ok=True)
    
    return converted_path

def generate_speech(text, voice, response_format, speed=1.0):
    return asyncio.run(_generate_audio(text, voice, response_format, speed))

def get_models():
    return [
        {"id": "tts-1", "name": "Text-to-speech v1"},
        {"id": "tts-1-hd", "name": "Text-to-speech v1 HD"}
    ]

async def _get_voices(language=None):
    all_voices = await edge_tts.list_voices()
    language = language or os.getenv('DEFAULT_LANGUAGE', 'en-US')
    filtered_voices = [
        {"name": v['ShortName'], "gender": v['Gender'], "language": v['Locale']}
        for v in all_voices if language == 'all' or language is None or v['Locale'] == language
    ]
    return filtered_voices

def get_voices(language=None):
    return asyncio.run(_get_voices(language))

@app.route('/v1/audio/speech', methods=['POST'])
@app.route('/audio/speech', methods=['POST'])
@require_api_key
def text_to_speech():
    try:
        data = request.json
        if not data or 'input' not in data:
            return jsonify({"error": "Missing 'input' in request body"}), 400

        text = data.get('input')

        if not REMOVE_FILTER:
            text = prepare_tts_input_with_context(text)

        voice = data.get('voice', DEFAULT_VOICE)
        response_format = data.get('response_format', DEFAULT_RESPONSE_FORMAT)
        speed = float(data.get('speed', DEFAULT_SPEED))
        
        mime_type = AUDIO_FORMAT_MIME_TYPES.get(response_format, "audio/mpeg")

        # Generate the audio file in the specified format with speed adjustment
        output_file_path = generate_speech(text, voice, response_format, speed)

        # Return the file with the correct MIME type
        return send_file(output_file_path, mimetype=mime_type, as_attachment=True, download_name=f"speech.{response_format}")
    except Exception as e:
        if DETAILED_ERROR_LOGGING:
            app.logger.error(f"Error in text_to_speech: {str(e)}\n{traceback.format_exc()}")
        else:
            app.logger.error(f"Error in text_to_speech: {str(e)}")
        return jsonify({"error": "An internal server error occurred", "details": str(e)}), 500

@app.route('/v1/models', methods=['GET', 'POST'])
@app.route('/models', methods=['GET', 'POST'])
@require_api_key
def list_models():
    return jsonify({"data": get_models()})

@app.route('/v1/voices', methods=['GET', 'POST'])
@app.route('/voices', methods=['GET', 'POST'])
@require_api_key
def list_voices():
    specific_language = None
    data = request.args if request.method == 'GET' else request.json
    if data and ('language' in data or 'locale' in data):
        specific_language = data.get('language') if 'language' in data else data.get('locale')
    return jsonify({"voices": get_voices(specific_language)})

@app.route('/v1/voices/all', methods=['GET', 'POST'])
@app.route('/voices/all', methods=['GET', 'POST'])
@require_api_key
def list_all_voices():
    return jsonify({"voices": get_voices('all')})

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "openai-edge-tts"
    })

@app.route('/')
def root():
    return jsonify({
        "service": "OpenAI Edge TTS",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": {
            "tts": "/v1/audio/speech",
            "voices": "/v1/voices",
            "models": "/v1/models",
            "health": "/health"
        }
    })

print(f" Edge TTS (Free Azure TTS) Replacement for OpenAI's TTS API")
print(f" ")
print(f" * Serving OpenAI Edge TTS")
print(f" * Server running on http://localhost:{PORT}")
print(f" * TTS Endpoint: http://localhost:{PORT}/v1/audio/speech")
print(f" ")

if __name__ == '__main__':
    http_server = WSGIServer(('0.0.0.0', PORT), app)
    http_server.serve_forever()
