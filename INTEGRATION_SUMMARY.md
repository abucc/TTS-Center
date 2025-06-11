# TTS Services Integration Summary

## Updated Services Using Official Repositories

### 1. Kokoro ONNX TTS (isaacgounton/kokoro-onnx)
- **Repository**: https://github.com/isaacgounton/kokoro-onnx.git
- **Installation**: `pip install kokoro-onnx`
- **Features**: High-quality multilingual TTS with ONNX runtime
- **Status**: ✅ Updated and integrated

### 2. OpenAI Edge TTS (isaacgounton/openai-edge-tts)
- **Repository**: https://github.com/isaacgounton/openai-edge-tts.git
- **Implementation**: Flask-based OpenAI-compatible TTS API
- **Features**: Uses Microsoft Edge TTS with OpenAI-style endpoints
- **Status**: ✅ Updated and integrated

### 3. Chatterbox TTS Server (isaacgounton/Chatterbox-TTS-Server)
- **Repository**: https://github.com/isaacgounton/Chatterbox-TTS-Server.git
- **Installation**: CPU-only installation (GPU components removed)
- **Features**: 
  - Complete Web UI with modern interface
  - Voice cloning with reference audio upload
  - Predefined voices management
  - Large text processing with intelligent chunking
  - Audiobook generation capabilities
  - Advanced generation parameters (temperature, CFG weight, seed)
  - Configuration management via YAML
  - Audio post-processing options
- **Implementation**: Full server with all advanced features
- **Status**: ✅ Full implementation integrated (CPU-only)

## Service Architecture

```
Internet → TTS Gateway (Port 9000) → Individual TTS Services
                                   ├── Kokoro ONNX (8000)
                                   ├── Chatterbox TTS (8000)  
                                   └── OpenAI Edge TTS (5050)
```

## API Endpoints

### Main Gateway (Port 9000)
- `POST /tts` - Unified TTS endpoint
- `GET /voices/{provider}` - Get voices for specific provider
- `GET /status` - Check all services health
- `GET /` - Web interface

### Provider-Specific Endpoints
- **Kokoro**: Standard TTS with multilingual support
- **Chatterbox**: OpenAI-compatible `/v1/audio/speech` + custom `/tts`
- **OpenAI Edge TTS**: OpenAI-compatible `/v1/audio/speech`

## Docker Configuration

All services are configured with:
- Health checks
- Resource limits
- Volume mounts for models and cache
- Proper networking

## Deployment Notes for Coolify

1. **Main Service**: `tts-gateway` exposes port 9000
2. **Internal Services**: All other services run on internal network
3. **Resource Usage**: 
   - Chatterbox TTS: ~3GB RAM (CPU-only)
   - Kokoro ONNX: ~4GB RAM
   - OpenAI Edge TTS: ~1GB RAM
   - Gateway: ~1GB RAM

## Environment Variables

Key environment variables for customization:
- `KOKORO_URL`: Internal URL for Kokoro service
- `CHATTERBOX_URL`: Internal URL for Chatterbox service  
- `OPENAI_EDGE_TTS_URL`: Internal URL for OpenAI Edge TTS service
- `CORS_ORIGINS`: CORS configuration

## Usage Examples

### Python Client
```python
import requests

response = requests.post('https://your-domain.com/tts', json={
    "text": "Hello, this is awesome TTS!",
    "provider": "chatterbox",
    "voice": "default",
    "speed": 1.0,
    "format": "wav"
})

if response.status_code == 200:
    result = response.json()
    print(f"Generated audio: {result['audio_url']}")
```

### cURL Example
```bash
curl -X POST https://your-domain.com/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Test message",
    "provider": "kokoro", 
    "voice": "af_heart",
    "speed": 1.2
  }'
```

## Ready for Coolify Deployment

The entire stack is now configured with the official implementations from your specified repositories and ready for deployment on your Coolify server.
