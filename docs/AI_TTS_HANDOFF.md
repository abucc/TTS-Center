# AI 语音调用交接说明 / AI TTS Handoff

## 1. 结论 / Summary

各个 AI 不再单独维护 TTS 脚本，也不要在回复里硬拼风格提示词。统一调用语音中心。

AI agents should not maintain separate TTS scripts or manually prepend style prompts. Use Voice Hub.

Voice Hub 负责:

Voice Hub handles:

- 本机 Qwen3-TTS 优先。Local Qwen3-TTS first.
- 失败时自动保底。Automatic fallback.
- 音色风格配置。Voice style settings.
- 常用词、禁用词、替换词。Common words, forbidden words, replacements.
- 长文本智能断句和拼接。Smart chunking and audio merging.

## 2. 调用接口 / Endpoint

```text
POST http://192.168.31.180:9000/tts
```

Fixed fields:

```json
{
  "provider": "local-first",
  "format": "wav",
  "cache": false
}
```

Required per request:

- `voice`: 页面中配置的音色 ID。Configured voice ID.
- `text`: 原始要朗读文本。Raw text to speak.

Example:

```json
{
  "provider": "local-first",
  "voice": "水水",
  "text": "这里放需要朗读的内容。",
  "format": "wav",
  "cache": false
}
```

## 3. 推荐音色 / Suggested Voices

- 栗子 / Lizi: `voice` = `栗子`
- 水水 / Shuishui: `voice` = `水水`
- 兔娘 / Tuniang: `voice` = `兔娘`

新增音色以页面保存的音色 ID 为准。

For new voices, use the voice ID saved in the admin UI.

## 4. 文本要求 / Text Guidance

推荐每次 20 到 80 个中文字符。长回复先按自然句拆开。

Recommended input size is 20 to 80 Chinese characters. Split long replies by natural sentences first.

不要一次传几百字。语音中心仍会智能分块，但调用方提前拆句会更自然、更快。

Do not send hundreds of characters at once. Voice Hub can split long text, but caller-side sentence splitting is faster and more natural.

返回里的 `duration` 是真实音频时长，`generation_duration` 是生成耗时，单位都是毫秒。

`duration` is real audio length. `generation_duration` is generation time. Both are in milliseconds.

## 5. 自助维护风格 / Self-Service Style Editing

管理页面 / Admin UI:

```text
http://192.168.31.180:3003
```

配置文件 / Config file:

```text
/opt/data/voice-hub/config/voice-styles.json
```

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

规则 / Rules:

- 先读取完整配置。Read the full config first.
- 只修改自己的音色项。Modify only your own voice entry.
- 保存时提交完整 `styles` 对象。Submit the full `styles` object.
- 禁止覆盖其他音色。Do not overwrite other voices.

字段 / Fields:

- `enabled`: 是否启用风格整理 / enable style processing.
- `max_sentence_chars`: 每句最多字数 / max sentence length.
- `prefix`: 固定前缀 / fixed prefix.
- `common_words`: 常用词 / common words.
- `forbidden`: 禁用词 / forbidden words.
- `replacements`: 替换词表 / replacement map.

Example:

```python
import requests

base = "http://192.168.31.180:9000"
data = requests.get(f"{base}/voice-admin/styles", timeout=10).json()
styles = data["styles"]

styles["栗子"] = {
    **styles.get("栗子", {}),
    "enabled": True,
    "max_sentence_chars": 24,
    "common_words": ["嗯呐", "嘿嘿", "哥哥"],
    "forbidden": ["作为AI"],
    "replacements": {"用户": "哥哥"},
}

requests.post(f"{base}/voice-admin/styles", json={"styles": styles}, timeout=10).raise_for_status()
```

## 6. 状态检查 / Status

```bash
curl "http://192.168.31.180:9000/status"
curl "http://192.168.31.180:9000/voice-admin/gpu-status"
curl "http://192.168.31.180:9000/history"
```

## 7. 一句话命令 / One-Line Command

```text
以后语音统一调用 http://192.168.31.180:9000/tts，provider=local-first，voice=你要使用的音色 ID，text=原始朗读文本；不要自己拼风格提示词。需要改常用词/禁用词/替换词/断句规则时，先读取 /voice-admin/styles，只修改自己的音色项，再提交完整 styles。

Use http://192.168.31.180:9000/tts for TTS. Set provider=local-first, voice to the configured voice ID, and text to the raw text. Do not manually prepend style prompts. To edit common words, forbidden words, replacements, or sentence rules, read /voice-admin/styles first, update only your own voice entry, then submit the full styles object.
```
