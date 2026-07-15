# 🎤 Awesome-TTS

A unified Text-to-Speech gateway that combines multiple TTS providers into a single, easy-to-use API and modern React web interface.

## NAS Voice Hub Notes

This fork is used as a NAS voice center for Hermes/OpenClaw:

- Chinese management UI: `http://192.168.31.180:3003`
- Gateway API: `http://192.168.31.180:9000`
- Local-first provider: Qwen3-TTS first, configurable fallback TTS second
- Voice style rules: common words, forbidden words, replacements, sentence splitting, and 80-character chunking

Project-specific docs:

- [Voice Hub usage](docs/VOICE_HUB_USAGE.md)
- [Hermes TTS config](docs/HERMES_TTS_CONFIG.md)
- [AI TTS handoff](docs/AI_TTS_HANDOFF.md)

[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

## 🌟 Features

- **3 High-Quality TTS Providers** unified in a single gateway
- **Modern React Web Interface** with real-time controls and audio playback
- **REST API** with consistent endpoints across all providers
- **Redis Caching** for improved performance and reduced latency
- **Cloud Storage Support** (S3, DigitalOcean Spaces) for audio files
- **Production Ready** with health monitoring and error handling
- **Docker Compose** deployment for easy setup
- **Real-time Service Monitoring** with status dashboard

## 🎯 Supported TTS Providers

| Provider | Type | Features | Quality | Port |
|----------|------|----------|---------|------|
| **Kokoro ONNX** | Neural TTS | Multi-language, Grade A voices, Fast inference | ⭐⭐⭐⭐⭐ | 9002 |
| **Chatterbox TTS** | Neural TTS | Voice cloning, Reference audio, Advanced features | ⭐⭐⭐⭐⭐ | 9001 |
| **OpenAI Edge TTS** | Edge TTS | OpenAI API compatible, Free Microsoft voices | ⭐⭐⭐⭐ | 5050 |

## 🏗️ Architecture

```
Frontend (React) → TTS Gateway → Individual TTS Services → Redis Cache
    :3003             :9000         ├── Kokoro ONNX (9002)
                                   ├── Chatterbox TTS (9001)
                                   └── OpenAI Edge TTS (5050)
```

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- 8GB RAM (recommended)
- 4 CPU cores (recommended)

### 1. Clone and Setup
```bash
git clone https://github.com/isaacgounton/awesome-tts.git
cd awesome-tts

# Create required directories
mkdir -p models/kokoro models/chatterbox cache
```

### 2. Deploy with Docker Compose
```bash
# Start all services
docker-compose up -d

# Monitor logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 3. Access the Application
- **Web Interface**: http://localhost:3003
- **API Gateway**: http://localhost:9000
- **API Documentation**: http://localhost:9000/docs
- **Service Status**: http://localhost:3003/api/status

#### Individual Services (Direct Access)
- **Kokoro ONNX**: http://localhost:9002
- **Chatterbox TTS**: http://localhost:9001
- **OpenAI Edge TTS**: http://localhost:5050

## 🌐 Web Interface

The modern React frontend provides:

### 🎛️ Provider Selection
- Switch between Kokoro ONNX, Chatterbox TTS, and OpenAI Edge TTS
- Dynamic voice loading for each provider
- Real-time provider status monitoring

### 🎤 Voice Controls
- **Text Input** with character counter
- **Voice Selection** from available provider voices
- **Speed Control** (0.5x - 2.0x)
- **Pitch Control** (0.5x - 2.0x) - for supported providers
- **Format Selection** (WAV/MP3)

### 🔊 Audio Playback
- **Inline Audio Player** with browser controls
- **Play Button** for quick audio preview
- **Download Button** for saving audio files
- **Open in New Tab** for direct file access

### 📊 Real-time Monitoring
- **Service Status Dashboard** with health indicators
- **Response Time Monitoring** for each service
- **Error Display** with detailed error messages
- **Cache Status** showing cached vs. fresh requests

## 📡 API Usage

### Basic TTS Request
```bash
curl -X POST http://localhost:3003/api/tts \
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

### Get Available Voices
```bash
# Kokoro voices
curl http://localhost:3003/api/voices/kokoro

# Chatterbox voices
curl http://localhost:3003/api/voices/chatterbox

# OpenAI Edge TTS voices
curl http://localhost:3003/api/voices/openai-edge-tts
```

### Python Example
```python
import requests

# Generate speech
response = requests.post('http://localhost:9000/tts', json={
    "text": "Hello world!",
    "provider": "kokoro",  # Can be "kokoro", "chatterbox", or "openai-edge-tts"
    "voice": "af_heart",   # Use appropriate voice for selected provider
    "speed": 1.2,
    "format": "wav"
})

result = response.json()
if result['success']:
    print(f"Generated in {result['duration']}ms")
    audio_url = f"http://localhost:9000{result['audio_url']}"
    
    # Download the audio
    audio_response = requests.get(audio_url)
    with open('speech.wav', 'wb') as f:
        f.write(audio_response.content)
else:
    print(f"Error: {result['error']}")
```

### OpenAI Edge TTS Example
```bash
curl -X POST "http://localhost:9000/v1/audio/speech" \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world, this is a test of text-to-speech conversion",
    "voice": "en-US-AvaNeural", 
    "speed": 1.0,
    "provider": "openai-edge-tts"
  }'
```

### Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tts` | POST | Generate speech from text |
| `/voices/{provider}` | GET | List voices for specific provider |
| `/status` | GET | Check all service health status |
| `/health` | GET | Overall gateway health check |
| `/audio/{id}` | GET | Download cached audio file |
| `/play/{id}` | GET | Stream audio for inline playback |
| `/debug` | GET | Comprehensive debug information |

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root to customize the deployment:

```bash
# Basic Configuration
CORS_ORIGINS=*
REDIS_ENABLED=true
REDIS_URL=redis://redis:6379/1

# Cloud Storage Configuration (Optional)
S3_ENABLED=true
S3_ENDPOINT_URL=https://your-region.digitaloceanspaces.com
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_BUCKET_NAME=your-bucket-name
S3_REGION=your-region
PUBLIC_URL=https://tts.yourdomain.com
```

### Cloud Storage Setup

The TTS Gateway supports storing audio files in S3-compatible cloud storage:

1. **Create S3 Bucket**: Set up a bucket in AWS S3, DigitalOcean Spaces, or similar
2. **Configure CORS**: Allow access from your domain
3. **Set Environment Variables**: Update `.env` with your credentials
4. **Restart Services**: `docker-compose down && docker-compose up -d`

#### Example S3 CORS Configuration
```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET"],
    "AllowedOrigins": ["https://yourdomain.com"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

### Voice Configuration

Each provider has its own voice configuration:

- **Kokoro**: Uses `kokoro_voices.json` for voice definitions
- **Chatterbox**: Dynamically loads from reference audio files
- **OpenAI Edge TTS**: Uses Microsoft Edge TTS voice catalog

## 📦 Service Details

### 🎯 Kokoro ONNX (Port 9002)
- **High-quality neural TTS** with ONNX optimization
- **Multi-language support** (EN, JP, CN, ES, FR, etc.)
- **Grade A voices** with natural prosody
- **Fast inference** optimized for CPU/GPU
- **Automatic model downloading** on first run

### 🎪 Chatterbox TTS (Port 9001)
- **Voice cloning capabilities** with reference audio
- **Advanced neural models** with high-quality output
- **Reference audio support** for custom voices
- **CPU-optimized** for efficient generation
- **Hugging Face model integration**

### 🌐 OpenAI Edge TTS (Port 5050)
- **OpenAI API compatibility** for easy integration
- **Microsoft Edge TTS backend** with extensive voice catalog
- **Free voice synthesis** using system TTS
- **Multiple language support** with native speakers
- **High-quality neural voices**

### 🚪 TTS Gateway (Port 9000)
- **Unified API** for all TTS providers
- **Redis caching** for improved performance
- **Health monitoring** for all services
- **Error handling** with detailed responses
- **Audio format conversion** and optimization

### 🖥️ React Frontend (Port 3003)
- **Modern React 18** with TypeScript
- **Tailwind CSS** for responsive design
- **Real-time updates** and status monitoring
- **Audio controls** with inline playback
- **Mobile-responsive** interface

## 🔍 Health Monitoring

### Service Status Check
```bash
# Check all services
curl http://localhost:9000/status

# Individual service health
curl http://localhost:9002/health  # Kokoro
curl http://localhost:9001/health  # Chatterbox  
curl http://localhost:5050/v1/models  # OpenAI Edge TTS
```

### Debug Information
```bash
# Comprehensive debug info
curl http://localhost:9000/debug
```

This provides detailed information about:
- Service connectivity and latency
- Voice availability for each provider  
- Redis cache status
- Environment configuration
- Error diagnostics

## 🎯 Use Cases

- **Content Creation** - Generate voiceovers for videos and podcasts
- **Accessibility** - Convert text to speech for visually impaired users
- **Gaming** - Add dynamic voice synthesis to games and applications
- **Streaming** - Text-to-speech for live streams and broadcasts
- **Education** - Create audio content from written materials
- **Development** - Test and compare different TTS providers
- **Prototyping** - Quickly add voice capabilities to applications

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Adding New TTS Providers

1. Create service directory: `mkdir new-tts-service/`
2. Add Dockerfile and FastAPI application
3. Update `docker-compose.yml` with new service
4. Add provider support in `tts-gateway/app.py`
5. Update frontend provider list
6. Submit pull request

## 🔒 Security Considerations

Before making the repository public:
1. Ensure all sensitive credentials are in `.env` (not committed)
2. Review all API keys and secrets
3. Consider adding a SECURITY.md file
4. Enable GitHub's vulnerability scanning

## 📋 System Requirements
- **Docker** 20.10+
- **Docker Compose** 2.0+
- **4GB RAM**
- **2 CPU cores**
- **10GB disk space**

### Recommended for Production
- **8GB RAM** (or more for Chatterbox)
- **4 CPU cores**
- **20GB disk space**
- **SSD storage** for model files

## 🔒 Production Deployment

For production deployment with SSL and custom domains, see the detailed [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

Key production features:
- SSL/HTTPS support
- Rate limiting and security headers
- Health monitoring and alerting
- Backup and recovery procedures
- Performance optimization tips

## 🐛 Troubleshooting

### Common Issues

**Services not starting:**
```bash
# Check logs
docker-compose logs [service-name]

# Check resource usage
docker stats
```

**Audio not playing:**
```bash
# Check audio cache
curl http://localhost:9000/audio/[audio-id]

# Verify service connectivity
curl http://localhost:9000/debug
```

**High memory usage:**
- Chatterbox TTS requires significant memory for model loading
- Consider adjusting memory limits in `docker-compose.yml`
- Monitor with `docker stats`

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Kokoro ONNX](https://github.com/thewh1teagle/kokoro-onnx) - High-quality neural TTS with ONNX optimization
- [Chatterbox TTS](https://github.com/devnen/Chatterbox-TTS-Server) - Advanced neural TTS with voice cloning
- [OpenAI Edge TTS](https://github.com/isaacgounton/openai-edge-tts) - OpenAI-compatible Edge TTS wrapper
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://reactjs.org/) - Frontend user interface library
- [Docker](https://www.docker.com/) - Containerization platform

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=isaacgounton/awesome-tts&type=Date)](https://star-history.com/#isaacgounton/awesome-tts&Date)

---

**Made with ❤️ for the TTS community**

Found this useful? Please ⭐ star the repository and share it with others!
