import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authApi } from '../api/auth';
import { useAuthStore } from '../store/authStore';

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { login, setError, error } = useAuthStore();
  const [workspaceName, setWorkspaceName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { data } = await authApi.register({
        workspace_name: workspaceName,
        email,
        password,
      });
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
        'Registration failed. Please try again.';
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
          <p className="text-slate-400 text-sm">Create your fabrication workspace</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-xl shadow-black/40">
          <h2 className="text-xl font-semibold text-white mb-6">Create workspace</h2>

          {error && (
            <div className="mb-4 px-4 py-3 bg-red-950/60 border border-red-800 rounded-lg text-red-300 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="register-workspace" className="block text-sm font-medium text-slate-300 mb-1.5">
                Workspace Name
              </label>
              <input
                id="register-workspace"
                data-testid="register-workspace"
                type="text"
                required
                minLength={2}
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500 transition"
                placeholder="Virgin Surfaces — Plant 1"
              />
            </div>
            <div>
              <label htmlFor="register-email" className="block text-sm font-medium text-slate-300 mb-1.5">
                Email
              </label>
              <input
                id="register-email"
                data-testid="register-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500 transition"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label htmlFor="register-password" className="block text-sm font-medium text-slate-300 mb-1.5">
                Password
              </label>
              <input
                id="register-password"
                data-testid="register-password"
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-slate-200 text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-violet-500 transition"
                placeholder="Min 8 characters"
              />
            </div>

            <button
              type="submit"
              data-testid="register-submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-medium rounded-lg transition-all duration-200 disabled:opacity-50 shadow-lg shadow-violet-500/20"
            >
              {loading ? 'Creating workspace…' : 'Create Workspace'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            Already have an account?{' '}
            <Link to="/login" className="text-violet-400 hover:text-violet-300 transition-colors">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};
