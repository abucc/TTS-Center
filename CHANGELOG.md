# Changelog

All notable changes to Awesome-TTS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-06-11

### Added
- Initial release of Awesome-TTS unified gateway
- Support for 5 TTS providers:
  - Kokoro ONNX - High-quality neural TTS
  - ChatterboxTTS - Streamlabs/Polly backend
  - OpenAI Edge TTS - OpenAI-compatible API
  - Edge TTS - Microsoft Edge TTS
  - Streamlabs TTS - Direct Streamlabs API
- Unified web interface for all TTS providers
- REST API with consistent endpoints
- Redis caching for improved performance
- Docker Compose deployment
- Nginx reverse proxy with SSL support
- Health monitoring and status endpoints
- Rate limiting and security features
- Comprehensive voice management
- Production-ready configuration
- Complete documentation and deployment guide

### Features
- **Multi-provider Support**: Access 5 different TTS engines through one interface
- **Web Interface**: Easy-to-use web UI for testing and demos
- **REST API**: Consistent API across all providers
- **Caching**: Redis-based caching for faster responses
- **Monitoring**: Health checks and service status endpoints
- **Security**: SSL, rate limiting, and CORS protection
- **Scalability**: Docker-based architecture for easy scaling
- **Documentation**: Comprehensive guides and API documentation

### Technical Details
- FastAPI-based microservices architecture
- Docker containerization for all services
- Nginx reverse proxy with SSL termination
- Redis for caching and session management
- Health checks and auto-restart capabilities
- Resource limits and monitoring
- Production-ready configuration

## [Unreleased]

### Planned
- Additional TTS providers
- Batch processing capabilities
- Audio format conversion
- Voice cloning support
- Real-time streaming
- Advanced caching strategies
- Metrics and analytics
- Multi-language support improvements
