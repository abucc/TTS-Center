import React, { useState } from 'react';
import { Eye, EyeOff, Lock, LogIn, User } from 'lucide-react';

interface LoginProps {
  apiBase: string;
  onLogin: (success: boolean) => void;
}

const Login: React.FC<LoginProps> = ({ apiBase, onLogin }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await fetch(`${apiBase}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      const data = await response.json();
      if (response.ok && data.success && data.token) {
        localStorage.setItem('authToken', data.token);
        onLogin(true);
      } else {
        setError(data.message || '账号或密码不正确');
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : '连接语音中心失败');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 flex items-center justify-center px-4">
      <section className="w-full max-w-sm rounded-md border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-teal-700 text-white">
            <Lock className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">语音中心</h1>
            <p className="text-sm text-slate-500">登录后管理音色和 TTS 配置</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block text-sm font-medium text-slate-700">
            账号
            <div className="relative mt-2">
              <User className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                className="w-full rounded-md border border-slate-300 py-2 pl-9 pr-3 text-sm"
                autoComplete="username"
                required
              />
            </div>
          </label>

          <label className="block text-sm font-medium text-slate-700">
            密码
            <div className="relative mt-2">
              <Lock className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full rounded-md border border-slate-300 py-2 pl-9 pr-10 text-sm"
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword((value) => !value)}
                className="absolute right-2 top-1.5 rounded p-1 text-slate-500 hover:bg-slate-100"
                title={showPassword ? '隐藏密码' : '显示密码'}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </label>

          {error && <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

          <button
            type="submit"
            disabled={isLoading || !username || !password}
            className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {isLoading ? <Lock className="h-4 w-4" /> : <LogIn className="h-4 w-4" />}
            登录
          </button>
        </form>
      </section>
    </main>
  );
};

export default Login;
