import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { healthApi, type HealthResponse } from '../api/auth';

export const DashboardPage: React.FC = () => {
  const { user, tenantId, logout } = useAuthStore();
  const navigate = useNavigate();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);

  useEffect(() => {
    healthApi
      .check()
      .then(({ data }) => setHealth(data))
      .catch(() => setHealth(null))
      .finally(() => setHealthLoading(false));
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const dbBadge = (db: string | undefined) => {
    if (!db) return null;
    const isCloud = db.includes('cloudsql');
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
          isCloud
            ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
            : 'bg-slate-800 text-slate-400 border border-slate-700'
        }`}
      >
        <span className={`w-1.5 h-1.5 rounded-full ${isCloud ? 'bg-emerald-400' : 'bg-slate-400'}`} />
        {db}
      </span>
    );
  };

  const quickShapes: Array<{ label: string; shape: string; icon: string }> = [
    { label: 'Rectangle', shape: 'rectangle', icon: '▭' },
    { label: 'Island', shape: 'island', icon: '⬚' },
    { label: 'Vanity', shape: 'vanity', icon: '▯' },
    { label: 'Straight Kitchen', shape: 'straight_kitchen', icon: '▬' },
    { label: 'L-Kitchen', shape: 'l_kitchen', icon: '⌐' },
  ];

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Top Nav */}
      <nav className="border-b border-slate-800 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">B</span>
            </div>
            <span className="text-white font-semibold">BuildDesk</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-slate-400 text-sm">{user?.email}</span>
            <button
              onClick={handleLogout}
              className="text-sm text-slate-400 hover:text-white transition-colors px-3 py-1.5 border border-slate-700 rounded-lg hover:border-slate-600"
            >
              Sign out
            </button>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-10">
        {/* Page header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-400 mt-1">Welcome back, {user?.email}</p>
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-10">
          {/* User card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3">Account</p>
            <p className="text-white font-medium truncate">{user?.email}</p>
            <p className="text-slate-400 text-sm mt-1">
              Role:{' '}
              <span className="capitalize text-violet-400 font-medium">{user?.role}</span>
            </p>
          </div>

          {/* Tenant card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3">Tenant</p>
            <p className="text-slate-300 text-xs font-mono break-all leading-relaxed">{tenantId}</p>
          </div>

          {/* Backend health card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3">Backend</p>
            {healthLoading ? (
              <p className="text-slate-500 text-sm animate-pulse">Checking…</p>
            ) : health ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  <span className="text-emerald-400 text-sm font-medium">Operational</span>
                </div>
                {dbBadge(health.database)}
                <p className="text-slate-500 text-xs">v{health.version}</p>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-red-400" />
                <span className="text-red-400 text-sm">Unreachable</span>
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-white mb-1">Generate Geometry</h2>
          <p className="text-slate-400 text-sm">Choose a surface type to open the workspace.</p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {quickShapes.map((s) => (
            <Link
              key={s.shape}
              to={`/workspace?shape=${s.shape}`}
              className="group bg-slate-900 border border-slate-800 rounded-xl p-5 text-center hover:border-violet-600 hover:bg-slate-800/70 transition-all duration-200 cursor-pointer"
            >
              <div className="text-3xl mb-3 text-slate-400 group-hover:text-violet-400 transition-colors">
                {s.icon}
              </div>
              <p className="text-sm font-medium text-slate-300 group-hover:text-white transition-colors">
                {s.label}
              </p>
            </Link>
          ))}
        </div>

        {/* Links */}
        <div className="mt-8 flex gap-4">
          <Link
            to="/workspace"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-violet-500/20"
          >
            Open Workspace
          </Link>
        </div>
      </div>
    </div>
  );
};
