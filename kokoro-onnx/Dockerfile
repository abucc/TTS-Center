FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including cmake for ONNX compilation
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    cmake \
    pkg-config \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .

# Upgrade pip and install wheel for faster builds
RUN pip install --upgrade pip wheel setuptools

# Install ONNX with pre-built wheel first (avoiding compilation)
RUN pip install --no-cache-dir --only-binary=onnx onnx

# Install remaining requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create models and voices directories
RUN mkdir -p /app/models /app/voices

# Copy voices JSON file
COPY ../voices/kokoro_voices.json /app/voices/

# Download required voices file
RUN curl -L -o /app/voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "app.py"]
