# 语音中心使用说明

## 地址

- 管理页面: `http://192.168.31.180:3003`
- API 地址: `http://192.168.31.180:9000`
- API 文档: `http://192.168.31.180:9000/docs`

## 当前能力

语音中心优先调用本机 Qwen3-TTS，失败后再走保底 TTS。保底 provider 当前配置为 Hermes 里的阿里云 TTS，后续可以继续扩展其他 provider。

实际生成链路:

1. 调用 `/tts`。
2. 按 `voice` 读取音色风格配置。
3. 应用禁用词、替换词、断句规则。
4. 超过 80 字自动分块生成。
5. 多段 WAV 自动拼接。
6. 本机 Qwen 失败时，自动走保底 TTS。

## 页面功能

### 音频目录

把已授权的参考音频放到页面配置的固定目录里，点击刷新后会显示在音频列表中。

### 生成音色配置

选择参考音频后，可以配置:

- 音色 ID: Hermes/OpenClaw/其他 AI 调用时使用的 `voice`。
- 音色名称: 页面显示用。
- 参考音频: 清洗裁剪后的音频路径。
- 参考文本: 推荐先自动识别，再手动修正。

### 音色风格配置

每个音色可以配置:

- 是否启用风格整理。
- 每句最多字数。
- 固定前缀。
- 常用词。
- 禁用词。
- 替换词，格式为 `原词=>新词`。

保存后会写入:

```text
/opt/data/voice_styles.json
```

页面里的“预览整理”只做文本预览，不生成音频。真正调用 `/tts` 时也会自动使用同一套规则。

其他 AI 也可以通过 API 自助维护自己的音色风格配置。原则是先读取完整配置，只修改自己的音色 ID，再提交完整配置，不能覆盖其他音色。

## API 调用示例

```bash
curl -X POST "http://192.168.31.180:9000/tts" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "local-first",
    "voice": "栗子",
    "text": "好的，作为AI我明白了，用户继续测试。",
    "format": "wav",
    "cache": false
  }'
```

### 读取和保存音色风格

读取:

```bash
curl "http://192.168.31.180:9000/voice-admin/styles"
```

保存:

```bash
curl -X POST "http://192.168.31.180:9000/voice-admin/styles" \
  -H "Content-Type: application/json" \
  -d '{"styles":{...完整styles对象...}}'
```

预览:

```bash
curl -X POST "http://192.168.31.180:9000/voice-admin/styles/preview" \
  -H "Content-Type: application/json" \
  -d '{"voice":"栗子","text":"好的，作为AI我明白了，用户继续测试。"}'
```

返回里的 `audio_url` 是相对路径，需要拼接 API 地址:

```text
http://192.168.31.180:9000/audio/xxxxx
```

## 常用音色 ID

当前默认包含:

- `栗子`
- `水水`
- `兔娘`

新增音色后，以页面保存的音色 ID 为准。

## 文本长度建议

语音中心会自动按 80 字分块。为了速度和断句自然，调用方最好每次发送 20 到 60 个中文字符。如果是很长回复，建议调用方先按句号、问号、感叹号、逗号拆成多段。

## 故障排查

### 本机 Qwen 不可用

检查:

```bash
curl http://192.168.31.167:7861/health
```

如果失败，语音中心仍会尝试保底 TTS。

### 查看语音中心容器

```bash
cd /volume1/docker/voice-hub
docker compose ps
docker compose logs -f voice-hub-gateway
docker compose logs -f voice-hub-frontend
```

### 重启

```bash
cd /volume1/docker/voice-hub
docker compose up -d --build voice-hub-gateway voice-hub-frontend
```
