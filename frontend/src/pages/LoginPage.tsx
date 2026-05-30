import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authApi } from '../api/auth';
import { useAuthStore } from '../store/authStore';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login, setError, error } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { data } = await authApi.login({ email, password });
      login(data.access_token, {
        user_id: data.user_id,
        tenant_id: data.tenant_id,
        email: data.email,
        role: data.role,
        is_active: true,
      });
      navigate('/dashboard');
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Login failed. Check your credentials.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/30">
              <span className="text-white font-bold text-lg">B</span>
            </div>
            <span className="text-2xl font-bold text-white tracking-tight">BuildDesk</span>
          </div>
          <p className="text-slate-400 text-sm">Sign in to your workspace</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-xl shadow-black/40">
          <h2 className="text-xl font-semibold text-white mb-6">Welcome back</h2>

          {error && (
            <div className="mb-4 px-4 py-3 bg-red-950/60 border border-red-800 rounded-lg text-red-300 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="login-email" className="block text-sm font-medium text-slate-300 mb-1.5">
                Email
              </label>
              <input
                id="login-email"
                data-testid="login-email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500 transition"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label htmlFor="login-password" className="block text-sm font-medium text-slate-300 mb-1.5">
                Password
              </label>
              <input
                id="login-password"
                data-testid="login-password"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500 transition"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              data-testid="login-submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-medium rounded-lg transition-all duration-200 disabled:opacity-50 shadow-lg shadow-violet-500/20"
            >
              {loading ? 'Signing in…' : 'Login'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            No account?{' '}
            <Link to="/register" className="text-violet-400 hover:text-violet-300 transition-colors">
              Create workspace
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};
