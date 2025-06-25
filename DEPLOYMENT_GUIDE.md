# 🚀 Awesome TTS - Production Deployment Guide

This guide covers deploying the Awesome TTS system to production environments using Docker Compose with proper SSL, monitoring, and optimization.

**Repository**: https://github.com/isaacgounton/awesome-tts

## 📋 Prerequisites

- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Domain name** configured with DNS
- **SSL certificates** for HTTPS
- **Minimum 8GB RAM** and 4 CPU cores
- **20GB+ disk space** for models and cache

## 🏗️ Architecture Overview

### With Coolify (Recommended)
```
Internet → Coolify Proxy → Individual Services
                          ├── Frontend (:3003)
                          ├── TTS Gateway (:9000) 
                          ├── Kokoro ONNX (:9002)
                          ├── Chatterbox TTS (:9001)
                          └── OpenAI Edge TTS (:5050)
```

### Manual Production (with Nginx)
```
Internet → Nginx/Reverse Proxy → TTS Gateway → Individual TTS Services
                                    :9000       ├── Kokoro ONNX (:9002)
                                               ├── Chatterbox TTS (:9001)  
                                               └── OpenAI Edge TTS (:5050)
                                               
Frontend (:3003) → API Proxy → TTS Gateway
                               └── Redis Cache
```

### Local Development
```
localhost:3003 (Frontend) → localhost:9000 (Gateway) → Individual Services
                                                       ├── localhost:9002 (Kokoro)
                                                       ├── localhost:9001 (Chatterbox)
                                                       └── localhost:5050 (OpenAI Edge)
```

## 🔧 Production Configuration

### 1. Environment Variables

Create a `.env` file for production settings:

```bash
# .env file for production
# Domain and SSL
DOMAIN=tts.yourdomain.com
SSL_CERT_PATH=./ssl/cert.pem
SSL_KEY_PATH=./ssl/key.pem

# Service URLs (internal Docker network)
KOKORO_URL=http://kokoro-onnx:9002
CHATTERBOX_URL=http://chatterbox-tts:9001
OPENAI_EDGE_TTS_URL=http://openai-edge-tts:5050

# Gateway configuration
TTS_GATEWAY_PORT=9000
CORS_ORIGINS=https://tts.yourdomain.com,https://yourdomain.com

# Redis configuration
REDIS_ENABLED=true
REDIS_URL=redis://redis:6379/1
REDIS_KEY_PREFIX=tts_prod_

# Frontend configuration
FRONTEND_PORT=3003
NODE_ENV=production

# API Keys (if required)
OPENAI_API_KEY=your_api_key_here

# Resource limits
CHATTERBOX_MEMORY_LIMIT=6g
KOKORO_MEMORY_LIMIT=4g
GATEWAY_MEMORY_LIMIT=1g
FRONTEND_MEMORY_LIMIT=512m
```

### 2. Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  # Redis Cache
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  # Kokoro ONNX TTS
  kokoro-onnx:
    build:
      context: ./kokoro-onnx
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - MODEL_PATH=/app/models
      - MAX_WORKERS=4
      - PORT=9002
    volumes:
      - ./models/kokoro:/app/models
      - ./cache:/app/cache
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9002/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s
    deploy:
      resources:
        limits:
          memory: ${KOKORO_MEMORY_LIMIT:-4g}
        reservations:
          memory: 2G

  # Chatterbox TTS Server
  chatterbox-tts:
    build:
      context: ./chatterbox-tts
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - HF_HOME=/app/hf_cache
      - TRANSFORMERS_CACHE=/app/hf_cache
      - HF_HUB_CACHE=/app/hf_cache
      - PORT=9001
      - CUDA_VISIBLE_DEVICES=-1  # CPU only for stability
    volumes:
      - ./models/chatterbox:/app/model_cache
      - ./cache:/app/cache
      - chatterbox_hf_cache:/app/hf_cache
      - ./chatterbox-tts/reference_audio:/app/reference_audio
      - ./chatterbox-tts/outputs:/app/outputs
      - ./chatterbox-tts/logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9001/health"]
      interval: 60s
      timeout: 30s
      retries: 5
      start_period: 900s  # 15 minutes for model download
    deploy:
      resources:
        limits:
          memory: ${CHATTERBOX_MEMORY_LIMIT:-6g}
        reservations:
          memory: 2G

  # OpenAI Edge TTS
  openai-edge-tts:
    build:
      context: ./openai-edge-tts
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - API_KEY=${OPENAI_API_KEY}
      - PORT=5050
      - DEFAULT_VOICE=en-US-AvaNeural
      - DEFAULT_RESPONSE_FORMAT=wav
      - DEFAULT_SPEED=1.0
      - DEFAULT_LANGUAGE=en
      - REQUIRE_API_KEY=false
      - REMOVE_FILTER=false
      - EXPAND_API=true
      - DETAILED_ERROR_LOGGING=true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5050/v1/models"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  # TTS Gateway (Main API)
  tts-gateway:
    build:
      context: ./tts-gateway
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - KOKORO_URL=${KOKORO_URL}
      - CHATTERBOX_URL=${CHATTERBOX_URL}
      - OPENAI_EDGE_TTS_URL=${OPENAI_EDGE_TTS_URL}
      - PORT=${TTS_GATEWAY_PORT:-9000}
      - CORS_ORIGINS=${CORS_ORIGINS}
      - REDIS_ENABLED=${REDIS_ENABLED:-true}
      - REDIS_URL=${REDIS_URL}
      - REDIS_KEY_PREFIX=${REDIS_KEY_PREFIX}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - redis
      - kokoro-onnx
      - chatterbox-tts
      - openai-edge-tts
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: ${GATEWAY_MEMORY_LIMIT:-1g}
        reservations:
          memory: 512M

  # React Frontend
  tts-frontend:
    build:
      context: ./tts-frontend
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - NODE_ENV=production
      - PORT=${FRONTEND_PORT:-3003}
    depends_on:
      - tts-gateway
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3003/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: ${FRONTEND_MEMORY_LIMIT:-512m}
        reservations:
          memory: 256M

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - tts-gateway
      - tts-frontend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  redis_data:
  chatterbox_hf_cache:

networks:
  default:
    name: tts-production
```

### 3. Nginx Configuration

Create `nginx/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;
    
    # Basic settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 10M;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript
               application/javascript application/xml+rss application/json;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=tts:10m rate=5r/s;
    
    # Upstream backends
    upstream tts_gateway {
        server tts-gateway:9000;
    }
    
    upstream tts_frontend {
        server tts-frontend:3003;
    }
    
    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name _;
        return 301 https://$host$request_uri;
    }
    
    # Main HTTPS server
    server {
        listen 443 ssl http2;
        server_name tts.yourdomain.com;
        
        # SSL configuration
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;
        
        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        
        # Frontend (React app)
        location / {
            proxy_pass http://tts_frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # API Gateway
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            rewrite ^/api/(.*)$ /$1 break;
            proxy_pass http://tts_gateway;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Increase timeouts for TTS generation
            proxy_connect_timeout 60s;
            proxy_send_timeout 1800s;
            proxy_read_timeout 1800s;
        }
        
        # TTS endpoint with special rate limiting
        location /api/tts {
            limit_req zone=tts burst=5 nodelay;
            
            rewrite ^/api/(.*)$ /$1 break;
            proxy_pass http://tts_gateway;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Extended timeouts for TTS generation
            proxy_connect_timeout 60s;
            proxy_send_timeout 1800s;
            proxy_read_timeout 1800s;
        }
        
        # Health check
        location /health {
            proxy_pass http://tts_gateway/health;
            proxy_set_header Host $host;
        }
    }
}
```

## 🚀 Deployment Steps

## Option A: Coolify Deployment (Recommended)

Coolify handles SSL, reverse proxy, and domain management automatically. Simply:

1. **Import Repository** in Coolify
2. **Set Environment Variables** in Coolify UI
3. **Deploy Each Service** with custom domains:
   - Frontend: `https://tts.yourdomain.com:3003`
   - Gateway: `https://tts.yourdomain.com:9000/api` 
   - Individual services (optional): separate subdomains

4. **Configure API Proxy** in Coolify to route `/api` to the gateway

**Benefits of Coolify:**
- ✅ Automatic SSL certificate management
- ✅ Built-in reverse proxy
- ✅ Easy domain configuration
- ✅ No nginx setup required
- ✅ Automatic deployments from Git

## Option B: Manual Production Deployment

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
```

### 2. SSL Certificate Setup

```bash
# Create SSL directory
mkdir -p nginx/ssl

# Option 1: Let's Encrypt (recommended)
sudo apt install certbot
sudo certbot certonly --standalone -d tts.yourdomain.com
sudo cp /etc/letsencrypt/live/tts.yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/tts.yourdomain.com/privkey.pem nginx/ssl/key.pem
sudo chown $USER:$USER nginx/ssl/*

# Option 2: Self-signed (development only)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=tts.yourdomain.com"
```

### 3. Directory Structure Setup

```bash
# Create required directories
mkdir -p {models/{kokoro,chatterbox},cache,logs/nginx,nginx/ssl}

# Set proper permissions
chmod 755 models cache logs
chmod 600 nginx/ssl/*
```

### 4. Configuration

```bash
# Copy and edit environment file
cp .env.example .env
nano .env  # Edit with your settings

# Update nginx configuration with your domain
sed -i 's/tts.yourdomain.com/your-actual-domain.com/g' nginx/nginx.conf
```

### 5. Deploy

```bash
# Build and start services
docker-compose -f docker-compose.prod.yml up -d

# Monitor startup
docker-compose -f docker-compose.prod.yml logs -f

# Check service status
docker-compose -f docker-compose.prod.yml ps
```

## 🔍 Monitoring and Health Checks

### Service Monitoring

```bash
# Check all service health
curl https://tts.yourdomain.com/api/status

# Check individual services
curl https://tts.yourdomain.com/api/health
curl https://tts.yourdomain.com/api/debug

# Monitor resource usage
docker stats

# View logs
docker-compose -f docker-compose.prod.yml logs [service_name]
```

### Automated Health Monitoring

Create `scripts/health-check.sh`:

```bash
#!/bin/bash
# Health check script for monitoring

DOMAIN="https://tts.yourdomain.com"
SERVICES=("kokoro" "chatterbox" "openai-edge-tts")

echo "=== TTS Health Check $(date) ==="

# Check gateway health
if curl -sf "$DOMAIN/api/health" > /dev/null; then
    echo "✅ Gateway: Healthy"
else
    echo "❌ Gateway: Unhealthy"
fi

# Check individual services
for service in "${SERVICES[@]}"; do
    if curl -sf "$DOMAIN/api/voices/$service" > /dev/null; then
        echo "✅ $service: Healthy"
    else
        echo "❌ $service: Unhealthy"
    fi
done

# Check disk space
df -h | grep -E "/$|/var"

# Check memory usage
free -h

echo "=========================="
```

Add to crontab:
```bash
# Add to crontab (crontab -e)
*/5 * * * * /path/to/scripts/health-check.sh >> /var/log/tts-health.log 2>&1
```

## 🔧 Performance Optimization

### 1. Resource Tuning

```yaml
# docker-compose.prod.yml optimizations
deploy:
  resources:
    limits:
      memory: 6g
      cpus: '2.0'
    reservations:
      memory: 2g
      cpus: '1.0'
```

### 2. Redis Optimization

```bash
# Redis performance tuning
echo 'vm.overcommit_memory = 1' >> /etc/sysctl.conf
echo never > /sys/kernel/mm/transparent_hugepage/enabled
```

### 3. Nginx Caching

Add to nginx.conf:
```nginx
# Static file caching
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# API response caching for non-TTS endpoints
location /api/voices/ {
    proxy_cache_valid 200 1h;
    add_header X-Cache-Status $upstream_cache_status;
}
```

## 🔒 Security Hardening

### 1. Firewall Configuration

```bash
# UFW firewall setup
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. Docker Security

```yaml
# Add to docker-compose.prod.yml
security_opt:
  - no-new-privileges:true
read_only: true
tmpfs:
  - /tmp
user: "1000:1000"  # Non-root user
```

### 3. SSL Security

```bash
# Generate strong DH parameters
openssl dhparam -out nginx/ssl/dhparam.pem 2048

# Add to nginx SSL configuration
ssl_dhparam /etc/nginx/ssl/dhparam.pem;
```

## 📊 Backup and Recovery

### Backup Script

Create `scripts/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups/tts/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup configurations
tar -czf "$BACKUP_DIR/config.tar.gz" docker-compose.prod.yml .env nginx/

# Backup models (if modified)
tar -czf "$BACKUP_DIR/models.tar.gz" models/

# Backup Redis data
docker-compose -f docker-compose.prod.yml exec redis redis-cli BGSAVE
docker cp $(docker-compose -f docker-compose.prod.yml ps -q redis):/data/dump.rdb "$BACKUP_DIR/"

# Cleanup old backups (keep 7 days)
find /backups/tts -type d -mtime +7 -exec rm -rf {} +

echo "Backup completed: $BACKUP_DIR"
```

### Recovery Procedure

```bash
# Stop services
docker-compose -f docker-compose.prod.yml down

# Restore configurations
tar -xzf backup/config.tar.gz

# Restore models
tar -xzf backup/models.tar.gz

# Restore Redis data
docker-compose -f docker-compose.prod.yml up -d redis
docker cp backup/dump.rdb $(docker-compose -f docker-compose.prod.yml ps -q redis):/data/
docker-compose -f docker-compose.prod.yml restart redis

# Start all services
docker-compose -f docker-compose.prod.yml up -d
```

## 🚨 Troubleshooting

### Common Issues

**High Memory Usage:**
```bash
# Check memory usage
docker stats --no-stream

# Restart memory-heavy services
docker-compose -f docker-compose.prod.yml restart chatterbox-tts
```

**SSL Certificate Issues:**
```bash
# Check certificate validity
openssl x509 -in nginx/ssl/cert.pem -text -noout

# Test SSL
curl -I https://tts.yourdomain.com
```

**Service Connection Issues:**
```bash
# Test internal connectivity
docker-compose -f docker-compose.prod.yml exec tts-gateway curl http://kokoro-onnx:9002/health

# Check network
docker network ls
docker network inspect tts-production
```

**Database/Cache Issues:**
```bash
# Check Redis
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping

# Clear cache if needed
docker-compose -f docker-compose.prod.yml exec redis redis-cli FLUSHDB
```

## 📈 Scaling for High Traffic

### Horizontal Scaling

```yaml
# docker-compose.scale.yml
services:
  kokoro-onnx:
    deploy:
      replicas: 3
  
  tts-gateway:
    deploy:
      replicas: 2
```

### Load Balancer Configuration

```nginx
# Multiple gateway instances
upstream tts_gateway {
    least_conn;
    server tts-gateway-1:9000;
    server tts-gateway-2:9000;
}

# Multiple Kokoro instances  
upstream kokoro_pool {
    server kokoro-onnx-1:9002;
    server kokoro-onnx-2:9002;
    server kokoro-onnx-3:9002;
}
```

## 🎯 Production Checklist

- [ ] SSL certificates installed and auto-renewal configured
- [ ] Domain DNS configured correctly
- [ ] All services starting and healthy
- [ ] Health monitoring active
- [ ] Rate limiting configured
- [ ] Security headers enabled
- [ ] Firewall configured
- [ ] Backup system active
- [ ] Log rotation configured
- [ ] Resource monitoring setup
- [ ] Error alerting configured
- [ ] Documentation updated

## 🆘 Emergency Procedures

### Quick Recovery

```bash
# Emergency restart
docker-compose -f docker-compose.prod.yml restart

# Emergency stop
docker-compose -f docker-compose.prod.yml down

# Emergency logs
docker-compose -f docker-compose.prod.yml logs --tail=100 -f
```

### Contact Information

For critical issues:
- System Admin: isaac@etugrand.com
- On-call Engineer: +1-438-454-1235
- Status Page: https://status.etugrand.com

---

🎉 **Production Deployment Complete!** Your Awesome TTS system is now running securely at https://tts.yourdomain.com with full monitoring, caching, and high availability.
