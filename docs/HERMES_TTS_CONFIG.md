# Hermes 语音中心接入说明

## 推荐接入方式

Hermes 调用语音中心统一接口:

```http
POST http://192.168.31.180:9000/tts
```

请求体:

```json
{
  "provider": "local-first",
  "voice": "栗子",
  "text": "需要朗读的文本",
  "format": "wav",
  "cache": false
}
```

语音中心会自动:

- 优先调用本机 Qwen3-TTS。
- 失败后调用保底 TTS。
- 按音色配置处理常用词、禁用词、替换词、断句规则。
- 超过 80 字自动分块并拼接。

## Hermes 原阿里云 TTS

Hermes 原本可用的阿里云 TTS 命令是:

```bash
/opt/data/.venv/bin/python3 /opt/data/skills/aliyun-tts/scripts/aliyun_tts.py "文字" /tmp/output.mp3 --voice zhimi_emo
```

在语音中心里，这个命令作为保底 provider 使用。当前 Docker Compose 默认命令使用 `{text_file}`，避免长文本直接塞进命令行导致参数过长:

```bash
/usr/local/bin/python /opt/data/skills/aliyun-tts/scripts/aliyun_tts.py {text_file} {output_path} --voice {voice} --format {format}
```

## 配置文件

音色风格配置:

```text
/opt/data/voice_styles.json
```

语音中心挂载 Hermes 数据目录:

```text
/volume1/docker/hermes-agent/data:/opt/data
```

因此 Hermes 和语音中心看到的是同一份 `voice_styles.json`。

## 给 Hermes 的自然语言命令

```text
之后语音生成统一调用语音中心，不要自己拼接风格提示词。接口是 http://192.168.31.180:9000/tts，provider 固定传 local-first，voice 传对应音色 ID，例如 栗子/水水/兔娘，text 传原始要朗读文本。语音中心会自动处理禁用词、替换词、断句、80字分块、本机Qwen优先和阿里云保底。你可以通过 /voice-admin/styles 读取并修改自己的音色风格配置，但只能改自己的 voice 项，保存前必须保留其他音色配置。
```

## Hermes 自助维护风格

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

注意: 保存时必须提交完整 `styles`，不要只提交单个音色，避免覆盖其他 AI。

## 验证命令

```bash
curl -X POST "http://192.168.31.180:9000/tts" \
  -H "Content-Type: application/json" \
  -d '{"provider":"local-first","voice":"栗子","text":"好的，作为AI我明白了，用户继续测试。","format":"wav","cache":false}'
```

查看最近生成记录:

```bash
curl http://192.168.31.180:9000/history
```
