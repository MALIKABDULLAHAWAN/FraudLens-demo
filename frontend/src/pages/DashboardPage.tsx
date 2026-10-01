import { useState, useEffect, type ElementType } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle, CheckCircle, Clock, Zap, RefreshCw,
  ChevronRight, Filter, X, Activity,
} from 'lucide-react';
import { getStats, getTransactions, simulateTransaction } from '../lib/api';
import type { StatsResponse, TransactionSummary, SimulateResponse } from '../types/api';
import { fmt, fmtDate, riskBadgeClass, statusBadgeClass } from '../lib/utils';

// ── KPI Card ──────────────────────────────────────────────────────────────────

function KpiCard({
  label, value, sub, icon: Icon, color,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: ElementType;
  color: string;
}) {
  return (
    <div className="card-glow p-5 flex items-start gap-4">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${color}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-2xl font-bold text-white">{value}</p>
        <p className="text-sm text-slate-400">{label}</p>
        {sub && <p className="text-xs text-slate-500 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

// ── Simulate Modal ────────────────────────────────────────────────────────────

function SimulateModal({ onClose }: { onClose: () => void }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimulateResponse | null>(null);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const run = async (kind: 'normal' | 'suspicious') => {
    setLoading(true);
    setError('');
    try {
      const res = await simulateTransaction(kind);
      setResult(res);
    } catch {
      setError('Simulation failed. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative glass rounded-2xl p-6 w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-indigo-400" />
            <h3 className="font-semibold text-white">Send Test Transaction</h3>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {!result ? (
          <>
            <p className="text-sm text-slate-400 mb-5">
              Generate a realistic synthetic transaction and score it live through the ML pipeline.
            </p>
            <div className="grid grid-cols-2 gap-3">
              <button
                id="simulate-normal"
                onClick={() => run('normal')}
                disabled={loading}
                className="btn-success justify-center py-3 flex-col gap-1 h-auto"
              >
                {loading ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full spin-slow" /> : <CheckCircle className="w-5 h-5" />}
                <span>Normal</span>
                <span className="text-xs opacity-70">Low-risk pattern</span>
              </button>
              <button
                id="simulate-suspicious"
                onClick={() => run('suspicious')}
                disabled={loading}
                className="btn-danger justify-center py-3 flex-col gap-1 h-auto"
              >
                {loading ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full spin-slow" /> : <AlertTriangle className="w-5 h-5" />}
                <span>Suspicious</span>
                <span className="text-xs opacity-70">High-risk pattern</span>
              </button>
            </div>
          </>
        ) : (
          <div className="space-y-4">
            <div className={`p-4 rounded-xl border ${result.transaction.is_flagged
              ? 'bg-rose-500/10 border-rose-500/20'
              : 'bg-emerald-500/10 border-emerald-500/20'}`}>
              <p className="text-sm font-medium text-white mb-2">{result.message}</p>
              <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
                <span>ID: <span className="text-slate-300 font-mono">{result.transaction.id}</span></span>
                <span>Score: <span className="text-slate-300 font-semibold">{((result.transaction.risk_score ?? 0) * 100).toFixed(1)}%</span></span>
                <span>Amount: <span className="text-slate-300">{fmt(result.transaction.amount)}</span></span>
                <span>Status: <span className="text-slate-300 capitalize">{result.transaction.status}</span></span>
              </div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setResult(null)} className="btn-ghost flex-1 justify-center">Run another</button>
              {result.transaction.is_flagged && (
                <button
                  id="view-case-link"
                  onClick={() => { navigate(`/case/${result.transaction.id}`); onClose(); }}
                  className="btn-primary flex-1 justify-center"
                >
                  View Case <ChevronRight className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        )}
        {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}
      </div>
    </div>
  );
}

// ── Main Dashboard ────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [txns, setTxns] = useState<TransactionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('');
  const [filterRisk, setFilterRisk] = useState('');
  const [showSimulate, setShowSimulate] = useState(false);
  const [page, setPage] = useState(1);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const [s, t] = await Promise.all([
        getStats(),
        getTransactions({
          status: filterStatus || undefined,
          risk_level: filterRisk || undefined,
          page,
          page_size: 20,
        }),
      ]);
      setStats(s);
      setTxns(t);
    } catch {
      /* handled by interceptor */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filterStatus, filterRisk, page]);

  return (
    <div className="flex-1 p-6 space-y-6 overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Review Dashboard</h1>
          <p className="text-slate-400 text-sm mt-0.5">All data is synthetic — demo environment</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={load} className="btn-ghost" title="Refresh">
            <RefreshCw className={`w-4 h-4 ${loading ? 'spin-slow' : ''}`} />
          </button>
          <button
            id="open-simulate-modal"
            onClick={() => setShowSimulate(true)}
            className="btn-primary"
          >
            <Zap className="w-4 h-4" />
            Send Test Transaction
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Flagged Today"
          value={stats?.flagged_today ?? '—'}
          icon={AlertTriangle}
          color="bg-rose-500/20 text-rose-400"
        />
        <KpiCard
          label="Pending Review"
          value={stats?.pending_review ?? '—'}
          icon={Clock}
          color="bg-amber-500/20 text-amber-400"
        />
        <KpiCard
          label="Approved"
          value={stats?.approved ?? '—'}
          sub={`${stats?.rejected ?? 0} rejected`}
          icon={CheckCircle}
          color="bg-emerald-500/20 text-emerald-400"
        />
        <KpiCard
          label="Flag Rate"
          value={stats ? `${(stats.flagged_rate * 100).toFixed(1)}%` : '—'}
          sub={stats?.avg_review_time_minutes ? `Avg review: ${stats.avg_review_time_minutes.toFixed(0)}m` : undefined}
          icon={Activity}
          color="bg-indigo-500/20 text-indigo-400"
        />
      </div>

      {/* Queue Table */}
      <div className="card-glow overflow-hidden">
        {/* Filters */}
        <div className="flex items-center gap-3 p-4 border-b border-slate-800">
          <Filter className="w-4 h-4 text-slate-500" />
          <select
            value={filterStatus}
            onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
            className="input w-36 py-1.5 text-xs"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="escalated">Escalated</option>
          </select>
          <select
            value={filterRisk}
            onChange={(e) => { setFilterRisk(e.target.value); setPage(1); }}
            className="input w-36 py-1.5 text-xs"
          >
            <option value="">All Risk Levels</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          {(filterStatus || filterRisk) && (
            <button onClick={() => { setFilterStatus(''); setFilterRisk(''); setPage(1); }} className="text-slate-500 hover:text-slate-300 transition-colors">
              <X className="w-4 h-4" />
            </button>
          )}
          <span className="ml-auto text-xs text-slate-500">{txns.length} transactions</span>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-800">
                {['Transaction ID', 'Customer', 'Amount', 'Merchant', 'Risk Score', 'Status', 'Time'].map((h) => (
                  <th key={h} className="px-4 py-3 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-slate-800/50">
                    {Array.from({ length: 7 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-3 bg-slate-800 rounded animate-pulse w-24" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : txns.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-slate-500">
                    No transactions found. Try{' '}
                    <button onClick={() => setShowSimulate(true)} className="text-indigo-400 hover:text-indigo-300 underline">
                      sending a test transaction
                    </button>.
                  </td>
                </tr>
              ) : (
                txns.map((tx) => (
                  <tr
                    key={tx.id}
                    className="table-row"
                    onClick={() => navigate(`/case/${tx.id}`)}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-indigo-400">{tx.id}</td>
                    <td className="px-4 py-3 text-slate-300 text-xs">{tx.customer_id}</td>
                    <td className="px-4 py-3 text-slate-200 font-medium">{fmt(tx.amount)}</td>
                    <td className="px-4 py-3 text-slate-400 capitalize">{tx.merchant_category.replace('_', ' ')}</td>
                    <td className="px-4 py-3">
                      {tx.risk_score !== null ? (
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all"
                              style={{
                                width: `${(tx.risk_score * 100).toFixed(0)}%`,
                                backgroundColor: tx.risk_score >= 0.8 ? '#f43f5e' :
                                  tx.risk_score >= 0.55 ? '#f97316' :
                                  tx.risk_score >= 0.3 ? '#f59e0b' : '#10b981',
                              }}
                            />
                          </div>
                          <span className={`text-xs font-semibold ${riskBadgeClass(tx.risk_level)} border-0 bg-transparent px-0 py-0`}>
                            {(tx.risk_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={statusBadgeClass(tx.status)}>{tx.status}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">{fmtDate(tx.timestamp)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {txns.length > 0 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="btn-ghost py-1 px-3 text-xs disabled:opacity-30"
            >
              Previous
            </button>
            <span className="text-xs text-slate-500">Page {page}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={txns.length < 20}
              className="btn-ghost py-1 px-3 text-xs disabled:opacity-30"
            >
              Next
            </button>
          </div>
        )}
      </div>

      {showSimulate && <SimulateModal onClose={() => { setShowSimulate(false); load(); }} />}
    </div>
  );
}
