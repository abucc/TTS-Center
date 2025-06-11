FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for Chatterbox TTS
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .

# Make sure pip is upgraded
RUN pip install --upgrade pip

# Install requirements with CPU-only PyTorch
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/models /app/cache /app/voices /app/reference_audio /app/outputs /app/logs

# Set environment variables
ENV MODELS_DIR=/app/models
ENV CACHE_DIR=/app/cache
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "app.py"]
