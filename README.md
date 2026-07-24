# TTS Center / 语音中心

TTS Center is a NAS-hosted voice hub built from Awesome-TTS and adapted for Hermes, OpenClaw, and other local AI agents.

语音中心基于 Awesome-TTS 改造，用作 NAS 上的统一语音生成中心，供 Hermes、OpenClaw 和其他本地 AI 调用。

## 1. What This Project Does / 项目用途

TTS Center provides one stable API and one Chinese admin UI for voice generation, voice asset management, fallback routing, and per-voice style rules.

语音中心提供统一 API 和中文管理页面，用于语音生成、音色资产管理、保底路由和每个音色的风格规则维护。

Core flow / 核心链路:

1. Caller sends text to `/tts`.
2. Voice Hub applies the selected `voice` configuration.
3. Local Qwen3-TTS is used first.
4. If local Qwen fails, Voice Hub falls back to the configured provider.
5. Generated audio is returned through a playable URL and recorded in history.

1. 调用方把文本发送到 `/tts`。
2. 语音中心按 `voice` 加载音色配置。
3. 优先调用本机 Qwen3-TTS。
4. 本机失败后自动调用页面配置的保底 TTS。
5. 返回可播放音频地址，并记录生成历史。

## 2. Current Services / 当前服务

- Admin UI / 管理页面: `http://192.168.31.180:3003`
- API base / API 地址: `http://192.168.31.180:9000`
- Swagger / 接口文档: `http://192.168.31.180:9000/docs`
- Local Qwen bridge / 本机 Qwen 桥接: `http://192.168.31.167:7861`
- Qwen3-TTS WebUI / Qwen3-TTS 页面: `http://192.168.31.167:7860`

## 3. Features / 功能

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
- Bilingual human and AI documentation.

- 本机优先链路：Qwen3-TTS 优先，失败后走保底 TTS。
- 保底服务：阿里云 TTS、小米 MiMo 音色克隆。
- 音频资产和配置都保存在 NAS。
- 管理页面上传源音频。
- 截取并清洗参考音频。
- 保存音色定义和参考文本。
- 每个音色支持常用词、禁用词、替换词、固定前缀和断句长度。
- 长文本按自然停顿智能分块。
- 页面控制 Qwen 启动、关闭、重载 GPU。
- 页面展示 Qwen 服务状态、GPU 加载状态和显存占用。
- 最近生成历史可直接播放。
- 提供面向人和 AI 的中英双语说明文档。

## 4. Documentation / 文档

- User guide / 使用说明: [docs/VOICE_HUB_USAGE.md](docs/VOICE_HUB_USAGE.md)
- API reference / API 文档: [docs/VOICE_HUB_API.md](docs/VOICE_HUB_API.md)
- Hermes integration / Hermes 接入: [docs/HERMES_TTS_CONFIG.md](docs/HERMES_TTS_CONFIG.md)
- AI handoff / AI 交接: [docs/AI_TTS_HANDOFF.md](docs/AI_TTS_HANDOFF.md)

## 5. Data Layout / 数据目录

Voice Hub is deployed on NAS Docker and stores persistent data under `/opt/data/voice-hub`.

语音中心部署在 NAS Docker 中，持久化数据统一放在 `/opt/data/voice-hub`。

```text
/opt/data/voice-hub/
  voices/                       uploaded source audio
  voices/processed/             processed reference audio
  config/voices.json            voice definitions
  config/voice-styles.json      voice style settings
  config/voice-routing.json     fallback routing
```

The local Windows Qwen bridge is compute-only. It reads NAS audio through Voice Hub URLs.

Windows 本机 Qwen bridge 只负责计算，通过语音中心 URL 临时读取 NAS 音频。

## 6. Quick API Example / API 快速示例

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

Response fields / 返回字段:

- `actual_provider`: actual provider used, such as `qwen-local`, `aliyun-zhimi`, or `mimo-voiceclone`.
- `duration`: real audio duration in milliseconds.
- `generation_duration`: generation time in milliseconds.
- `audio_url`: relative audio playback URL.

- `actual_provider`: 实际使用的 provider，例如 `qwen-local`、`aliyun-zhimi`、`mimo-voiceclone`。
- `duration`: 真实音频时长，单位毫秒。
- `generation_duration`: 生成耗时，单位毫秒。
- `audio_url`: 相对音频播放地址。

## 7. Admin Workflow / 管理流程

1. Open the admin UI.
2. Upload authorized source audio.
3. Select the source audio and clip a clean reference segment.
4. Transcribe or manually enter reference text.
5. Save the voice and style settings together.
6. Test generation.
7. Let Hermes/OpenClaw call `/tts` with the selected `voice`.

1. 打开管理页面。
2. 上传已授权的源音频。
3. 选择源音频并截取干净的参考片段。
4. 自动识别或手动填写参考文本。
5. 一起保存音色和风格配置。
6. 生成试听。
7. Hermes/OpenClaw 调用 `/tts` 并传入对应 `voice`。

## 8. Local Qwen Controls / 本机 Qwen 控制

The admin UI has a Local Qwen card:

管理页面有“本机 Qwen”卡片：

- Gray light / 灰灯: PC, network, or bridge is unreachable.
- Red light / 红灯: bridge is online, but Qwen3-TTS is not running.
- Green light / 绿灯: Qwen3-TTS is running.
- Start / 启动: starts Qwen3-TTS silently.
- Stop / 关闭: stops Qwen3-TTS and frees GPU memory.
- Reload GPU / 重载GPU: loads the model into GPU memory.

The bridge starts Qwen with hidden Windows subprocess settings to avoid visible Python console windows.

bridge 使用隐藏窗口方式启动 Qwen，避免频繁弹出 Python 控制台窗口。

## 9. Deployment / 部署

NAS deployment path / NAS 部署目录:

```bash
cd /volume1/docker/voice-hub
docker compose up -d --build voice-hub-gateway voice-hub-frontend
```

Check status / 查看状态:

```bash
docker compose ps
docker compose logs -f voice-hub-gateway
docker compose logs -f voice-hub-frontend
```

## 10. Environment Variables / 环境变量

Important variables / 关键变量:

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

不要提交真实 `.env`、API key、token、上传音频、生成音频或私人运行数据。

## 11. Agent Rules / AI 调用规则

```text
Use POST http://192.168.31.180:9000/tts for TTS.
Set provider=local-first, voice=<configured voice ID>, text=<raw text>.
Do not manually prepend style prompts.
To edit voice style, GET /voice-admin/styles first, update only your own voice entry, then POST the full styles object back.

统一调用 POST http://192.168.31.180:9000/tts。
provider=local-first，voice=页面配置的音色 ID，text=原始朗读文本。
不要自己拼接风格提示词。
修改音色风格时，先 GET /voice-admin/styles，只改自己的音色项，再 POST 回完整 styles。
```

## 12. Upstream / 上游项目

This project started from Awesome-TTS and has been adapted into a NAS voice center workflow.

本项目基于 Awesome-TTS 改造，当前主要服务于 NAS 语音中心工作流。

Original upstream / 原上游:

```text
https://github.com/isaacgounton/awesome-tts
```

## 13. License / 许可证

This repository keeps the upstream MIT license unless a file states otherwise.

除非具体文件另有说明，本仓库沿用上游 MIT License。
