# Changelog

All notable changes to the Awesome TTS project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-13

### 🎉 Initial Release

#### Added
- **Multi-Provider TTS Gateway** with unified API
  - Kokoro ONNX TTS service (port 9002)
  - Chatterbox TTS service (port 9001)
  - OpenAI Edge TTS service (port 5050)
  - Unified TTS Gateway (port 9000)
  
- **Modern React Frontend** (port 3003)
  - Real-time provider selection and voice switching
  - Audio controls with speed/pitch adjustment
  - Inline audio playback and download
  - Service status monitoring dashboard
  - Mobile-responsive design with Tailwind CSS

- **Production-Ready Features**
  - Redis caching for improved performance
  - Health monitoring for all services
  - Comprehensive error handling
  - Audio format support (WAV/MP3)
  - CORS configuration for web integration

- **Docker Compose Deployment**
  - Multi-service orchestration
  - Health checks for all services
  - Volume management for models and cache
  - Resource limits and optimization
  - Production deployment configuration

#### TTS Providers

##### Kokoro ONNX (Port 9002)
- High-quality neural TTS with ONNX optimization
- Multi-language support (EN, JP, CN, ES, FR, etc.)
- Grade A voices with natural prosody
- Automatic model downloading
- CPU/GPU optimized inference

##### Chatterbox TTS (Port 9001)
- Voice cloning capabilities with reference audio
- Advanced neural models
- CPU-optimized for efficient generation
- Hugging Face model integration
- Custom voice support

##### OpenAI Edge TTS (Port 5050)
- OpenAI API compatibility
- Microsoft Edge TTS backend
- Extensive voice catalog
- Multiple language support
- Free voice synthesis

#### API Features
- **Unified TTS Endpoint**: `POST /tts`
- **Voice Discovery**: `GET /voices/{provider}`
- **Health Monitoring**: `GET /status`, `GET /health`
- **Debug Information**: `GET /debug`
- **Audio Serving**: `GET /audio/{id}`, `GET /play/{id}`

#### Frontend Features
- **Provider Selection**: Dynamic switching between TTS providers
- **Voice Controls**: Speed (0.5x-2.0x), Pitch (0.5x-2.0x), Format selection
- **Audio Management**: Inline player, download, play buttons
- **Real-time Monitoring**: Service status with latency display
- **Error Handling**: Detailed error messages and troubleshooting

#### Deployment & Operations
- **Docker Compose**: Complete multi-service deployment
- **Health Checks**: Automated service monitoring
- **Caching**: Redis-based audio caching
- **Logging**: Comprehensive logging across all services
- **Resource Management**: Memory and CPU limits

#### Documentation
- **README.md**: Complete project overview and quick start
- **DEPLOYMENT_GUIDE.md**: Production deployment guide
- **CONTRIBUTING.md**: Contribution guidelines
- **API Documentation**: Built-in FastAPI documentation

#### Configuration
- **Environment Variables**: Comprehensive configuration options
- **Service URLs**: Configurable internal service communication
- **CORS Settings**: Flexible cross-origin configuration
- **Cache Settings**: Redis configuration and TTL management

### 🏗️ Architecture

```
Frontend (React) → TTS Gateway → Individual TTS Services → Redis Cache
    :3003             :9000         ├── Kokoro ONNX (9002)
                                   ├── Chatterbox TTS (9001)
                                   └── OpenAI Edge TTS (5050)
```

### 📊 Technical Specifications

#### System Requirements
- **Minimum**: 4GB RAM, 2 CPU cores, 10GB disk
- **Recommended**: 8GB RAM, 4 CPU cores, 20GB disk
- **Docker**: 20.10+, Docker Compose 2.0+

#### Supported Audio Formats
- **Input**: Text (UTF-8)
- **Output**: WAV, MP3
- **Quality**: 16-bit, 22kHz (default)

#### Performance Metrics
- **Kokoro ONNX**: ~2-5 seconds for typical sentences
- **Chatterbox TTS**: ~5-15 seconds for typical sentences
- **OpenAI Edge TTS**: ~1-3 seconds for typical sentences
- **Cache Hit Rate**: ~80-90% for repeated requests

### 🔧 Configuration Options

#### Environment Variables
```bash
# Service URLs
KOKORO_URL=http://kokoro-onnx:9002
CHATTERBOX_URL=http://chatterbox-tts:9001
OPENAI_EDGE_TTS_URL=http://openai-edge-tts:5050

# Gateway Configuration
PORT=9000
CORS_ORIGINS=*
REDIS_ENABLED=true
REDIS_URL=redis://redis:6379/1

# API Keys
OPENAI_API_KEY=your_key_here
```

#### Service Ports
- **Frontend**: 3003
- **TTS Gateway**: 9000
- **Kokoro ONNX**: 9002
- **Chatterbox TTS**: 9001
- **OpenAI Edge TTS**: 5050

### 🚀 Quick Start Commands

```bash
# Clone and setup
git clone https://github.com/yourusername/awesome-tts.git
cd awesome-tts
mkdir -p models/kokoro models/chatterbox cache

# Start all services
docker-compose up -d

# Access the application
# Web Interface: http://localhost:3003
# API Gateway: http://localhost:9000
# Service Status: http://localhost:9000/status
```

### 🎯 Use Cases

- **Content Creation**: Video voiceovers and podcasts
- **Accessibility**: Text-to-speech for visually impaired users
- **Gaming**: Dynamic voice synthesis for games
- **Streaming**: Live stream text-to-speech
- **Education**: Audio content generation
- **Development**: TTS provider testing and comparison

### 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Adding new TTS providers
- Improving existing services
- Frontend enhancements
- Documentation updates

### 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE).

---

## Release Notes

### What's New in v1.0.0

🎤 **First stable release** of Awesome TTS with a complete multi-provider architecture!

**Key Highlights:**
- **3 High-Quality TTS Providers** unified in a single system
- **Modern React Frontend** with real-time controls
- **Production-Ready Deployment** with Docker Compose
- **Comprehensive Documentation** and deployment guides

**Getting Started:**
1. Clone the repository
2. Run `docker-compose up -d`
3. Access http://localhost:3003 for the web interface

**For Production:**
See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for SSL, monitoring, and scaling.

---

*Made with ❤️ for the TTS community*
