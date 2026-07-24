# Hermes 语音中心接入说明 / Hermes Integration Guide

## 1. 推荐接入 / Recommended Integration

Hermes 统一调用语音中心:

Hermes should call Voice Hub through the unified endpoint:

```http
POST http://192.168.31.180:9000/tts
```

Request:

```json
{
  "provider": "local-first",
  "voice": "栗子",
  "text": "需要朗读的文本",
  "format": "wav",
  "cache": false
}
```

直接传 `voice`。传哪个音色 ID，语音中心就使用哪个音色。

Pass `voice` directly. Voice Hub uses the matching configured voice ID.

## 2. 自动能力 / Automatic Behavior

语音中心会自动:

Voice Hub automatically:

- 优先调用本机 Qwen3-TTS。Uses local Qwen3-TTS first.
- 失败后调用页面配置的保底 TTS。Falls back to the configured fallback provider.
- 按音色配置处理常用词、禁用词、替换词、断句规则。Applies voice style rules.
- 长文本智能分块并拼接。Splits and merges long text naturally.

Hermes 不需要自己拼接“风格提示词”，也不需要直接调用阿里云脚本。

Hermes should not manually prepend style prompts or call the Aliyun script directly for normal TTS.

## 3. 原阿里云 TTS / Existing Aliyun TTS

Hermes 原本可用的阿里云命令:

Existing Hermes Aliyun command:

```bash
/opt/data/.venv/bin/python3 /opt/data/skills/aliyun-tts/scripts/aliyun_tts.py "文字" /tmp/output.mp3 --voice zhimi_emo
```

语音中心将它作为保底 provider。Docker Compose 默认使用 `{text_file}`，避免长文本塞进命令行:

Voice Hub uses it as a fallback provider. The compose command uses `{text_file}` to avoid long command-line arguments:

```bash
/usr/local/bin/python /opt/data/skills/aliyun-tts/scripts/aliyun_tts.py {text_file} {output_path} --voice {voice} --format {format}
```

## 4. 小米 MiMo 保底 / Xiaomi MiMo Fallback

`mimo-voiceclone` 会读取当前 `voice` 的 NAS 参考音频，转为 base64 调用 MiMo。

`mimo-voiceclone` reads the NAS reference audio for the requested `voice`, converts it to base64, and calls MiMo.

凭证通过 Docker `.env` 配置，不写入代码:

Credentials are configured in Docker `.env`, not committed to code:

```text
MIMO_API_KEY=...
MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
MIMO_MODEL=mimo-v2.5-tts-voiceclone
MIMO_AUTH_HEADER=auto
```

如果 key 以 `tp-` 开头，必须使用 Token Plan 专属 Base URL，否则可能 401。

If the key starts with `tp-`, use a Token Plan base URL; the default API URL may return 401.

## 5. 配置文件 / Config Files

```text
/opt/data/voice-hub/config/voices.json          voice definitions
/opt/data/voice-hub/config/voice-styles.json    style rules
/opt/data/voice-hub/config/voice-routing.json   fallback routing
/opt/data/voice-hub/voices                      source audio
/opt/data/voice-hub/voices/processed            processed reference audio
```

语音中心挂载 Hermes 数据目录:

Voice Hub mounts the Hermes data directory:

```text
/volume1/docker/hermes-agent/data:/opt/data
```

因此 Hermes 和语音中心看到的是同一份 `/opt/data/voice-hub` 数据。

Therefore Hermes and Voice Hub share the same `/opt/data/voice-hub` data.

## 6. 给 Hermes 的自然语言命令 / Natural-Language Command for Hermes

```text
之后语音生成统一调用语音中心，不要自己拼接风格提示词。接口是 http://192.168.31.180:9000/tts，provider 固定传 local-first，voice 传要使用的音色 ID，例如 栗子/水水/兔娘，text 传原始要朗读文本。语音中心会自动处理禁用词、替换词、断句、本机 Qwen 优先和保底 TTS。你可以通过 /voice-admin/styles 读取并修改自己的音色风格配置，但只能改自己的音色项，保存前必须保留其他音色配置。音频源文件和配置都以 NAS 的 /opt/data/voice-hub 为准，不要使用 Windows 本机音频路径。

Use Voice Hub for all TTS generation. Do not manually prepend style prompts. Endpoint: http://192.168.31.180:9000/tts. Set provider to local-first, voice to the desired voice ID such as 栗子/水水/兔娘, and text to the raw text. Voice Hub handles forbidden words, replacements, sentence splitting, local Qwen first, and fallback TTS. You may read and update your own voice style through /voice-admin/styles, but only modify your own voice entry and preserve all other voices. Audio and config paths are under /opt/data/voice-hub on NAS, not Windows local paths.
```

## 7. Hermes 自助维护风格 / Self-Service Style Updates

Read:

```bash
curl "http://192.168.31.180:9000/voice-admin/styles"
```

Save:

```bash
curl -X POST "http://192.168.31.180:9000/voice-admin/styles" \
  -H "Content-Type: application/json" \
  -d '{"styles":{...完整styles对象...}}'
```

注意: 保存时必须提交完整 `styles`，不要只提交单个音色。

Important: submit the full `styles` object. Do not submit only one voice entry.

## 8. 验证命令 / Verification

```bash
curl -X POST "http://192.168.31.180:9000/tts" \
  -H "Content-Type: application/json" \
  -d '{"provider":"local-first","voice":"栗子","text":"哥哥，你好，我是栗子，听听我现在的声音怎么样？","format":"wav","cache":false}'
```

History:

```bash
curl http://192.168.31.180:9000/history
```
