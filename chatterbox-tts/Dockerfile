FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV HF_HOME=/app/hf_cache

WORKDIR /app

# Install system dependencies including CMake for ONNX compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libsndfile1 \
    ffmpeg \
    python3-dev \
    git \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Upgrade pip and install ONNX first to ensure precompiled wheels are used
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "onnx>=1.15.0,<2.0.0" "onnxruntime>=1.16.0,<2.0.0" && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create required directories for the application
RUN mkdir -p /app/models /app/cache /app/voices /app/reference_audio /app/outputs /app/logs /app/hf_cache

# Set environment variables for the app
ENV MODELS_DIR=/app/models
ENV CACHE_DIR=/app/cache

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "app.py"]
