# 🎤 Unified TTS Gateway - Deployment Guide

This guide will help you deploy your unified TTS application that includes **Kokoro ONNX**, **ChatterboxTTS**, **OpenAI Edge TTS**, **Edge TTS (Microsoft)**, and **Streamlabs TTS** as a single application accessible at `tts.dahopevi.com`.

## 📋 Prerequisites

- Docker and Docker Compose installed
- Domain name configured (tts.dahopevi.com)
- SSL certificates for HTTPS
- At least 8GB RAM and 4 CPU cores recommended

## 🏗️ Architecture Overview

```
Internet → Nginx (SSL Termination) → TTS Gateway → Individual TTS Services
                                                  ├── Kokoro ONNX
                                                  ├── ChatterboxTTS  
                                                  ├── OpenAI Edge TTS
                                                  ├── Streamlabs TTS
                                                  └── Redis (Caching)
```

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Navigate to your project directory
cd /path/to/your/tts/project

# Create required directories
mkdir -p models/kokoro models/chatterbox cache nginx/ssl web
```

### 2. SSL Certificate Setup

Place your SSL certificates in the `nginx/ssl/` directory:
```bash
# Your SSL certificate files
nginx/ssl/tts.dahopevi.com.crt
nginx/ssl/tts.dahopevi.com.key
```

**For Let's Encrypt certificates:**
```bash
# Copy from Let's Encrypt
sudo cp /etc/letsencrypt/live/tts.dahopevi.com/fullchain.pem nginx/ssl/tts.dahopevi.com.crt
sudo cp /etc/letsencrypt/live/tts.dahopevi.com/privkey.pem nginx/ssl/tts.dahopevi.com.key
sudo chown $USER:$USER nginx/ssl/*
```

### 3. Download Kokoro Models

The Kokoro models will be automatically downloaded when the container starts, but you can pre-download them:

```bash
mkdir -p models/kokoro
cd models/kokoro

# Download Kokoro v1.0 models
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

cd ../..
```

### 4. Deploy the Services

```bash
# Build and start all services
docker-compose up -d

# Monitor the logs
docker-compose logs -f

# Check service status
docker-compose ps
```

## 🔧 Configuration

### Environment Variables

You can customize the deployment by setting environment variables in the `docker-compose.yml` file:

```yaml
environment:
  - KOKORO_URL=http://kokoro-onnx:8000
  - CHATTERBOX_URL=http://chatterbox-tts:8000
  - EDGE_TTS_URL=http://openai-edge-tts:8000
  - STREAMLABS_URL=http://streamlabs-tts:8000
  - CORS_ORIGINS=*
```

### Service Ports

- **Gateway**: 8000 (main entry point)
- **Kokoro ONNX**: 8001
- **ChatterboxTTS**: 8002
- **OpenAI Edge TTS**: 8003
- **Streamlabs TTS**: 8004
- **Nginx**: 80 (HTTP), 443 (HTTPS)
- **Redis**: 6379

## 🌐 Access Points

Once deployed, you can access the services at:

### Web Interface
- **Main Interface**: https://tts.dahopevi.com
- **Service Status**: https://tts.dahopevi.com/status

### API Endpoints
- **Unified TTS**: `POST https://tts.dahopevi.com/tts`
- **Voice Lists**: `GET https://tts.dahopevi.com/voices/{provider}`
- **Health Check**: `GET https://tts.dahopevi.com/health`

### Direct Service Access (Optional)
- **Kokoro**: https://tts.dahopevi.com/kokoro/
- **ChatterboxTTS**: https://tts.dahopevi.com/chatterbox/
- **Edge TTS**: https://tts.dahopevi.com/edge/
- **Streamlabs**: https://tts.dahopevi.com/streamlabs/

## 📝 API Usage Examples

### Using the Unified API

```bash
# Basic TTS request
curl -X POST https://tts.dahopevi.com/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test of the unified TTS gateway!",
    "provider": "kokoro",
    "voice": "af_heart",
    "speed": 1.0,
    "pitch": 1.0,
    "format": "wav"
  }' \
  --output speech.wav

# Get available voices for a provider
curl https://tts.dahopevi.com/voices/kokoro

# Check service status
curl https://tts.dahopevi.com/status
```

### Python Example

```python
import requests

# TTS request
response = requests.post('https://tts.dahopevi.com/tts', json={
    "text": "Hello world!",
    "provider": "edge",
    "voice": "alloy",
    "speed": 1.2
})

if response.status_code == 200:
    result = response.json()
    if result['success']:
        print(f"TTS generated in {result['duration']}ms")
        # Download audio from result['audio_url']
    else:
        print(f"Error: {result['error']}")
```

## 🔍 Monitoring and Troubleshooting

### Check Service Health

```bash
# Overall health
curl https://tts.dahopevi.com/health

# Individual service status
curl https://tts.dahopevi.com/status

# Docker container status
docker-compose ps

# View logs
docker-compose logs tts-gateway
docker-compose logs kokoro-onnx
docker-compose logs chatterbox-tts
docker-compose logs openai-edge-tts
docker-compose logs streamlabs-tts
```

### Common Issues

#### 1. SSL Certificate Issues
```bash
# Check certificate validity
openssl x509 -in nginx/ssl/tts.dahopevi.com.crt -text -noout

# Test SSL configuration
curl -I https://tts.dahopevi.com
```

#### 2. Model Download Issues
```bash
# Check Kokoro model files
ls -la models/kokoro/
docker-compose exec kokoro-onnx ls -la /app/models/
```

#### 3. Service Connection Issues
```bash
# Test internal connectivity
docker-compose exec tts-gateway curl http://kokoro-onnx:8000/health
docker-compose exec tts-gateway curl http://chatterbox-tts:8000/health
```

#### 4. Memory Issues
```bash
# Check resource usage
docker stats

# Adjust memory limits in docker-compose.yml if needed
```

## 🔧 Maintenance

### Updating Services

```bash
# Pull latest changes
git pull

# Rebuild and restart services
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Backup and Recovery

```bash
# Backup voice configurations
tar -czf voices-backup.tar.gz voices/

# Backup Redis data (if needed)
docker-compose exec redis redis-cli BGSAVE

# Backup models
tar -czf models-backup.tar.gz models/
```

### Log Rotation

Add to your crontab:
```bash
# Rotate Docker logs weekly
0 0 * * 0 docker system prune -f
```

## 🎛️ Customization

### Adding New TTS Providers

1. Create a new service directory (e.g., `new-tts-service/`)
2. Add Dockerfile and app.py following the existing pattern
3. Update `docker-compose.yml` to include the new service
4. Update `tts-gateway/app.py` to add the new provider
5. Add voice configuration in `voices/new_service_voices.json`

### Custom Voice Configurations

Edit the voice JSON files in the `voices/` directory:
- `kokoro_voices.json` - Kokoro voice definitions
- `edge_tts_voices.json` - Edge TTS voices
- `openai_edge_tts_voices.json` - OpenAI-style voices
- `streamlabs_voices.json` - Streamlabs voices

## 🔒 Security Considerations

1. **Rate Limiting**: Already configured in Nginx
2. **CORS**: Configure appropriate origins in environment variables
3. **SSL**: Always use HTTPS in production
4. **Firewall**: Only expose necessary ports (80, 443)
5. **Updates**: Keep Docker images and dependencies updated

## 📊 Performance Optimization

### For High Load

1. **Scale Services**:
```yaml
deploy:
  replicas: 3  # Add to docker-compose.yml
```

2. **Use Load Balancer**:
```yaml
# Add multiple instances in nginx upstream
upstream kokoro_direct {
    server kokoro-onnx-1:8000;
    server kokoro-onnx-2:8000;
    server kokoro-onnx-3:8000;
}
```

3. **Optimize Caching**:
- Increase Redis memory
- Adjust cache TTL values
- Use CDN for static assets

### Resource Monitoring

```bash
# Monitor resource usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Set up monitoring with Prometheus/Grafana (optional)
```

## 🎯 Production Checklist

- [ ] SSL certificates installed and valid
- [ ] Domain DNS configured correctly
- [ ] All services starting successfully
- [ ] Health checks passing
- [ ] Rate limiting configured
- [ ] Backups configured
- [ ] Monitoring set up
- [ ] Security headers configured
- [ ] CORS properly configured
- [ ] Log rotation configured

## 🆘 Support

If you encounter issues:

1. Check the logs: `docker-compose logs`
2. Verify service health: `curl https://tts.dahopevi.com/status`
3. Test individual services directly
4. Check resource usage: `docker stats`
5. Verify network connectivity between containers

For additional help, check the individual service documentation:
- [Kokoro ONNX](https://github.com/thewh1teagle/kokoro-onnx)
- [ChatterboxTTS](https://github.com/devnen/Chatterbox-TTS-Server)
- [OpenAI Edge TTS](https://github.com/isaacgounton/openai-edge-tts)

---

🎉 **Congratulations!** Your unified TTS gateway should now be running at https://tts.dahopevi.com with all five TTS providers available through a single interface!
