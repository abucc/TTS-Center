# TTS Center

[中文 README](README.md)

TTS Center is a NAS-hosted voice hub built from Awesome-TTS and adapted for Hermes, OpenClaw, and other local AI agents.

## 1. What This Project Does

TTS Center provides one stable API and one Chinese admin UI for voice generation, voice asset management, fallback routing, and per-voice style rules.

Core flow:

1. Caller sends text to `/tts`.
2. Voice Hub applies the selected `voice` configuration.
3. Local Qwen3-TTS is used first.
4. If local Qwen fails, Voice Hub falls back to the configured provider.
5. Generated audio is returned through a playable URL and recorded in history.

## 2. Current Services

- Admin UI: `http://192.168.31.180:3003`
- API base: `http://192.168.31.180:9000`
- Swagger: `http://192.168.31.180:9000/docs`
- Local Qwen bridge: `http://192.168.31.167:7861`
- Qwen3-TTS WebUI: `http://192.168.31.167:7860`

## 3. Features

- Local-first TTS chain: Qwen3-TTS first, fallback provider second.
- Fallback providers: Aliyun TTS and Xiaomi MiMo voice clone.
- NAS-based voice assets and configuration.
- Upload source audio from the admin UI.
- Clip and process reference audio.
- Save voice definitions and reference text.
- Per-voice style rules: common words, forbidden words, replacements, prefix, and sentence length.
- Smart text splitting with pause-aware chunking.
- Qwen start, stop, and GPU reload controls from the admin UI.
- GPU status display: service status, loaded model status, and memory usage.
- Recent generation history with playable audio.
- Documentation for human users and AI agents.

## 4. Documentation

- User guide: [docs/VOICE_HUB_USAGE.md](docs/VOICE_HUB_USAGE.md)
- API reference: [docs/VOICE_HUB_API.md](docs/VOICE_HUB_API.md)
- Hermes integration: [docs/HERMES_TTS_CONFIG.md](docs/HERMES_TTS_CONFIG.md)
- AI handoff: [docs/AI_TTS_HANDOFF.md](docs/AI_TTS_HANDOFF.md)

## 5. Data Layout

Voice Hub is deployed on NAS Docker and stores persistent data under `/opt/data/voice-hub`.

```text
/opt/data/voice-hub/
  voices/                       uploaded source audio
  voices/processed/             processed reference audio
  config/voices.json            voice definitions
  config/voice-styles.json      voice style settings
  config/voice-routing.json     fallback routing
```

The local Windows Qwen bridge is compute-only. It reads NAS audio through Voice Hub URLs.

## 6. Quick API Example

```bash
curl -X POST "http://192.168.31.180:9000/tts" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "local-first",
    "voice": "栗子",
    "text": "哥哥，你好，我是栗子，听听我现在的声音怎么样？",
    "format": "wav",
    "cache": false
  }'
```

Response fields:

- `actual_provider`: actual provider used, such as `qwen-local`, `aliyun-zhimi`, or `mimo-voiceclone`.
- `duration`: real audio duration in milliseconds.
- `generation_duration`: generation time in milliseconds.
- `audio_url`: relative audio playback URL.

## 7. Admin Workflow

1. Open the admin UI.
2. Upload authorized source audio.
3. Select the source audio and clip a clean reference segment.
4. Transcribe or manually enter reference text.
5. Save the voice and style settings together.
6. Test generation.
7. Let Hermes/OpenClaw call `/tts` with the selected `voice`.

## 8. Local Qwen Controls

The admin UI has a Local Qwen card:

- Gray light: PC, network, or bridge is unreachable.
- Red light: bridge is online, but Qwen3-TTS is not running.
- Green light: Qwen3-TTS is running.
- Start: starts Qwen3-TTS silently.
- Stop: stops Qwen3-TTS and frees GPU memory.
- Reload GPU: loads the model into GPU memory.

The bridge starts Qwen with hidden Windows subprocess settings to avoid visible Python console windows.

## 9. Deployment

NAS deployment path:

```bash
cd /volume1/docker/voice-hub
docker compose up -d --build voice-hub-gateway voice-hub-frontend
```

Check status:

```bash
docker compose ps
docker compose logs -f voice-hub-gateway
docker compose logs -f voice-hub-frontend
```

## 10. Environment Variables

Important variables:

```text
AUTH_USERNAME=admin
AUTH_PASSWORD=change-me
SESSION_SECRET=change-this-session-secret
QWEN_URL=http://192.168.31.167:7861
VOICE_HUB_DATA_DIR=/opt/data/voice-hub
VOICE_HUB_DOCS_DIR=/app/docs
ALIYUN_TTS_COMMAND=/usr/local/bin/python /opt/data/skills/aliyun-tts/scripts/aliyun_tts.py {text_file} {output_path} --voice {voice} --format {format}
MIMO_API_KEY=
MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
MIMO_MODEL=mimo-v2.5-tts-voiceclone
MIMO_AUTH_HEADER=auto
```

Do not commit real `.env` files, API keys, tokens, uploaded audio, generated audio, or private runtime data.

## 11. Agent Rules

```text
Use POST http://192.168.31.180:9000/tts for TTS.
Set provider=local-first, voice=<configured voice ID>, text=<raw text>.
Do not manually prepend style prompts.
To edit voice style, GET /voice-admin/styles first, update only your own voice entry, then POST the full styles object back.
```

## 12. Upstream

This project started from Awesome-TTS and has been adapted into a NAS voice center workflow.

Original upstream:

```text
https://github.com/isaacgounton/awesome-tts
```

The legacy upstream submodules `chatterbox-tts` and `openai-edge-tts` are not used by the current Voice Hub main path and have been removed from this repository.

## 13. License

This repository keeps the upstream MIT license unless a file states otherwise.
