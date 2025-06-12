import React, { useState, useEffect } from 'react';
import { Play, Download, Volume2, Settings, Mic, Loader2 } from 'lucide-react';

interface Voice {
  name: string;
  display_name: string;
}

interface TTSRequest {
  text: string;
  provider: string;
  voice?: string;
  speed: number;
  pitch: number;
  format: string;
  cache: boolean;
}

interface TTSResponse {
  success: boolean;
  provider: string;
  duration?: number;
  cached?: boolean;
  audio_url?: string;
  error?: string;
}

interface ServiceStatus {
  service: string;
  status: string;
  latency?: number;
  error?: string;
}

const App: React.FC = () => {
  const [text, setText] = useState("Hello! This is a test of the awesome TTS system with multiple providers and high-quality audio generation.");
  const [provider, setProvider] = useState("kokoro");
  const [voice, setVoice] = useState("");
  const [speed, setSpeed] = useState(1.0);
  const [pitch, setPitch] = useState(1.0);
  const [format, setFormat] = useState("wav");
  const [voices, setVoices] = useState<Voice[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [result, setResult] = useState<TTSResponse | null>(null);
  const [serviceStatuses, setServiceStatuses] = useState<ServiceStatus[]>([]);

  // Load voices when provider changes
  useEffect(() => {
    loadVoices();
  }, [provider]);

  const loadVoices = async () => {
    try {
      const response = await fetch(`/voices/${provider}`);
      if (response.ok) {
        const voicesData = await response.json();
        setVoices(Array.isArray(voicesData) ? voicesData : []);
        setVoice(""); // Reset voice selection
      }
    } catch (error) {
      console.error('Error loading voices:', error);
      setVoices([]);
    }
  };

  const generateSpeech = async () => {
    if (!text.trim()) return;

    setIsLoading(true);
    setResult(null);
    setAudioUrl(null);

    const request: TTSRequest = {
      text,
      provider,
      voice: voice || undefined,
      speed,
      pitch,
      format,
      cache: true
    };

    try {
      const response = await fetch('/tts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      const result: TTSResponse = await response.json();
      setResult(result);

      if (result.success && result.audio_url) {
        setAudioUrl(result.audio_url);
      }
    } catch (error) {
      setResult({
        success: false,
        provider,
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const checkServiceStatus = async () => {
    try {
      const response = await fetch('/status');
      if (response.ok) {
        const statuses: ServiceStatus[] = await response.json();
        setServiceStatuses(statuses);
      }
    } catch (error) {
      console.error('Error checking service status:', error);
    }
  };

  const downloadAudio = () => {
    if (audioUrl) {
      const link = document.createElement('a');
      link.href = audioUrl;
      link.download = `speech_${Date.now()}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const playAudio = () => {
    if (audioUrl) {
      // Replace /audio/ with /play/ for inline playback
      const playUrl = audioUrl.replace('/audio/', '/play/');
      const audio = new Audio(playUrl);
      audio.play().catch(console.error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return '✅';
      case 'unhealthy': return '⚠️';
      case 'error': return '❌';
      default: return '❓';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            🎤 Awesome TTS
          </h1>
          <p className="text-gray-600">
            Multi-provider Text-to-Speech with advanced features
          </p>
        </div>

        {/* Main TTS Interface */}
        <div className="max-w-4xl mx-auto">
          <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
            <h2 className="text-2xl font-semibold text-gray-800 mb-6 flex items-center">
              <Mic className="mr-2" />
              Generate Speech
            </h2>

            {/* Provider Selection */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  TTS Provider
                </label>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="kokoro">Kokoro ONNX</option>
                  <option value="chatterbox">Chatterbox TTS</option>
                  <option value="openai-edge-tts">OpenAI Edge TTS</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Voice
                </label>
                <select
                  value={voice}
                  onChange={(e) => setVoice(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">Default Voice</option>
                  {voices.map((v) => (
                    <option key={v.name} value={v.name}>
                      {v.display_name || v.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Text Input */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Text to Speech
              </label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Enter the text you want to convert to speech..."
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent h-32 resize-vertical"
              />
              <div className="text-sm text-gray-500 mt-1">
                {text.length} characters
              </div>
            </div>

            {/* Audio Controls */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Speed: {speed.toFixed(1)}x
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  value={speed}
                  onChange={(e) => setSpeed(parseFloat(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Pitch: {pitch.toFixed(1)}x
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  value={pitch}
                  onChange={(e) => setPitch(parseFloat(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Format
                </label>
                <select
                  value={format}
                  onChange={(e) => setFormat(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="wav">WAV</option>
                  <option value="mp3">MP3</option>
                </select>
              </div>
            </div>

            {/* Generate Button */}
            <button
              onClick={generateSpeech}
              disabled={isLoading || !text.trim()}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold py-3 px-6 rounded-lg transition duration-200 flex items-center justify-center"
            >
              {isLoading ? (
                <>
                  <Loader2 className="animate-spin mr-2" size={20} />
                  Generating...
                </>
              ) : (
                <>
                  <Volume2 className="mr-2" size={20} />
                  Generate Speech
                </>
              )}
            </button>
          </div>

          {/* Result */}
          {result && (
            <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
              <h3 className="text-xl font-semibold text-gray-800 mb-4">Result</h3>
              
              {result.success ? (
                <div>
                  <div className="flex items-center text-green-600 mb-4">
                    <span className="text-2xl mr-2">✅</span>
                    <div>
                      <div className="font-semibold">Speech generated successfully!</div>
                      <div className="text-sm text-gray-600">
                        Provider: {result.provider} | 
                        Duration: {result.duration}ms |
                        {result.cached && ' (Cached)'}
                      </div>
                    </div>
                  </div>

                  {audioUrl && (
                    <div className="space-y-4">
                      {/* Audio Player */}
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <audio 
                          controls 
                          src={audioUrl.replace('/audio/', '/play/')}
                          className="w-full"
                        >
                          Your browser does not support the audio element.
                        </audio>
                      </div>

                      {/* Action Buttons */}
                      <div className="flex flex-wrap gap-3">
                        <button
                          onClick={playAudio}
                          className="flex items-center bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition duration-200"
                        >
                          <Play className="mr-2" size={16} />
                          Play
                        </button>
                        
                        <button
                          onClick={downloadAudio}
                          className="flex items-center bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition duration-200"
                        >
                          <Download className="mr-2" size={16} />
                          Download
                        </button>

                        <a
                          href={audioUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg transition duration-200"
                        >
                          Open in New Tab
                        </a>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center text-red-600">
                  <span className="text-2xl mr-2">❌</span>
                  <div>
                    <div className="font-semibold">Generation failed</div>
                    <div className="text-sm">{result.error}</div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Service Status */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold text-gray-800 flex items-center">
                <Settings className="mr-2" />
                Service Status
              </h3>
              <button
                onClick={checkServiceStatus}
                className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg transition duration-200"
              >
                Refresh
              </button>
            </div>

            {serviceStatuses.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {serviceStatuses.map((status) => (
                  <div
                    key={status.service}
                    className="bg-gray-50 p-4 rounded-lg"
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-semibold capitalize">
                        {status.service}
                      </div>
                      <div className="text-2xl">
                        {getStatusIcon(status.status)}
                      </div>
                    </div>
                    <div className="text-sm text-gray-600 mt-1">
                      Status: {status.status}
                      {status.latency && ` (${status.latency}ms)`}
                      {status.error && (
                        <div className="text-red-600 mt-1">{status.error}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-gray-500 text-center py-4">
                Click "Refresh" to check service status
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
