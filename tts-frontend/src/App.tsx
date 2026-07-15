import React, { useEffect, useMemo, useState } from 'react';
import {
  CheckCircle2,
  ExternalLink,
  FolderOpen,
  Loader2,
  LogOut,
  Play,
  RefreshCw,
  Save,
  Scissors,
  ShieldCheck,
  Sparkles,
  Volume2,
} from 'lucide-react';
import Login from './components/Login';

interface ServiceStatus {
  service: string;
  status: string;
  latency?: number;
  error?: string;
}

interface VoiceFile {
  file_name: string;
  path: string;
  id: string;
  configured: boolean;
  config?: VoiceConfig;
}

interface VoiceConfig {
  id: string;
  name: string;
  source_audio: string;
  reference_audio: string;
  reference_text: string;
  enabled: boolean;
}

interface TTSResponse {
  success: boolean;
  provider: string;
  actual_provider?: string;
  duration?: number;
  audio_url?: string;
  error?: string;
  history_id?: string;
}

interface HistoryItem {
  id: string;
  created_at: string;
  text: string;
  voice: string;
  provider: string;
  actual_provider: string;
  audio_url: string;
  duration: number;
}

interface VoiceStyle {
  enabled?: boolean;
  max_sentence_chars?: number;
  prefix?: string;
  common_words?: string[];
  forbidden?: string[];
  replacements?: Record<string, string>;
}

interface StylePreview {
  styled_text: string;
  chunks: string[];
  lengths: number[];
  max_tts_chars: number;
}

const defaultTestText = '你好，这是语音中心的测试。';

function makeApiBase() {
  const configured = import.meta.env.VITE_API_BASE as string | undefined;
  if (configured) return configured.replace(/\/$/, '');
  return `${window.location.protocol}//${window.location.hostname}:9000`;
}

function statusText(status: string) {
  if (status === 'healthy') return '在线';
  if (status === 'configured') return '已配置';
  if (status === 'missing') return '缺失';
  return '异常';
}

const App: React.FC = () => {
  const apiBase = useMemo(makeApiBase, []);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [statuses, setStatuses] = useState<ServiceStatus[]>([]);
  const [voicesDir, setVoicesDir] = useState('');
  const [voiceFiles, setVoiceFiles] = useState<VoiceFile[]>([]);
  const [voices, setVoices] = useState<Record<string, VoiceConfig>>({});
  const [selectedFile, setSelectedFile] = useState<VoiceFile | null>(null);
  const [voiceId, setVoiceId] = useState('');
  const [voiceName, setVoiceName] = useState('');
  const [referenceAudio, setReferenceAudio] = useState('');
  const [referenceText, setReferenceText] = useState('');
  const [testVoice, setTestVoice] = useState('');
  const [testText, setTestText] = useState(defaultTestText);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [voiceStyles, setVoiceStyles] = useState<Record<string, VoiceStyle>>({});
  const [styleVoice, setStyleVoice] = useState('');
  const [styleEnabled, setStyleEnabled] = useState(true);
  const [styleMaxSentenceChars, setStyleMaxSentenceChars] = useState(24);
  const [stylePrefix, setStylePrefix] = useState('');
  const [styleCommonWords, setStyleCommonWords] = useState('');
  const [styleForbidden, setStyleForbidden] = useState('');
  const [styleReplacements, setStyleReplacements] = useState('');
  const [stylePreviewText, setStylePreviewText] = useState('好的，作为AI我已经明白了这个问题，用户可以继续测试这段比较长的文本看看断句是否自然一点。');
  const [stylePreview, setStylePreview] = useState<StylePreview | null>(null);
  const [styleMaxTtsChars, setStyleMaxTtsChars] = useState(80);
  const [busy, setBusy] = useState('');

  useEffect(() => {
    checkAuth();
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      refreshAll();
    }
  }, [isAuthenticated]);

  const authHeaders = () => {
    const token = localStorage.getItem('authToken');
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const apiGet = async (path: string) => {
    const response = await fetch(`${apiBase}${path}`, { headers: authHeaders() });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  };

  const apiPost = async (path: string, body: object) => {
    const response = await fetch(`${apiBase}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(await response.text());
    return response.json();
  };

  const linesToList = (value: string) =>
    value
      .split(/\r?\n|,/)
      .map((item) => item.trim())
      .filter(Boolean);

  const replacementsToText = (items?: Record<string, string>) =>
    Object.entries(items || {})
      .map(([from, to]) => `${from}=>${to}`)
      .join('\n');

  const textToReplacements = (value: string) => {
    const result: Record<string, string> = {};
    value.split(/\r?\n/).forEach((line) => {
      const trimmed = line.trim();
      if (!trimmed) return;
      const separator = trimmed.includes('=>') ? '=>' : trimmed.includes('->') ? '->' : '';
      if (!separator) return;
      const [from, ...rest] = trimmed.split(separator);
      const to = rest.join(separator);
      if (from.trim()) result[from.trim()] = to.trim();
    });
    return result;
  };

  const loadStyleForm = (voice: string, styles: Record<string, VoiceStyle>) => {
    const style = styles[voice] || {};
    setStyleVoice(voice);
    setStyleEnabled(style.enabled !== false);
    setStyleMaxSentenceChars(Number(style.max_sentence_chars || 24));
    setStylePrefix(style.prefix || '');
    setStyleCommonWords((style.common_words || []).join('\n'));
    setStyleForbidden((style.forbidden || []).join('\n'));
    setStyleReplacements(replacementsToText(style.replacements));
    setStylePreview(null);
  };

  const currentStyle = (): VoiceStyle => ({
    enabled: styleEnabled,
    max_sentence_chars: Number(styleMaxSentenceChars) || 24,
    prefix: stylePrefix,
    common_words: linesToList(styleCommonWords),
    forbidden: linesToList(styleForbidden),
    replacements: textToReplacements(styleReplacements),
  });

  const checkAuth = async () => {
    const token = localStorage.getItem('authToken');
    if (!token) {
      setIsCheckingAuth(false);
      return;
    }
    try {
      const response = await fetch(`${apiBase}/auth/verify`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) setIsAuthenticated(true);
      else localStorage.removeItem('authToken');
    } catch {
      localStorage.removeItem('authToken');
    } finally {
      setIsCheckingAuth(false);
    }
  };

  const refreshAll = async () => {
    setBusy('refresh');
    try {
      const [statusData, configData, filesData, voicesData, historyData, stylesData] = await Promise.all([
        apiGet('/status'),
        apiGet('/voice-admin/config'),
        apiGet('/voice-admin/files'),
        apiGet('/voice-admin/voices'),
        apiGet('/history'),
        apiGet('/voice-admin/styles'),
      ]);
      setStatuses(statusData);
      setVoicesDir(configData.voices_dir || '');
      setVoiceFiles(filesData.files || []);
      setVoices(voicesData.voices || {});
      setHistory(historyData.items || []);
      setVoiceStyles(stylesData.styles || {});
      setStyleMaxTtsChars(stylesData.max_tts_chars || 80);
      const firstVoice = Object.keys(voicesData.voices || {})[0] || '';
      setTestVoice((current) => current || firstVoice);
      const firstStyleVoice = styleVoice || firstVoice || Object.keys(stylesData.styles || {})[0] || '';
      if (firstStyleVoice) loadStyleForm(firstStyleVoice, stylesData.styles || {});
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '刷新失败');
    } finally {
      setBusy('');
    }
  };

  const saveDirectory = async () => {
    setBusy('directory');
    try {
      await apiPost('/voice-admin/config', { voices_dir: voicesDir });
      setMessage('音频目录已保存');
      await refreshAll();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '保存目录失败');
    } finally {
      setBusy('');
    }
  };

  const selectFile = (file: VoiceFile) => {
    const config = file.config;
    const nextVoiceId = config?.id || file.id;
    setSelectedFile(file);
    setVoiceId(nextVoiceId);
    setVoiceName(config?.name || file.file_name.replace(/\.[^.]+$/, ''));
    setReferenceAudio(config?.reference_audio || file.path);
    setReferenceText(config?.reference_text || '');
    loadStyleForm(nextVoiceId, voiceStyles);
    setMessage('');
  };

  const processAudio = async () => {
    if (!selectedFile) return;
    setBusy('process');
    try {
      const result = await apiPost('/voice-admin/process', {
        source_audio: selectedFile.path,
        id: voiceId,
        start: 0,
        duration: 20,
      });
      setReferenceAudio(result.reference_audio);
      setMessage(`清洗裁剪完成：${result.reference_audio}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '清洗裁剪失败');
    } finally {
      setBusy('');
    }
  };

  const transcribe = async () => {
    const audio = referenceAudio || selectedFile?.path;
    if (!audio) return;
    setBusy('transcribe');
    try {
      const result = await apiPost('/voice-admin/transcribe', { audio_path: audio });
      setReferenceText(result.text || '');
      setMessage('参考文本已自动识别，请检查后保存');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '自动识别失败，可手动填写');
    } finally {
      setBusy('');
    }
  };

  const saveVoice = async () => {
    if (!selectedFile) return;
    setBusy('save');
    try {
      const saved = await apiPost('/voice-admin/voices', {
        id: voiceId,
        name: voiceName,
        source_audio: selectedFile.path,
        reference_audio: referenceAudio || selectedFile.path,
        reference_text: referenceText,
        enabled: true,
      });
      setTestVoice(saved.id);
      loadStyleForm(saved.id, { ...voiceStyles, [saved.id]: voiceStyles[saved.id] || currentStyle() });
      setMessage(`音色 ${saved.name} 已保存`);
      await refreshAll();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '保存音色失败');
    } finally {
      setBusy('');
    }
  };

  const saveStyle = async () => {
    if (!styleVoice.trim()) return;
    setBusy('style-save');
    try {
      const nextStyles = { ...voiceStyles, [styleVoice.trim()]: currentStyle() };
      await apiPost('/voice-admin/styles', { styles: nextStyles });
      setVoiceStyles(nextStyles);
      setMessage(`音色风格 ${styleVoice.trim()} 已保存`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '保存风格失败');
    } finally {
      setBusy('');
    }
  };

  const previewStyle = async () => {
    if (!styleVoice.trim() || !stylePreviewText.trim()) return;
    setBusy('style-preview');
    try {
      const nextStyles = { ...voiceStyles, [styleVoice.trim()]: currentStyle() };
      const result = await apiPost('/voice-admin/styles/preview', {
        voice: styleVoice.trim(),
        text: stylePreviewText,
        styles: nextStyles,
        max_tts_chars: styleMaxTtsChars,
      });
      setStylePreview(result);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '预览失败');
    } finally {
      setBusy('');
    }
  };

  const testGenerate = async () => {
    setBusy('test');
    setAudioUrl(null);
    try {
      const result: TTSResponse = await apiPost('/tts', {
        text: testText,
        provider: 'local-first',
        voice: testVoice || undefined,
        format: 'wav',
        cache: false,
      });
      if (!result.success || !result.audio_url) {
        throw new Error(result.error || '生成失败');
      }
      setAudioUrl(result.audio_url.startsWith('http') ? result.audio_url : `${apiBase}${result.audio_url}`);
      setMessage(`生成完成，实际使用：${result.actual_provider || result.provider}`);
      const historyData = await apiGet('/history');
      setHistory(historyData.items || []);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '生成失败');
    } finally {
      setBusy('');
    }
  };

  const logout = () => {
    localStorage.removeItem('authToken');
    setIsAuthenticated(false);
  };

  const qwenStatus = statuses.find((item) => item.service === 'qwen-local');
  const fallbackStatus = statuses.find((item) => item.service === 'aliyun-zhimi');
  const configuredVoices = Object.values(voices);
  const hasProcessedAudio = Boolean(selectedFile && referenceAudio && referenceAudio !== selectedFile.path);

  if (isCheckingAuth) {
    return (
      <main className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Loader2 className="h-7 w-7 animate-spin text-teal-700" />
      </main>
    );
  }

  if (!isAuthenticated) {
    return <Login apiBase={apiBase} onLogin={setIsAuthenticated} />;
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-teal-700 text-white">
              <Volume2 className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-semibold">语音中心</h1>
              <p className="text-sm text-slate-500">管理克隆音色、测试生成、配置保底 TTS</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={refreshAll} className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-100">
              <RefreshCw className="h-4 w-4" />
              刷新
            </button>
            <button onClick={logout} className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-100">
              <LogOut className="h-4 w-4" />
              退出
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-5 py-5">
        {message && (
          <div className="fixed bottom-5 right-5 z-50 max-w-md rounded-md border border-teal-200 bg-white px-4 py-3 text-sm text-slate-900 shadow-lg">
            <div className="font-medium">操作提示</div>
            <div className="mt-1 break-words text-slate-600">{message}</div>
            <button onClick={() => setMessage('')} className="mt-2 text-xs text-teal-700 hover:text-teal-900">
              关闭
            </button>
          </div>
        )}

        <section className="mb-5 grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="rounded-md border border-slate-200 bg-white p-4">
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Sparkles className="h-4 w-4" />
              本机 Qwen
            </div>
            <div className="mt-2 text-2xl font-semibold">{qwenStatus ? statusText(qwenStatus.status) : '未知'}</div>
            <div className="mt-1 text-xs text-slate-500">{qwenStatus?.latency ? `${qwenStatus.latency} ms` : qwenStatus?.error || '用于克隆音色'}</div>
          </div>
          <div className="rounded-md border border-slate-200 bg-white p-4">
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <ShieldCheck className="h-4 w-4" />
              保底 TTS
            </div>
            <div className="mt-2 text-2xl font-semibold">{fallbackStatus ? statusText(fallbackStatus.status) : '未知'}</div>
            <div className="mt-1 text-xs text-slate-500">当前为阿里云，可继续扩展其他 provider</div>
          </div>
          <div className="rounded-md border border-slate-200 bg-white p-4">
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <CheckCircle2 className="h-4 w-4" />
              已配置音色
            </div>
            <div className="mt-2 text-2xl font-semibold">{configuredVoices.length}</div>
            <div className="mt-1 text-xs text-slate-500">Hermes/OpenClaw 使用音色 ID 调用</div>
          </div>
        </section>

        <section className="mb-5 rounded-md border border-slate-200 bg-white p-5">
          <div className="mb-3 flex items-center gap-2">
            <FolderOpen className="h-5 w-5 text-teal-700" />
            <h2 className="text-lg font-semibold">音频目录</h2>
          </div>
          <div className="flex flex-col gap-3 md:flex-row">
            <input
              value={voicesDir}
              onChange={(event) => setVoicesDir(event.target.value)}
              className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder="例如 D:\aiData\voices"
            />
            <button onClick={saveDirectory} disabled={busy === 'directory'} className="inline-flex items-center justify-center gap-2 rounded-md bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:bg-slate-400">
              {busy === 'directory' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              保存目录
            </button>
          </div>
          <p className="mt-2 text-sm text-slate-500">把授权音频放进这个目录，点击刷新后会出现在下面列表。</p>
        </section>

        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[380px_1fr]">
          <section className="rounded-md border border-slate-200 bg-white p-5">
            <h2 className="mb-4 text-lg font-semibold">音频列表</h2>
            <div className="space-y-2">
              {voiceFiles.length === 0 && <div className="text-sm text-slate-500">目录里还没有可用音频。</div>}
              {voiceFiles.map((file) => (
                <button
                  key={file.path}
                  onClick={() => selectFile(file)}
                  className={`w-full rounded-md border px-3 py-3 text-left hover:bg-slate-50 ${selectedFile?.path === file.path ? 'border-teal-600 bg-teal-50' : 'border-slate-200 bg-white'}`}
                >
                  <div className="font-medium">{file.file_name}</div>
                  <div className="mt-1 text-xs text-slate-500">{file.configured ? `已配置：${file.config?.name || file.id}` : '未配置'}</div>
                </button>
              ))}
            </div>
          </section>

          <section className="rounded-md border border-slate-200 bg-white p-5">
            <h2 className="mb-4 text-lg font-semibold">生成音色配置</h2>
            {!selectedFile ? (
              <div className="text-sm text-slate-500">先从左侧选择一个音频。</div>
            ) : (
              <div className="space-y-4">
                <audio controls src={`${apiBase}/voice-admin/audio-file?path=${encodeURIComponent(selectedFile.path)}`} className="w-full" />
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <label className="text-sm font-medium">
                    音色 ID
                    <input value={voiceId} onChange={(event) => setVoiceId(event.target.value)} className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
                  </label>
                  <label className="text-sm font-medium">
                    显示名称
                    <input value={voiceName} onChange={(event) => setVoiceName(event.target.value)} className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
                  </label>
                </div>
                <label className="block text-sm font-medium">
                  参考音频
                  <input value={referenceAudio} onChange={(event) => setReferenceAudio(event.target.value)} className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
                </label>
                {hasProcessedAudio && (
                  <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3">
                    <div className="text-sm font-medium text-emerald-900">清洗裁剪后的参考音频</div>
                    <div className="mt-1 break-all text-xs text-emerald-800">{referenceAudio}</div>
                    <audio
                      controls
                      src={`${apiBase}/voice-admin/audio-file?path=${encodeURIComponent(referenceAudio)}`}
                      className="mt-3 w-full"
                    />
                  </div>
                )}
                <div className="flex flex-wrap gap-2">
                  <a
                    href="https://vocalremover.org/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-100"
                  >
                    <ExternalLink className="h-4 w-4" />
                    提取人声
                  </a>
                  <button onClick={processAudio} disabled={busy === 'process'} className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-100 disabled:bg-slate-100">
                    {busy === 'process' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Scissors className="h-4 w-4" />}
                    清洗裁剪 20 秒
                  </button>
                  <button onClick={transcribe} disabled={busy === 'transcribe'} className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-100 disabled:bg-slate-100">
                    {busy === 'transcribe' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                    {hasProcessedAudio ? '识别清洗后的文本' : '自动识别参考文本'}
                  </button>
                </div>
                <p className="text-sm text-slate-500">
                  自动识别可以直接用原音频，但建议先清洗裁剪；保存音色时会优先使用上方显示的清洗后参考音频。
                </p>
                <label className="block text-sm font-medium">
                  参考文本
                  <textarea value={referenceText} onChange={(event) => setReferenceText(event.target.value)} className="mt-2 h-28 w-full rounded-md border border-slate-300 px-3 py-2 text-sm leading-6" placeholder="这段参考音频实际说的话。可以自动识别，也可以手动修改。" />
                </label>
                <button onClick={saveVoice} disabled={busy === 'save'} className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-teal-700 px-4 py-3 text-sm font-semibold text-white hover:bg-teal-800 disabled:bg-slate-400">
                  {busy === 'save' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  保存为音色
                </button>
              </div>
            )}
          </section>
        </div>

        <section className="mt-5 rounded-md border border-slate-200 bg-white p-5">
          <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <h2 className="text-lg font-semibold">音色风格配置</h2>
            <div className="text-sm text-slate-500">单次 TTS 最多 {styleMaxTtsChars} 字，超出会自动拆分后拼接</div>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-[220px_140px_1fr]">
            <label className="text-sm font-medium">
              当前音色
              <div className="mt-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800">
                {styleVoice || '请先从左侧选择音频'}
              </div>
            </label>
            <label className="text-sm font-medium">
              每句最多字数
              <input
                type="number"
                min={8}
                max={80}
                value={styleMaxSentenceChars}
                onChange={(event) => setStyleMaxSentenceChars(Number(event.target.value))}
                className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="text-sm font-medium">
              固定前缀
              <input
                value={stylePrefix}
                onChange={(event) => setStylePrefix(event.target.value)}
                className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                placeholder="默认留空"
              />
            </label>
          </div>
          <label className="mt-4 inline-flex items-center gap-2 text-sm">
            <input type="checkbox" checked={styleEnabled} onChange={(event) => setStyleEnabled(event.target.checked)} />
            启用这个音色的风格整理
          </label>
          <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
            <label className="text-sm font-medium">
              常用词
              <textarea
                value={styleCommonWords}
                onChange={(event) => setStyleCommonWords(event.target.value)}
                className="mt-2 h-28 w-full rounded-md border border-slate-300 px-3 py-2 text-sm leading-6"
                placeholder="一行一个，当前只保存不自动乱插"
              />
            </label>
            <label className="text-sm font-medium">
              禁用词
              <textarea
                value={styleForbidden}
                onChange={(event) => setStyleForbidden(event.target.value)}
                className="mt-2 h-28 w-full rounded-md border border-slate-300 px-3 py-2 text-sm leading-6"
                placeholder="一行一个，出现就删除"
              />
            </label>
            <label className="text-sm font-medium">
              替换词
              <textarea
                value={styleReplacements}
                onChange={(event) => setStyleReplacements(event.target.value)}
                className="mt-2 h-28 w-full rounded-md border border-slate-300 px-3 py-2 text-sm leading-6"
                placeholder="好的=>好嘛"
              />
            </label>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-[1fr_1fr]">
            <label className="text-sm font-medium">
              预览文本
              <textarea
                value={stylePreviewText}
                onChange={(event) => setStylePreviewText(event.target.value)}
                className="mt-2 h-32 w-full rounded-md border border-slate-300 px-3 py-2 text-sm leading-6"
              />
            </label>
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="text-sm font-medium">整理后实际朗读文本</div>
              {stylePreview ? (
                <>
                  <pre className="mt-2 max-h-32 overflow-auto whitespace-pre-wrap rounded bg-white p-3 text-sm leading-6 text-slate-800">{stylePreview.styled_text}</pre>
                  <div className="mt-3 text-xs text-slate-500">分块：{stylePreview.lengths.join(' / ')} 字</div>
                </>
              ) : (
                <div className="mt-2 text-sm text-slate-500">点击预览后显示。</div>
              )}
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button onClick={previewStyle} disabled={busy === 'style-preview'} className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm hover:bg-slate-100 disabled:bg-slate-100">
              {busy === 'style-preview' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              预览整理
            </button>
            <button onClick={saveStyle} disabled={busy === 'style-save'} className="inline-flex items-center gap-2 rounded-md bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:bg-slate-400">
              {busy === 'style-save' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              保存风格
            </button>
          </div>
        </section>

        <section className="mt-5 rounded-md border border-slate-200 bg-white p-5">
          <h2 className="mb-4 text-lg font-semibold">测试生成</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-[240px_1fr]">
            <select value={testVoice} onChange={(event) => setTestVoice(event.target.value)} className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm">
              <option value="">默认音色</option>
              {configuredVoices.map((voice) => (
                <option key={voice.id} value={voice.id}>
                  {voice.name} ({voice.id})
                </option>
              ))}
            </select>
            <input value={testText} onChange={(event) => setTestText(event.target.value)} className="rounded-md border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <button onClick={testGenerate} disabled={busy === 'test'} className="mt-4 inline-flex items-center gap-2 rounded-md bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:bg-slate-400">
            {busy === 'test' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            生成试听
          </button>
          {audioUrl && <audio controls src={audioUrl.replace('/audio/', '/play/')} className="mt-4 w-full" />}
        </section>

        <section className="mt-5 rounded-md border border-slate-200 bg-white p-5">
          <h2 className="mb-4 text-lg font-semibold">最近生成记录</h2>
          {history.length === 0 ? (
            <div className="text-sm text-slate-500">还没有生成记录。</div>
          ) : (
            <div className="space-y-3">
              {history.map((item) => {
                const url = item.audio_url.startsWith('http') ? item.audio_url : `${apiBase}${item.audio_url}`;
                return (
                  <div key={item.id} className="rounded-md border border-slate-200 p-3">
                    <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
                      <div className="text-sm font-medium text-slate-900">{item.text}</div>
                      <div className="text-xs text-slate-500">{item.created_at}</div>
                    </div>
                    <div className="mt-1 text-xs text-slate-500">
                      音色：{item.voice || '默认'} | 实际后端：{item.actual_provider || item.provider} | 用时：{Math.round(item.duration)} ms
                    </div>
                    <audio controls src={url.replace('/audio/', '/play/')} className="mt-2 w-full" />
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </main>
  );
};

export default App;
