# 给其他 AI 的语音调用交接说明

## 结论

现在不要让各个 AI 自己维护 TTS 脚本或在回复里硬拼风格提示词。统一调用语音中心，由语音中心负责:

- 选择本机 Qwen3-TTS 或保底 TTS。
- 根据音色 ID 应用风格配置。
- 处理常用词、禁用词、替换词。
- 控制断句，并按目标 80 字、最多 120 字做停顿优先分块。
- 生成失败时自动切保底 provider。

各个 AI 可以自助维护自己的音色风格配置，例如常用词、禁用词、替换词和断句长度，但只能修改自己的 `voice` 配置，不要覆盖其他 AI 的配置。

## 调用参数

接口:

```text
http://192.168.31.180:9000/tts
```

固定参数:

```json
{
  "provider": "local-first",
  "format": "wav",
  "cache": false
}
```

每个 AI 只需要决定:

- `voice`: 使用哪个音色 ID。
- `text`: 要朗读的原始文本。

示例:

```json
{
  "provider": "local-first",
  "voice": "水水",
  "text": "这里放需要朗读的内容。",
  "format": "wav",
  "cache": false
}
```

## 推荐分工

- 栗子: `voice` 使用 `栗子`。
- 水水: `voice` 使用 `水水`。
- 兔娘: `voice` 使用 `兔娘`。

如果页面里新增了音色，以页面保存的音色 ID 为准。

## 文本要求

调用方传原始文本即可，不需要主动拼接“使用某某语气”这种前缀。

推荐:

- 每次 20 到 60 个中文字符。
- 长回复先按自然句拆开。
- 不要一次传几百字。

语音中心仍会做智能分块，目标 80 字、最多 120 字，并优先在自然停顿处截断；调用方提前拆句会更自然、更快。

接口返回里的 `duration` 是真实音频时长，`generation_duration` 是生成耗时，单位都是毫秒。不要用 `generation_duration` 判断音频有多长。

## 维护方式

音色风格在管理页面维护:

```text
http://192.168.31.180:3003
```

修改后保存即可，其他 AI 不需要改代码。

配置文件位置:

```text
/opt/data/voice_styles.json
```

## 自助修改音色风格配置

读取当前全部风格:

```bash
curl "http://192.168.31.180:9000/voice-admin/styles"
```

保存风格时要先读取现有配置，只修改自己的那一项，再把完整 `styles` 写回去。不要只提交自己的单项配置，否则可能覆盖其他音色。

字段说明:

- `enabled`: 是否启用风格整理。
- `max_sentence_chars`: 每句最多字数，建议 20 到 30。
- `prefix`: 固定前缀，默认留空。
- `common_words`: 常用词列表，只记录偏好，不强行乱插。
- `forbidden`: 禁用词列表，出现就删除。
- `replacements`: 替换词表，格式是 `"原词": "新词"`。

示例，只修改 `栗子`:

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
    "forbidden": ["作为AI", "作为一个AI", "我是AI"],
    "replacements": {
        **styles.get("栗子", {}).get("replacements", {}),
        "好的": "好嘛",
        "明白了": "知道啦"
    }
}

requests.post(f"{base}/voice-admin/styles", json={"styles": styles}, timeout=10).raise_for_status()
```

修改前可以先预览，不会生成音频:

```bash
curl -X POST "http://192.168.31.180:9000/voice-admin/styles/preview" \
  -H "Content-Type: application/json" \
  -d '{"voice":"栗子","text":"好的，作为AI我明白了，用户继续测试。"}'
```

自助修改规则:

- 只改自己的 `voice`，例如栗子只改 `栗子`。
- 修改前必须 GET 当前配置，修改后 POST 完整配置。
- 不要把账号、token、路径密码写进风格配置。
- 不要把 `max_sentence_chars` 设太大，建议不超过 30。
- 不要删除其他 AI 的配置。
