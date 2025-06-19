import React, { useState, useEffect } from 'react';
import { Play, Download, Volume2, Settings, Mic, Loader2, LogOut } from 'lucide-react';
import Login from './components/Login';

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
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
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

  // Use /api prefix for all API calls (proxied to gateway)
  const API_PREFIX = '/api';

  // Check authentication on component mount
  useEffect(() => {
    checkAuth();
  }, []);

  // Load voices when provider changes
  useEffect(() => {
    if (isAuthenticated) {
      loadVoices();
    }
  }, [provider, isAuthenticated]);

  const checkAuth = async () => {
    const token = localStorage.getItem('authToken');
    if (!token) {
      setIsCheckingAuth(false);
      return;
    }

    try {
      const response = await fetch('/api/auth/verify', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        setIsAuthenticated(true);
      } else {
        localStorage.removeItem('authToken');
        setIsAuthenticated(false);
      }
    } catch (error) {
      localStorage.removeItem('authToken');
      setIsAuthenticated(false);
    } finally {
      setIsCheckingAuth(false);
    }
  };

  const handleLogin = (success: boolean) => {
    if (success) {
      setIsAuthenticated(true);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    setIsAuthenticated(false);
  };

  const loadVoices = async () => {
    try {
      const url = `${API_PREFIX}/voices/${provider}`;
      const response = await fetch(url);
      
      if (response.ok) {
        const voicesData = await response.json();
        setVoices(Array.isArray(voicesData) ? voicesData : []);
        setVoice(""); // Reset voice selection
      } else {
        setVoices([]);
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
      const response = await fetch(`${API_PREFIX}/tts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      const result: TTSResponse = await response.json();
      setResult(result);

      if (result.success && result.audio_url) {
        setAudioUrl(`${API_PREFIX}${result.audio_url}`);
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
      const url = `${API_PREFIX}/status`;
      const response = await fetch(url);
      
      if (response.ok) {
        const statuses: ServiceStatus[] = await response.json();
        setServiceStatuses(statuses);
      } else {
        setServiceStatuses([{
          service: 'gateway',
          status: 'error',
          error: `HTTP ${response.status}`
        }]);
      }
    } catch (error) {
      setServiceStatuses([{
        service: 'gateway',
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error'
      }]);
    }
  };

  // Check status on component mount
  useEffect(() => {
    checkServiceStatus();
  }, []);

  const downloadAudio = () => {
      if (audioUrl) {
        const link = document.createElement('a');
        link.href = audioUrl.startsWith('http') ? audioUrl : audioUrl;
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
        const audio = new Audio(playUrl.startsWith('http') ? playUrl : playUrl);
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

  // Show loading spinner while checking authentication
  if (isCheckingAuth) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-indigo-900 flex items-center justify-center">
        <div className="text-center">
          <div className="relative">
            <div className="w-16 h-16 rounded-full border-4 border-purple-400/30 border-t-purple-400 animate-spin mx-auto mb-6"></div>
            <div className="absolute inset-0 w-16 h-16 rounded-full border-4 border-transparent border-t-blue-400 animate-ping mx-auto"></div>
          </div>
          <p className="text-purple-100 text-lg font-medium">Loading awesome TTS...</p>
        </div>
      </div>
    );
  }

  // Show login form if not authenticated
  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-indigo-900 relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-1/2 -left-1/2 w-full h-full bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-1/2 -right-1/2 w-full h-full bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
      </div>
      
      <div className="relative z-10 container mx-auto px-4 py-8">
        {/* Header with Logout */}
        <div className="text-center mb-12 relative">
          <button
            onClick={handleLogout}
            className="absolute top-0 right-0 flex items-center text-purple-200 hover:text-red-400 transition-all duration-300 hover:scale-105 bg-white/10 backdrop-blur-sm rounded-lg px-3 py-2"
            title="Logout"
          >
            <LogOut className="w-5 h-5 mr-1" />
            Logout
          </button>
          
          <div className="mb-6">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full mb-4 shadow-2xl animate-bounce">
              <Volume2 className="w-10 h-10 text-white" />
            </div>
          </div>
          
          <h1 className="text-6xl font-bold bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent mb-4 animate-pulse">
            Awesome TTS
          </h1>
          <p className="text-purple-200 text-xl font-medium">
            Multi-provider Text-to-Speech with advanced features
          </p>
          <div className="mt-4 w-32 h-1 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full mx-auto"></div>
        </div>

        {/* Main TTS Interface */}
        <div className="max-w-4xl mx-auto">
          <div className="bg-white/10 backdrop-blur-md rounded-2xl shadow-2xl border border-white/20 p-8 mb-8 transition-all duration-300 hover:bg-white/15">
            <h2 className="text-3xl font-bold text-white mb-8 flex items-center">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center mr-3 shadow-lg">
                <Mic className="w-6 h-6 text-white" />
              </div>
              Generate Speech
            </h2>

            {/* Provider Selection */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              <div>
                <label className="block text-sm font-bold text-purple-200 mb-3">
                  🚀 TTS Provider
                </label>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="w-full p-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl text-white placeholder-purple-300 focus:ring-2 focus:ring-purple-400 focus:border-purple-400 transition-all duration-300"
                >
                  <option value="kokoro" className="bg-slate-800 text-white">🎭 Kokoro ONNX</option>
                  <option value="chatterbox" className="bg-slate-800 text-white">💬 Chatterbox TTS</option>
                  <option value="openai-edge-tts" className="bg-slate-800 text-white">🤖 OpenAI Edge TTS</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-bold text-purple-200 mb-3">
                  🎵 Voice Selection
                </label>
                <select
                  value={voice}
                  onChange={(e) => setVoice(e.target.value)}
                  className="w-full p-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl text-white placeholder-purple-300 focus:ring-2 focus:ring-purple-400 focus:border-purple-400 transition-all duration-300"
                >
                  <option value="" className="bg-slate-800 text-white">✨ Default Voice</option>
                  {voices.map((v) => (
                    <option key={v.name} value={v.name} className="bg-slate-800 text-white">
                      🎤 {v.display_name || v.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Text Input */}
            <div className="mb-8">
              <label className="block text-sm font-bold text-purple-200 mb-3">
                📝 Text to Speech
              </label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Enter the text you want to convert to speech... ✨"
                className="w-full p-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl text-white placeholder-purple-300 focus:ring-2 focus:ring-purple-400 focus:border-purple-400 transition-all duration-300 h-40 resize-vertical"
              />
              <div className="text-sm text-purple-300 mt-2 flex justify-between items-center">
                <span>📊 {text.length} characters</span>
                <span className="text-xs">Max recommended: 500 characters</span>
              </div>
            </div>

            {/* Audio Controls */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="bg-white/5 backdrop-blur-sm border border-white/20 rounded-xl p-4">
                <label className="block text-sm font-bold text-purple-200 mb-3">
                  ⚡ Speed: {speed.toFixed(1)}x
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  value={speed}
                  onChange={(e) => setSpeed(parseFloat(e.target.value))}
                  className="w-full h-2 bg-purple-800/50 rounded-lg appearance-none cursor-pointer slider-gradient"
                />
                <div className="flex justify-between text-xs text-purple-300 mt-1">
                  <span>0.5x</span>
                  <span>2.0x</span>
                </div>
              </div>

              <div className="bg-white/5 backdrop-blur-sm border border-white/20 rounded-xl p-4">
                <label className="block text-sm font-bold text-purple-200 mb-3">
                  🎵 Pitch: {pitch.toFixed(1)}x
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  value={pitch}
                  onChange={(e) => setPitch(parseFloat(e.target.value))}
                  className="w-full h-2 bg-purple-800/50 rounded-lg appearance-none cursor-pointer slider-gradient"
                />
                <div className="flex justify-between text-xs text-purple-300 mt-1">
                  <span>0.5x</span>
                  <span>2.0x</span>
                </div>
              </div>

              <div className="bg-white/5 backdrop-blur-sm border border-white/20 rounded-xl p-4">
                <label className="block text-sm font-bold text-purple-200 mb-3">
                  💾 Format
                </label>
                <select
                  value={format}
                  onChange={(e) => setFormat(e.target.value)}
                  className="w-full p-3 bg-white/10 backdrop-blur-sm border border-white/20 rounded-lg text-white focus:ring-2 focus:ring-purple-400 focus:border-purple-400 transition-all duration-300"
                >
                  <option value="wav" className="bg-slate-800 text-white">🎵 WAV (High Quality)</option>
                  <option value="mp3" className="bg-slate-800 text-white">📱 MP3 (Compressed)</option>
                </select>
              </div>
            </div>

            {/* Generate Button */}
            <button
              onClick={generateSpeech}
              disabled={isLoading || !text.trim()}
              className="w-full bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 hover:from-blue-700 hover:via-purple-700 hover:to-pink-700 disabled:from-gray-600 disabled:via-gray-700 disabled:to-gray-800 text-white font-bold py-4 px-8 rounded-xl transition-all duration-300 flex items-center justify-center shadow-2xl hover:shadow-purple-500/25 hover:scale-105 disabled:scale-100 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <div className="w-6 h-6 border-3 border-white/30 border-t-white rounded-full animate-spin mr-3"></div>
                  <span className="text-lg">✨ Generating Magic...</span>
                </>
              ) : (
                <>
                  <div className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center mr-3">
                    <Volume2 className="w-5 h-5 text-white" />
                  </div>
                  <span className="text-lg">🎤 Generate Speech</span>
                </>
              )}
            </button>
          </div>

          {/* Result */}
          {result && (
            <div className="bg-white/10 backdrop-blur-md rounded-2xl shadow-2xl border border-white/20 p-8 mb-8 transition-all duration-300 hover:bg-white/15">
              <h3 className="text-2xl font-bold text-white mb-6 flex items-center">
                <div className="w-8 h-8 bg-gradient-to-br from-green-500 to-blue-600 rounded-lg flex items-center justify-center mr-3 shadow-lg">
                  <span className="text-white text-lg">🎉</span>
                </div>
                Result
              </h3>
              
              {result.success ? (
                <div>
                  <div className="flex items-center text-green-400 mb-6">
                    <div className="w-12 h-12 bg-green-500/20 backdrop-blur-sm rounded-full flex items-center justify-center mr-4">
                      <span className="text-2xl">✨</span>
                    </div>
                    <div>
                      <div className="font-bold text-lg text-white">Speech generated successfully!</div>
                      <div className="text-sm text-purple-200">
                        🚀 Provider: {result.provider} |
                        ⚡ Duration: {result.duration}ms |
                        {result.cached && ' 💾 (Cached)'}
                      </div>
                    </div>
                  </div>

                  {audioUrl && (
                    <div className="space-y-6">
                      {/* Audio Player */}
                      <div className="bg-black/20 backdrop-blur-sm border border-white/10 p-6 rounded-xl">
                        <audio
                          controls
                          src={audioUrl.startsWith('http') ? audioUrl.replace('/audio/', '/play/') : audioUrl.replace('/audio/', '/play/')}
                          className="w-full h-12 bg-gradient-to-r from-purple-500 to-blue-500 rounded-lg"
                        >
                          Your browser does not support the audio element.
                        </audio>
                      </div>

                      {/* Action Buttons */}
                      <div className="flex flex-wrap gap-4">
                        <button
                          onClick={playAudio}
                          className="flex items-center bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white px-6 py-3 rounded-xl transition-all duration-300 shadow-lg hover:shadow-green-500/25 hover:scale-105"
                        >
                          <Play className="mr-2" size={18} />
                          <span className="font-medium">▶️ Play</span>
                        </button>
                        
                        <button
                          onClick={downloadAudio}
                          className="flex items-center bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-6 py-3 rounded-xl transition-all duration-300 shadow-lg hover:shadow-blue-500/25 hover:scale-105"
                        >
                          <Download className="mr-2" size={18} />
                          <span className="font-medium">💾 Download</span>
                        </button>

                        <a
                          href={audioUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center bg-gradient-to-r from-gray-600 to-slate-600 hover:from-gray-700 hover:to-slate-700 text-white px-6 py-3 rounded-xl transition-all duration-300 shadow-lg hover:shadow-gray-500/25 hover:scale-105"
                        >
                          <span className="font-medium">🔗 Open in New Tab</span>
                        </a>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center text-red-400">
                  <div className="w-12 h-12 bg-red-500/20 backdrop-blur-sm rounded-full flex items-center justify-center mr-4">
                    <span className="text-2xl">💥</span>
                  </div>
                  <div>
                    <div className="font-bold text-lg text-white">Generation failed</div>
                    <div className="text-sm text-red-300">{result.error}</div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Service Status */}
          <div className="bg-white/10 backdrop-blur-md rounded-2xl shadow-2xl border border-white/20 p-8 transition-all duration-300 hover:bg-white/15">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-2xl font-bold text-white flex items-center">
                <div className="w-8 h-8 bg-gradient-to-br from-orange-500 to-red-600 rounded-lg flex items-center justify-center mr-3 shadow-lg">
                  <Settings className="w-5 h-5 text-white" />
                </div>
                Service Status
              </h3>
              <button
                onClick={checkServiceStatus}
                className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white px-6 py-3 rounded-xl transition-all duration-300 shadow-lg hover:shadow-purple-500/25 hover:scale-105 font-medium"
              >
                🔄 Refresh
              </button>
            </div>

            {serviceStatuses.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {serviceStatuses.map((status) => (
                  <div
                    key={status.service}
                    className="bg-white/5 backdrop-blur-sm border border-white/20 p-6 rounded-xl transition-all duration-300 hover:bg-white/10"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="font-bold capitalize text-white text-lg">
                        🔧 {status.service}
                      </div>
                      <div className="text-3xl">
                        {getStatusIcon(status.status)}
                      </div>
                    </div>
                    <div className="text-sm text-purple-200">
                      📊 Status: <span className="font-medium">{status.status}</span>
                      {status.latency && <span className="text-blue-300"> ⚡ ({status.latency}ms)</span>}
                      {status.error && (
                        <div className="text-red-400 mt-2 font-medium">❌ {status.error}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-purple-300 text-center py-8 text-lg">
                <div className="w-16 h-16 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl">🔍</span>
                </div>
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
