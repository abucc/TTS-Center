# Voice Hub 使用说明 / User Guide

## 1. 地址 / Addresses

- 管理页面 / Admin UI: `http://192.168.31.180:3003`
- API 地址 / API base: `http://192.168.31.180:9000`
- Swagger 文档 / Swagger docs: `http://192.168.31.180:9000/docs`

## 2. 工作方式 / How It Works

语音中心优先调用本机 Qwen3-TTS。若本机不可用或生成失败，会自动切换到页面配置的保底 TTS，目前支持阿里云 TTS 和小米 MiMo 音色克隆。

Voice Hub uses local Qwen3-TTS first. If local generation fails, it falls back to the configured fallback provider. Current fallback providers are Aliyun TTS and Xiaomi MiMo voice clone.

生成链路 / Pipeline:

1. 调用 `/tts`。Call `/tts`.
2. 根据 `voice` 读取音色与风格配置。Load voice and style settings by `voice`.
3. 应用禁用词、替换词、断句规则。Apply forbidden words, replacements, and sentence rules.
4. 长文本按目标长度智能分块，优先在自然停顿处截断。Split long text at natural pauses.
5. 多段音频自动拼接。Merge generated chunks.
6. 本机失败时自动走保底 TTS。Fallback automatically when local Qwen fails.

## 3. 页面功能 / Admin UI

### 上传音频 / Upload Audio

在页面选择授权音频并上传。上传后保存到 NAS:

Upload authorized audio files from the UI. Files are stored on NAS:

```text
/opt/data/voice-hub/voices
```

### 生成音色 / Create a Voice

选择源音频后，可以设置:

After selecting source audio, configure:

- 音色 ID / Voice ID: API 调用时传入的 `voice`。
- 显示名称 / Display name: 页面展示用。
- 源音频 / Source audio: 上传到 NAS 的原始音频。
- 参考音频 / Reference audio: 截取清洗后的音频。
- 参考文本 / Reference text: 建议自动识别后手动修正。

### 音色风格 / Voice Style

每个音色可以配置:

Each voice supports:

- 启用风格整理 / Enable style processing.
- 每句最多字数 / Max sentence length.
- 固定前缀 / Prefix.
- 常用词 / Common words.
- 禁用词 / Forbidden words.
- 替换词 / Replacements, format: `原词=>新词`.

保存后写入 / Saved to:

```text
/opt/data/voice-hub/config/voice-styles.json
```

其他 AI 可以通过 API 自助维护自己的音色风格配置。修改前必须读取完整配置，只修改自己的音色项，再提交完整 `styles`，不要覆盖其他音色。

Other AI agents may maintain their own voice style settings through the API. They must read the full settings first, update only their own voice entry, and submit the full `styles` object back.

### 本机 Qwen 控制 / Local Qwen Controls

页面“本机 Qwen”卡片提供:

The Local Qwen card provides:

- 灰灯 / Gray: 本机或 bridge 不可达。The PC or bridge is unreachable.
- 红灯 / Red: bridge 在线，但 Qwen3-TTS 未启动。Bridge is online, Qwen3-TTS is not running.
- 绿灯 / Green: Qwen3-TTS 已启动。Qwen3-TTS is running.
- 启动 / Start: 隐性启动 Qwen3-TTS。
- 关闭 / Stop: 关闭 Qwen3-TTS，释放显存。
- 重载GPU / Reload GPU: 将模型加载到 GPU。

GPU 小条会显示 `GPU 已加载模型` 或 `GPU 未加载模型`。

The GPU status row shows whether the model is loaded into GPU memory.

### 保底 TTS / Fallback TTS

页面“调用配置”里可以选择:

Fallback providers:

- `aliyun-zhimi`: 使用 Hermes 已配置好的阿里云 TTS，音色填写阿里云 voice，例如 `zhimi_emo`。
- `mimo-voiceclone`: 使用当前请求音色的参考音频调用小米 MiMo。MiMo 不使用固定保底音色，调用方传哪个 `voice` 就使用哪个参考音频。

MiMo credentials are configured through Docker `.env`, not in code or docs:

```text
MIMO_API_KEY=...
MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
MIMO_MODEL=mimo-v2.5-tts-voiceclone
MIMO_AUTH_HEADER=auto
```

If the key starts with `tp-`, use a Token Plan base URL such as `https://token-plan-cn.xiaomimimo.com/v1`; the default pay-as-you-go URL may return 401.

## 4. API 示例 / API Example

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

返回里的 `duration` 是真实音频时长，`generation_duration` 是生成耗时，单位都是毫秒。

`duration` is the real audio length. `generation_duration` is request generation time. Both are in milliseconds.

## 5. NAS 数据目录 / NAS Data Layout

```text
/opt/data/voice-hub/
  voices/                       uploaded source audio
  voices/processed/             processed reference audio
  config/voices.json            voice definitions
  config/voice-styles.json      voice style settings
  config/voice-routing.json     fallback routing
```

本机 Qwen bridge 只负责计算，会通过语音中心 URL 临时读取 NAS 音频。不要把 NAS 内路径改成 Windows 路径。

The local Qwen bridge is compute-only. It reads NAS audio through Voice Hub URLs. Keep persisted audio paths on NAS, not Windows local paths.

## 6. 文本长度建议 / Text Length

建议每次发送 20 到 80 个中文字符。长回复最好由调用方先按自然句拆开。语音中心仍会智能分块并优先在停顿处截断。

Recommended input size is 20 to 80 Chinese characters. Long replies should be split by natural sentences before calling the API.

## 7. 故障排查 / Troubleshooting

检查本机 bridge / Check local bridge:

```bash
curl http://192.168.31.167:7861/health
```

查看 NAS 容器 / Check NAS containers:

```bash
cd /volume1/docker/voice-hub
docker compose ps
docker compose logs -f voice-hub-gateway
docker compose logs -f voice-hub-frontend
```

重启语音中心 / Restart Voice Hub:

```bash
cd /volume1/docker/voice-hub
docker compose up -d --build voice-hub-gateway voice-hub-frontend
```
