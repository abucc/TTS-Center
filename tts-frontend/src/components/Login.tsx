import React, { useState } from 'react';
import { Lock, Eye, EyeOff, User } from 'lucide-react';

interface LoginProps {
  onLogin: (success: boolean) => void;
}

const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('authToken', data.token);
        onLogin(true);
      } else {
        const errorData = await response.json();
        setError(errorData.message || 'Invalid credentials');
      }
    } catch (error) {
      setError('Connection error. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-indigo-900 relative overflow-hidden flex items-center justify-center p-4">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-1/2 -left-1/2 w-full h-full bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-1/2 -right-1/2 w-full h-full bg-gradient-to-br from-purple-500/10 to-pink-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
      </div>

      <div className="relative z-10 max-w-md w-full bg-white/10 backdrop-blur-md rounded-2xl shadow-2xl border border-white/20 p-8 transition-all duration-300 hover:bg-white/15">
        <div className="text-center mb-8">
          <div className="mx-auto w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center mb-6 shadow-2xl animate-bounce">
            <Lock className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent mb-4">
            🎤 Awesome TTS
          </h1>
          <p className="text-purple-200 text-lg font-medium">
            Please sign in to access the TTS system
          </p>
          <div className="mt-4 w-24 h-1 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full mx-auto"></div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="username" className="block text-sm font-bold text-purple-200 mb-3">
              👤 Username
            </label>
            <div className="relative">
              <div className="absolute left-3 top-1/2 transform -translate-y-1/2 w-6 h-6 bg-purple-500/20 rounded-lg flex items-center justify-center">
                <User className="text-purple-300 w-4 h-4" />
              </div>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full pl-12 pr-4 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl text-white placeholder-purple-300 focus:ring-2 focus:ring-purple-400 focus:border-purple-400 transition-all duration-300"
                placeholder="Enter your username..."
                required
              />
            </div>
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-bold text-purple-200 mb-3">
              🔒 Password
            </label>
            <div className="relative">
              <div className="absolute left-3 top-1/2 transform -translate-y-1/2 w-6 h-6 bg-purple-500/20 rounded-lg flex items-center justify-center">
                <Lock className="text-purple-300 w-4 h-4" />
              </div>
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-12 pr-14 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl text-white placeholder-purple-300 focus:ring-2 focus:ring-purple-400 focus:border-purple-400 transition-all duration-300"
                placeholder="Enter your password..."
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 w-8 h-8 bg-white/10 rounded-lg flex items-center justify-center text-purple-300 hover:text-white hover:bg-white/20 transition-all duration-300"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {error && (
            <div className="bg-red-500/20 backdrop-blur-sm border border-red-400/30 text-red-200 px-4 py-3 rounded-xl flex items-center">
              <span className="text-xl mr-3">❌</span>
              <span className="font-medium">{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading || !username || !password}
            className="w-full bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 hover:from-blue-700 hover:via-purple-700 hover:to-pink-700 disabled:from-gray-600 disabled:via-gray-700 disabled:to-gray-800 text-white font-bold py-4 px-8 rounded-xl transition-all duration-300 flex items-center justify-center shadow-2xl hover:shadow-purple-500/25 hover:scale-105 disabled:scale-100 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <div className="w-6 h-6 border-3 border-white/30 border-t-white rounded-full animate-spin mr-3"></div>
                <span className="text-lg">✨ Signing in...</span>
              </>
            ) : (
              <>
                <div className="w-6 h-6 bg-white/20 rounded-lg flex items-center justify-center mr-3">
                  <span className="text-sm">🚀</span>
                </div>
                <span className="text-lg">🎤 Sign In</span>
              </>
            )}
          </button>

          <div className="text-center text-purple-300 text-sm">
            <p>✨ Default credentials: admin / password</p>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Login;