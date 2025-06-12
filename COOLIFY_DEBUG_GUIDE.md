# Debugging TTS Issues in Coolify Deployment

Since your app is running in Coolify, here's how to debug the issues:

## 1. Check Debug Endpoint (After applying fixes)

Once you apply the fixes and redeploy, you can access:
```
https://your-domain.com/debug
```

This will show:
- ✅ Service health status
- ✅ Response times
- ✅ Voice availability
- ✅ Redis connection status
- ✅ Error details

## 2. Current Issue Analysis

Based on your description:
- **File downloaded**: `speech.wav` (144 bytes, JSON content)
- **Problem**: Gateway is returning JSON error instead of audio

## 3. Manual API Testing (Current Deployment)

Test the current API endpoints:

### Check Gateway Health:
```bash
curl https://your-domain.com/health
```

### Check Service Status:
```bash
curl https://your-domain.com/status
```

### Test Voice Endpoints:
```bash
# Kokoro voices
curl https://your-domain.com/voices/kokoro

# Chatterbox voices  
curl https://your-domain.com/voices/chatterbox

# OpenAI Edge TTS voices
curl https://your-domain.com/voices/openai-edge-tts
```

### Test TTS Generation:
```bash
curl -X POST https://your-domain.com/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world test",
    "provider": "kokoro",
    "speed": 1.0,
    "format": "wav"
  }'
```

## 4. What You'll Likely Find:

The JSON response you're getting probably contains:
```json
{
  "success": false,
  "provider": "kokoro",
  "error": "Cannot connect to kokoro service"
}
```

## 5. Common Issues in Coolify:

1. **Service Discovery**: Services might not be able to reach each other
2. **Port Configuration**: Internal ports might not match docker-compose
3. **Environment Variables**: Service URLs might be wrong for Coolify
4. **Resource Limits**: Services might be crashing due to memory limits

## 6. Coolify-Specific Fixes Needed:

You may need to update the service URLs in your deployment environment:

Instead of:
```
KOKORO_URL=http://kokoro-onnx:8000
CHATTERBOX_URL=http://chatterbox-tts:8000
OPENAI_EDGE_TTS_URL=http://openai-edge-tts:5050
```

You might need Coolify-specific internal URLs (check your Coolify dashboard).

## 7. Quick Test Without Fixes:

To see what the current JSON error is, download the "speech.wav" file and open it in a text editor. It will show you the actual error message.

## 8. After Applying Fixes:

1. **Redeploy** in Coolify
2. **Test** the `/debug` endpoint
3. **Check** individual service health
4. **Verify** voice endpoints work
5. **Test** TTS generation

The fixes I provided will:
- ✅ Improve error handling so you see real errors instead of broken downloads
- ✅ Fix service communication issues
- ✅ Ensure proper audio serving
- ✅ Add comprehensive debugging information