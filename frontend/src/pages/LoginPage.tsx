import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Shield, Eye, EyeOff, Zap, AlertCircle,
} from 'lucide-react';
import { login } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';

export default function LoginPage() {
  const [email, setEmail] = useState('demo@fraudlens.app');
  const [password, setPassword] = useState('Demo@1234');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { setAuth } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await login({ email, password });
      setAuth(res.access_token, res.role, res.email);
      navigate('/dashboard');
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? 'Login failed. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = (role: 'analyst' | 'admin') => {
    if (role === 'analyst') {
      setEmail('demo@fraudlens.app');
      setPassword('Demo@1234');
    } else {
      setEmail('admin@fraudlens.app');
      setPassword('Admin@1234');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      <div className="absolute inset-0 bg-[rgb(11,15,25)]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(99,102,241,0.12),transparent_60%)]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_right,rgba(16,185,129,0.06),transparent_50%)]" />
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: 'linear-gradient(rgba(148,163,184,1) 1px,transparent 1px),linear-gradient(90deg,rgba(148,163,184,1) 1px,transparent 1px)',
          backgroundSize: '60px 60px',
        }}
      />

      <div className="relative z-10 w-full max-w-md px-4">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 mb-4 shadow-lg shadow-indigo-900/30">
            <Shield className="w-8 h-8 text-indigo-400" />
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">FraudLens</h1>
          <p className="text-slate-400 mt-1 text-sm">Explainable Fraud Review Assistant</p>
        </div>

        <div className="mb-6 flex items-start gap-2 bg-amber-500/10 border border-amber-500/20 rounded-lg px-4 py-3">
          <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <p className="text-amber-300/80 text-xs">
            <span className="font-semibold text-amber-300">Demo only.</span>{' '}
            All data is 100% synthetic. FraudLens supports human analysts; it does not block payments automatically.
          </p>
        </div>

        <div className="mb-6 card p-4">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-indigo-400" />
            Demo Credentials (click to fill)
          </p>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => fillDemo('analyst')}
              className="text-left p-2.5 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 hover:border-indigo-500/40 transition-all"
            >
              <div className="text-xs font-medium text-indigo-400 mb-0.5">Analyst</div>
              <div className="text-[11px] text-slate-400 font-mono">demo@fraudlens.app</div>
              <div className="text-[11px] text-slate-500 font-mono">Demo@1234</div>
            </button>
            <button
              onClick={() => fillDemo('admin')}
              className="text-left p-2.5 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 hover:border-purple-500/40 transition-all"
            >
              <div className="text-xs font-medium text-purple-400 mb-0.5">Admin</div>
              <div className="text-[11px] text-slate-400 font-mono">admin@fraudlens.app</div>
              <div className="text-[11px] text-slate-500 font-mono">Admin@1234</div>
            </button>
          </div>
        </div>

        <div className="card-glow p-6">
          <h2 className="text-lg font-semibold text-white mb-6">Sign in to your account</h2>

          {error && (
            <div className="mb-4 flex items-center gap-2 bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2.5 text-rose-400 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1.5">Email</label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input"
                placeholder="analyst@fraudlens.app"
                required
                autoComplete="email"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1.5">Password</label>
              <div className="relative">
                <input
                  id="login-password"
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input pr-10"
                  required
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                  tabIndex={-1}
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <button
              id="login-submit"
              type="submit"
              disabled={loading}
              className="btn-primary w-full justify-center py-2.5 text-base"
            >
              {loading ? (
                <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full spin-slow" />
              ) : (
                <Shield className="w-4 h-4" />
              )}
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
