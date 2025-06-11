# Contributing to Awesome-TTS

We love your input! We want to make contributing to Awesome-TTS as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Adding new TTS providers
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

## Pull Requests

Pull requests are the best way to propose changes to the codebase. We actively welcome your pull requests:

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

## Adding New TTS Providers

To add a new TTS provider to Awesome-TTS:

### 1. Create Service Directory
```bash
mkdir new-tts-provider/
cd new-tts-provider/
```

### 2. Create Required Files

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "app.py"]
```

**requirements.txt**:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic>=2.0.0
# Add your provider-specific dependencies
```

**app.py** (FastAPI application):
```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import io

app = FastAPI(
    title="Your TTS Service",
    description="Your TTS provider description",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "default"
    speed: Optional[float] = 1.0
    pitch: Optional[float] = 1.0
    format: Optional[str] = "wav"

class VoiceInfo(BaseModel):
    name: str
    gender: str
    locale: str
    engine: str
    description: str

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "your-tts"}

@app.get("/voices", response_model=List[VoiceInfo])
async def get_voices():
    # Return your available voices
    return []

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    # Implement your TTS logic here
    # Return StreamingResponse with audio data
    pass

@app.get("/")
async def root():
    return {
        "service": "Your TTS",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": {
            "tts": "/tts",
            "voices": "/voices",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 3. Update docker-compose.yml

Add your service to the docker-compose.yml file:

```yaml
  # Your TTS Service
  your-tts:
    build:
      context: ./your-tts-provider
      dockerfile: Dockerfile
    container_name: your-tts
    restart: unless-stopped
    ports:
      - "8005:8000"  # Use next available port
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

### 4. Update TTS Gateway

Add your provider to `tts-gateway/app.py`:

```python
# Add to SERVICES dict
SERVICES = {
    "kokoro": os.getenv("KOKORO_URL", "http://kokoro-onnx:8000"),
    "chatterbox": os.getenv("CHATTERBOX_URL", "http://chatterbox-tts:8000"),
    "edge": os.getenv("EDGE_TTS_URL", "http://openai-edge-tts:8000"),
    "streamlabs": os.getenv("STREAMLABS_URL", "http://streamlabs-tts:8000"),
    "your-provider": os.getenv("YOUR_TTS_URL", "http://your-tts:8000")
}

# Add to prepare_provider_request function
elif request.provider == "your-provider":
    if request.voice:
        base_request["voice"] = request.voice
    # Add any provider-specific parameters
    return base_request
```

### 5. Add Voice Configuration

Create `voices/your_provider_voices.json`:
```json
[
  {
    "name": "voice1",
    "gender": "female",
    "locale": "en-US",
    "engine": "your-provider",
    "description": "Voice 1 description"
  }
]
```

### 6. Update Documentation

- Update README.md to include your provider
- Add your provider to the supported providers table
- Update API documentation if needed

## Bug Reports

We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/yourusername/Awesome-TTS/issues).

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## Feature Requests

We welcome feature requests! Please:

1. Check if the feature already exists or is planned
2. Open an issue with the "enhancement" label
3. Describe the feature and why it would be useful
4. Provide examples of how it would work

## Code Style

### Python Code Style

- Follow PEP 8
- Use type hints where possible
- Add docstrings to functions and classes
- Keep functions small and focused
- Use meaningful variable names

### Docker Best Practices

- Use multi-stage builds when appropriate
- Minimize image size
- Use specific version tags
- Include health checks
- Set appropriate resource limits

### API Design

- Follow REST principles
- Use consistent naming conventions
- Include proper error handling
- Add comprehensive documentation
- Return appropriate HTTP status codes

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific service tests
pytest tests/test_kokoro.py

# Run with coverage
pytest --cov=. --cov-report=html
```

### Writing Tests

- Write tests for new features
- Test error conditions
- Include integration tests
- Test API endpoints
- Mock external dependencies

## Documentation

- Update README.md for new features
- Add docstrings to Python code
- Update API documentation
- Include examples in documentation
- Keep deployment guide current

## Release Process

1. Update version numbers
2. Update CHANGELOG.md
3. Create release notes
4. Tag the release
5. Update Docker images
6. Deploy to production

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

Examples of behavior that contributes to creating a positive environment include:

- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

### Enforcement

Project maintainers have the right and responsibility to remove, edit, or reject comments, commits, code, wiki edits, issues, and other contributions that are not aligned to this Code of Conduct.

## Questions?

Feel free to open an issue or contact the maintainers if you have any questions about contributing!
