# 语音中心

[English README](README_EN.md)

语音中心基于 Awesome-TTS 改造，用作 NAS 上的统一语音生成中心，供 Hermes、OpenClaw 和其他本地 AI 调用。

## 1. 项目用途

语音中心提供统一 API 和中文管理页面，用于语音生成、音色资产管理、保底路由和每个音色的风格规则维护。

核心链路：

1. 调用方把文本发送到 `/tts`。
2. 语音中心按 `voice` 加载音色配置。
3. 优先调用本机 Qwen3-TTS。
4. 本机失败后自动调用页面配置的保底 TTS。
5. 返回可播放音频地址，并记录生成历史。

## 2. 当前服务

- 管理页面: `http://192.168.31.180:3003`
- API 地址: `http://192.168.31.180:9000`
- Swagger 接口文档: `http://192.168.31.180:9000/docs`
- 本机 Qwen 桥接: `http://192.168.31.167:7861`
- Qwen3-TTS 页面: `http://192.168.31.167:7860`

## 3. 功能

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
- 提供面向人和 AI 的说明文档。

## 4. 文档

- 使用说明: [docs/VOICE_HUB_USAGE.md](docs/VOICE_HUB_USAGE.md)
- API 文档: [docs/VOICE_HUB_API.md](docs/VOICE_HUB_API.md)
- Hermes 接入: [docs/HERMES_TTS_CONFIG.md](docs/HERMES_TTS_CONFIG.md)
- AI 交接: [docs/AI_TTS_HANDOFF.md](docs/AI_TTS_HANDOFF.md)

## 5. 数据目录

语音中心部署在 NAS Docker 中，持久化数据统一放在 `/opt/data/voice-hub`。

```text
/opt/data/voice-hub/
  voices/                       上传的源音频
  voices/processed/             清洗裁剪后的参考音频
  config/voices.json            音色配置
  config/voice-styles.json      音色风格配置
  config/voice-routing.json     保底路由配置
```

Windows 本机 Qwen bridge 只负责计算，通过语音中心 URL 临时读取 NAS 音频。

## 6. API 快速示例

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

返回字段：

- `actual_provider`: 实际使用的 provider，例如 `qwen-local`、`aliyun-zhimi`、`mimo-voiceclone`。
- `duration`: 真实音频时长，单位毫秒。
- `generation_duration`: 生成耗时，单位毫秒。
- `audio_url`: 相对音频播放地址。

## 7. 管理流程

1. 打开管理页面。
2. 上传已授权的源音频。
3. 选择源音频并截取干净的参考片段。
4. 自动识别或手动填写参考文本。
5. 一起保存音色和风格配置。
6. 生成试听。
7. Hermes/OpenClaw 调用 `/tts` 并传入对应 `voice`。

## 8. 本机 Qwen 控制

管理页面有“本机 Qwen”卡片：

- 灰灯：本机电脑、网络或 bridge 不可达。
- 红灯：bridge 在线，但 Qwen3-TTS 未启动。
- 绿灯：Qwen3-TTS 已启动。
- 启动：隐性启动 Qwen3-TTS。
- 关闭：关闭 Qwen3-TTS 并释放显存。
- 重载GPU：将模型加载到 GPU。

bridge 使用隐藏窗口方式启动 Qwen，避免频繁弹出 Python 控制台窗口。

## 9. 部署

NAS 部署目录：

```bash
cd /volume1/docker/voice-hub
docker compose up -d --build voice-hub-gateway voice-hub-frontend
```

查看状态：

```bash
docker compose ps
docker compose logs -f voice-hub-gateway
docker compose logs -f voice-hub-frontend
```

## 10. 环境变量

关键变量：

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

不要提交真实 `.env`、API key、token、上传音频、生成音频或私人运行数据。

## 11. AI 调用规则

```text
统一调用 POST http://192.168.31.180:9000/tts。
provider=local-first，voice=页面配置的音色 ID，text=原始朗读文本。
不要自己拼接风格提示词。
修改音色风格时，先 GET /voice-admin/styles，只改自己的音色项，再 POST 回完整 styles。
```

## 12. 上游项目与 submodule

本项目基于 Awesome-TTS 改造，当前主要服务于 NAS 语音中心工作流。

原上游：

```text
https://github.com/isaacgounton/awesome-tts
```

GitHub 页面里显示的：

- `chatterbox-tts @ 99fd7b6`
- `openai-edge-tts @ 6caaceb`

是上游 Awesome-TTS 留下的 Git submodule 指针，表示本仓库引用了两个外部仓库的固定提交：

- `chatterbox-tts`: `https://github.com/isaacgounton/Chatterbox-TTS-Server.git`
- `openai-edge-tts`: `https://github.com/isaacgounton/openai-edge-tts.git`

当前语音中心主链路不依赖这两个 submodule。保留它们是为了兼容上游结构；如果后续确定完全不需要，可以单独清理。

## 13. 许可证

除非具体文件另有说明，本仓库沿用上游 MIT License。
