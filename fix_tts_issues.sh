#!/bin/bash

echo "🔧 Fixing TTS Issues..."

# Stop all services
echo "Stopping all services..."
docker-compose down

# Remove any problematic containers and volumes
echo "Cleaning up containers and networks..."
docker-compose rm -f
docker system prune -f

# Clear Redis data to fix caching issues
echo "Clearing Redis cache..."
docker volume rm awesome-tts_redis_data 2>/dev/null || true

# Rebuild services that have been modified
echo "Rebuilding modified services..."
docker-compose build --no-cache tts-gateway tts-frontend chatterbox-tts

# Start services in the correct order
echo "Starting services..."
docker-compose up -d redis
sleep 5

docker-compose up -d kokoro-onnx openai-edge-tts chatterbox-tts
sleep 10

docker-compose up -d tts-gateway
sleep 5

docker-compose up -d tts-frontend

echo "🚀 Services starting up..."
echo ""
echo "Check status with: docker-compose ps"
echo "View logs with: docker-compose logs -f [service-name]"
echo ""
echo "Frontend will be available at: http://localhost:3003"
echo "Gateway API at: http://localhost:9000"
echo "Chatterbox TTS at: http://localhost:9001"
echo ""
echo "Wait 2-3 minutes for all services to fully initialize before testing."