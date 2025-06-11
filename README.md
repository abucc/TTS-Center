# 🎤 Awesome-TTS

A unified Text-to-Speech gateway that combines multiple TTS providers into a single, easy-to-use API and web interface.

[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

## 🌟 Features

- **5 TTS Providers** in one unified interface
- **Web Interface** for easy testing and demos
- **REST API** with consistent endpoints
- **Redis Caching** for improved performance
- **Production Ready** with SSL, rate limiting, and monitoring
- **Docker Compose** deployment
- **Health Monitoring** and status endpoints

## 🎯 Supported TTS Providers

| Provider | Type | Features | Quality |
|----------|------|----------|---------|
| **Kokoro ONNX** | Neural TTS | Multi-language, High Quality | ⭐⭐⭐⭐⭐ |
| **ChatterboxTTS** | Cloud API | Streamlabs/Polly Backend | ⭐⭐⭐⭐ |
| **OpenAI Edge TTS** | Hybrid | OpenAI-compatible API | ⭐⭐⭐⭐ |
| **Edge TTS** | Microsoft | Built-in Windows voices | ⭐⭐⭐ |
| **Streamlabs TTS** | Cloud API | Popular streaming voices | ⭐⭐⭐ |

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Domain name (optional, for production)
- SSL certificates (for HTTPS)

### 1. Clone and Setup
```bash
git clone https://github.com/yourusername/Awesome-TTS.git
cd Awesome-TTS

# Create required directories
mkdir -p models/kokoro models/chatterbox cache nginx/ssl web
```

### 2. Deploy
```bash
# Start all services
docker-compose up -d

# Monitor logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 3. Access
- **Web Interface**: http://localhost (or your domain)
- **API Docs**: http://localhost/docs
- **Service Status**: http://localhost/status

## 📡 API Usage

### Basic TTS Request
```bash
curl -X POST http://localhost/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is Awesome-TTS!",
    "provider": "kokoro",
    "voice": "af_heart",
    "speed": 1.0,
    "format": "wav"
  }' \
  --output speech.wav
```

### Python Example
```python
import requests

response = requests.post('http://localhost/tts', json={
    "text": "Hello world!",
    "provider": "edge",
    "voice": "alloy",
    "speed": 1.2
})

result = response.json()
if result['success']:
    print(f"Generated in {result['duration']}ms")
    # Download audio from result['audio_url']
```

### Available Endpoints
- `POST /tts` - Generate speech
- `GET /voices/{provider}` - List voices for provider
- `GET /status` - Service health status
- `GET /health` - Overall health check

## 🎛️ Web Interface

The web interface provides:
- **Provider Selection** - Switch between all 5 TTS services
- **Voice Selection** - Dynamic voice loading per provider
- **Speed/Pitch Controls** - Adjust voice parameters
- **Real-time Status** - Monitor service health
- **Audio Playback** - Test generated speech instantly

## 🏗️ Architecture

```
Internet → Nginx (SSL) → TTS Gateway → Individual TTS Services
                                     ├── Kokoro ONNX (8001)
                                     ├── ChatterboxTTS (8002)  
                                     ├── OpenAI Edge TTS (8003)
                                     ├── Streamlabs TTS (8004)
                                     └── Redis (Cache)
```

## 📦 Services

### Kokoro ONNX
- **Neural TTS** with high-quality voices
- **Multi-language** support (EN, JP, CN, ES, FR, etc.)
- **Grade A voices** available
- Automatic model downloading

### ChatterboxTTS  
- **Streamlabs/Polly** backend
- Popular **streaming voices**
- Fast generation times
- Cloud-based processing

### OpenAI Edge TTS
- **OpenAI-compatible** API endpoints
- Edge TTS backend for reliability
- Supports `/v1/audio/speech` endpoint
- Multiple voice options

### Streamlabs TTS
- Direct **Streamlabs API** integration  
- **AWS Polly** voices
- Streaming-optimized
- High reliability

## 🔧 Configuration

### Environment Variables
```yaml
environment:
  - KOKORO_URL=http://kokoro-onnx:8000
  - CHATTERBOX_URL=http://chatterbox-tts:8000
  - EDGE_TTS_URL=http://openai-edge-tts:8000
  - STREAMLABS_URL=http://streamlabs-tts:8000
  - CORS_ORIGINS=*
```

### Custom Voices
Edit voice configurations in the `voices/` directory:
- `kokoro_voices.json` - Kokoro voice definitions
- `edge_tts_voices.json` - Edge TTS voices  
- `openai_edge_tts_voices.json` - OpenAI-style voices
- `streamlabs_voices.json` - Streamlabs voices

## 🔒 Production Deployment

For production use with SSL and your domain:

1. **SSL Setup**:
```bash
# Place your SSL certificates
cp your-domain.crt nginx/ssl/
cp your-domain.key nginx/ssl/
```

2. **Update nginx config** with your domain name

3. **Deploy with SSL**:
```bash
docker-compose up -d
```

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed production setup.

## 🔍 Monitoring

### Health Checks
```bash
# Overall health
curl http://localhost/health

# Service status  
curl http://localhost/status

# Individual service health
curl http://localhost:8001/health  # Kokoro
curl http://localhost:8002/health  # Chatterbox
curl http://localhost:8003/health  # OpenAI Edge
curl http://localhost:8004/health  # Streamlabs
```

### Resource Monitoring
```bash
# Container stats
docker stats

# Service logs
docker-compose logs [service-name]
```

## 🎯 Use Cases

- **Content Creation** - Generate voiceovers for videos
- **Accessibility** - Convert text to speech for visually impaired users  
- **Gaming** - Add voice synthesis to games and applications
- **Streaming** - Text-to-speech for live streams and broadcasts
- **Education** - Create audio content from written materials
- **Development** - Test different TTS providers and voices

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Adding New TTS Providers

1. Create service directory (e.g., `new-tts-service/`)
2. Add Dockerfile and FastAPI application
3. Update `docker-compose.yml`
4. Add provider to gateway
5. Submit pull request

## 📋 Requirements

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **8GB RAM** (recommended)
- **4 CPU cores** (recommended)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Kokoro ONNX](https://github.com/thewh1teagle/kokoro-onnx) - High-quality neural TTS
- [ChatterboxTTS](https://github.com/devnen/Chatterbox-TTS-Server) - Streamlabs TTS server
- [OpenAI Edge TTS](https://github.com/isaacgounton/openai-edge-tts) - OpenAI-compatible Edge TTS
- [Edge TTS](https://github.com/rany2/edge-tts) - Microsoft Edge TTS
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Docker](https://www.docker.com/) - Containerization platform

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/Awesome-TTS&type=Date)](https://star-history.com/#yourusername/Awesome-TTS&Date)

---

**Made with ❤️ for the TTS community**

Found this useful? Please ⭐ star the repository and share it with others!
