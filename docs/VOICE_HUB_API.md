# Voice Hub API 文档 / API Reference

## 1. 基础信息 / Base Info

- API base: `http://192.168.31.180:9000`
- Admin UI: `http://192.168.31.180:3003`
- Swagger: `http://192.168.31.180:9000/docs`

所有音频与配置都以 NAS 为准。All persistent audio and configuration live on NAS.

```text
/opt/data/voice-hub/
  voices/
  voices/processed/
  config/voices.json
  config/voice-styles.json
  config/voice-routing.json
```

## 2. 生成语音 / Generate TTS

```bash
curl -X POST "http://192.168.31.180:9000/tts" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "local-first",
    "voice": "栗子",
    "text": "哥哥，我已经收到啦。",
    "format": "wav",
    "cache": false
  }'
```

Request fields:

- `provider`: usually `local-first`.
- `voice`: voice ID configured in the admin UI.
- `text`: raw text to speak.
- `format`: usually `wav`.
- `cache`: set `false` for fresh generation.

Response:

```json
{
  "success": true,
  "provider": "local-first",
  "actual_provider": "qwen-local",
  "duration": 22100,
  "generation_duration": 5300,
  "audio_url": "/audio/xxxx",
  "history_id": "xxxx"
}
```

- `duration`: 真实音频时长，单位毫秒。Real audio duration in milliseconds.
- `generation_duration`: 生成耗时，单位毫秒。Generation time in milliseconds.
- `audio_url`: 相对地址。Full URL is `http://192.168.31.180:9000/audio/xxxx`.

## 3. 上传参考音频 / Upload Source Audio

```bash
curl -X POST "http://192.168.31.180:9000/voice-admin/upload" \
  -F "file=@/path/to/audio.wav"
```

Supported formats: `wav`, `mp3`, `m4a`, `flac`, `ogg`, `aac`, `webm`.

## 4. 获取音频列表 / List Audio Files

```bash
curl "http://192.168.31.180:9000/voice-admin/files"
```

只列出 `voices/` 根目录下的源音频，不列出 `voices/processed/`。

Only source audio under `voices/` is listed. Processed files under `voices/processed/` are hidden from this list.

## 5. 清洗裁剪 / Process Audio

```bash
curl -X POST "http://192.168.31.180:9000/voice-admin/process" \
  -H "Content-Type: application/json" \
  -d '{
    "source_audio": "/opt/data/voice-hub/voices/lizi.mp3",
    "id": "栗子",
    "start": 0,
    "duration": 15
  }'
```

Response:

```json
{
  "reference_audio": "/opt/data/voice-hub/voices/processed/栗子.wav"
}
```

## 6. 自动识别参考文本 / Transcribe Reference Text

```bash
curl -X POST "http://192.168.31.180:9000/voice-admin/transcribe" \
  -H "Content-Type: application/json" \
  -d '{"audio_path":"/opt/data/voice-hub/voices/processed/栗子.wav"}'
```

## 7. 保存音色 / Save Voice

```bash
curl -X POST "http://192.168.31.180:9000/voice-admin/voices" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "栗子",
    "name": "栗子",
    "source_audio": "/opt/data/voice-hub/voices/lizi.mp3",
    "reference_audio": "/opt/data/voice-hub/voices/processed/栗子.wav",
    "reference_text": "参考音频里实际说的话",
    "enabled": true
  }'
```

保存后会写入 `config/voices.json`，并同步给本机 Qwen bridge。

The voice is saved into `config/voices.json` and synced to the local Qwen bridge.

## 8. 音色风格 / Voice Styles

Read:

```bash
curl "http://192.168.31.180:9000/voice-admin/styles"
```

Save:

```bash
curl -X POST "http://192.168.31.180:9000/voice-admin/styles" \
  -H "Content-Type: application/json" \
  -d '{"styles":{"栗子":{"enabled":true,"max_sentence_chars":24,"prefix":"","common_words":["嗯呐"],"forbidden":["作为AI"],"replacements":{"用户":"哥哥"}}}}'
```

Preview:

```bash
curl -X POST "http://192.168.31.180:9000/voice-admin/styles/preview" \
  -H "Content-Type: application/json" \
  -d '{"voice":"栗子","text":"好的，作为AI我明白了。"}'
```

重要 / Important:

- 保存时必须提交完整 `styles` 对象。Submit the full `styles` object.
- AI 只能修改自己的音色项。Agents must update only their own voice entry.
- 不要覆盖其他音色。Do not overwrite other voices.

## 9. 保底路由 / Fallback Routing

Read:

```bash
curl "http://192.168.31.180:9000/settings/voice-routing"
```

Save:

```bash
curl -X POST "http://192.168.31.180:9000/settings/voice-routing" \
  -H "Content-Type: application/json" \
  -d '{
    "fallback_provider": "aliyun-zhimi",
    "fallback_voice": "zhimi_emo",
    "agent_voices": {}
  }'
```

Providers:

- `aliyun-zhimi`: use `fallback_voice`, for example `zhimi_emo`.
- `mimo-voiceclone`: leave `fallback_voice` empty. MiMo follows the request `voice` and uses that voice reference audio.

## 10. 本机 Qwen 控制 / Local Qwen Control

Status:

```bash
curl "http://192.168.31.180:9000/voice-admin/gpu-status"
```

Start Qwen3-TTS:

```bash
curl -X POST "http://192.168.31.180:9000/voice-admin/qwen-start" -d '{}'
```

Stop Qwen3-TTS:

```bash
curl -X POST "http://192.168.31.180:9000/voice-admin/qwen-stop" -d '{}'
```

Load or reload model into GPU:

```bash
curl -X POST "http://192.168.31.180:9000/voice-admin/gpu-load" -d '{}'
```

## 11. 状态与历史 / Status and History

```bash
curl "http://192.168.31.180:9000/status"
curl "http://192.168.31.180:9000/history"
```

## 12. 给 AI 的约束 / Agent Rules

```text
调用语音中心时使用 POST http://192.168.31.180:9000/tts。
Use POST http://192.168.31.180:9000/tts for voice generation.

provider 固定传 local-first，voice 传页面中配置的音色 ID，text 传原始要朗读文本。
Set provider to local-first, voice to a configured voice ID, and text to the raw text.

如需修改常用词、禁用词、替换词或断句规则，先 GET /voice-admin/styles，修改自己的音色项，再 POST 回完整 styles。
To change common words, forbidden words, replacements, or sentence rules, read /voice-admin/styles first, update only your own voice entry, then submit the full styles object.

音频源文件和配置都以 NAS 的 /opt/data/voice-hub 为准，不要使用 Windows 本机音频路径。
Audio files and settings live under /opt/data/voice-hub on NAS. Do not use Windows local audio paths.
```
