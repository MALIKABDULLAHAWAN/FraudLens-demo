import { useEffect, useState, type ElementType, type ReactNode } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Bot, CheckCircle, XCircle, AlertTriangle, Clock,
  Globe, Smartphone, CreditCard, MapPin, TrendingUp, User,
} from 'lucide-react';
import { getTransaction, makeDecision } from '../lib/api';
import type { TransactionDetail } from '../types/api';
import RiskGauge from '../components/RiskGauge';
import ShapChart from '../components/ShapChart';
import { fmt, fmtDate, statusBadgeClass, cap } from '../lib/utils';


// ── Fact Row ──────────────────────────────────────────────────────────────────

function FactRow({ icon: Icon, label, value, highlight }: {
  icon: ElementType; label: string; value: ReactNode; highlight?: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-slate-800/60 last:border-0">
      <div className="flex items-center gap-2 text-slate-500 text-xs">
        <Icon className="w-3.5 h-3.5 flex-shrink-0" />
        {label}
      </div>
      <div className={`text-sm font-medium ${highlight ? 'text-rose-400' : 'text-slate-200'}`}>
        {value}
      </div>
    </div>
  );
}

// ── Decision Panel ────────────────────────────────────────────────────────────

function DecisionPanel({ txId, currentStatus, onDecision }: {
  txId: string; currentStatus: string; onDecision: () => void;
}) {
  const [action, setAction] = useState<'approve' | 'reject' | 'escalate' | null>(null);
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async () => {
    if (!action) return;
    setLoading(true);
    setError('');
    try {
      await makeDecision(txId, { action, note: note || undefined });
      onDecision();
    } catch (err: unknown) {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Decision failed');
    } finally {
      setLoading(false);
    }
  };

  if (currentStatus !== 'pending') {
    return (
      <div className={`flex items-center gap-2 px-4 py-3 rounded-xl border text-sm font-medium ${statusBadgeClass(currentStatus)} bg-transparent`}>
        <CheckCircle className="w-4 h-4" />
        Decision recorded: {cap(currentStatus)}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Analyst Decision</p>
      <p className="text-xs text-slate-500">
        FraudLens supports human analysts — you make the final call.
      </p>

      <div className="grid grid-cols-3 gap-2">
        {(['approve', 'reject', 'escalate'] as const).map((a) => {
          const classes = {
            approve: 'btn-success',
            reject: 'btn-danger',
            escalate: 'btn-warning',
          }[a];
          const icons = {
            approve: CheckCircle,
            reject: XCircle,
            escalate: AlertTriangle,
          }[a];
          const Icon = icons;
          return (
            <button
              key={a}
              id={`decision-${a}`}
              onClick={() => setAction(a === action ? null : a)}
              className={`${classes} justify-center py-2 ${action === a ? 'ring-2 ring-offset-2 ring-offset-slate-900' : 'opacity-70 hover:opacity-100'}`}
            >
              <Icon className="w-4 h-4" />
              {cap(a)}
            </button>
          );
        })}
      </div>

      {action && (
        <div className="space-y-2">
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={`Optional note for ${action} decision…`}
            className="input text-sm resize-none h-20"
          />
          {error && <p className="text-rose-400 text-xs">{error}</p>}
          <button
            onClick={submit}
            disabled={loading}
            className="btn-primary w-full justify-center"
          >
            {loading ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full spin-slow" /> : null}
            Confirm {cap(action)}
          </button>
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [tx, setTx] = useState<TransactionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    if (!id) return;
    try {
      const data = await getTransaction(id);
      setTx(data);
    } catch {
      setError('Transaction not found.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [id]);

  if (loading) return (
    <div className="flex-1 flex items-center justify-center">
      <span className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full spin-slow" />
    </div>
  );

  if (error || !tx) return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4">
      <AlertTriangle className="w-10 h-10 text-rose-400" />
      <p className="text-slate-400">{error || 'Not found'}</p>
      <button onClick={() => navigate('/dashboard')} className="btn-ghost">Back to Dashboard</button>
    </div>
  );

  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  return (
    <div className="flex-1 overflow-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/dashboard')} className="btn-ghost p-2">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-white font-mono">{tx.id}</h1>
            <span className={statusBadgeClass(tx.status)}>{tx.status}</span>
          </div>
          <p className="text-slate-500 text-xs mt-0.5">{fmtDate(tx.timestamp)}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Left: facts + gauge */}
        <div className="space-y-4">
          {/* Risk score gauge */}
          <div className="card-glow p-5 flex flex-col items-center">
            <RiskGauge score={tx.risk_score} size={180} />
            <div className="mt-3 w-full space-y-0.5">
              <FactRow icon={TrendingUp} label="Suggested action" value={
                <span className={`capitalize font-semibold ${
                  tx.suggested_action === 'escalate' ? 'text-amber-400' :
                  tx.suggested_action === 'review' ? 'text-orange-400' : 'text-emerald-400'
                }`}>{tx.suggested_action ?? '—'}</span>
              } />
            </div>
          </div>

          {/* Transaction facts */}
          <div className="card-glow p-5 space-y-0.5">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Transaction Details</p>
            <FactRow icon={TrendingUp} label="Amount" value={fmt(tx.amount)} highlight={tx.amount_vs_avg_ratio > 3} />
            <FactRow icon={TrendingUp} label="vs Customer Avg" value={`${tx.amount_vs_avg_ratio.toFixed(2)}×`} highlight={tx.amount_vs_avg_ratio > 3} />
            <FactRow icon={Globe} label="Country" value={tx.country} highlight={tx.is_foreign === 1} />
            <FactRow icon={MapPin} label="Distance from home" value={`${tx.distance_from_home_km.toFixed(0)} km`} highlight={tx.distance_from_home_km > 500} />
            <FactRow icon={Smartphone} label="New device" value={tx.device_is_new ? '⚠ Yes' : 'No'} highlight={!!tx.device_is_new} />
            <FactRow icon={CreditCard} label="Card present" value={tx.card_present ? 'Yes' : 'No (CNP)'} />
            <FactRow icon={Clock} label="Hour of day" value={`${tx.hour_of_day}:00 (${dayNames[tx.day_of_week]})`} highlight={tx.hour_of_day < 6} />
            <FactRow icon={TrendingUp} label="Txns last 1h" value={tx.txns_last_1h} highlight={tx.txns_last_1h > 3} />
            <FactRow icon={TrendingUp} label="Txns last 24h" value={tx.txns_last_24h} />
            <FactRow icon={User} label="Account age" value={`${tx.account_age_days} days`} />
          </div>
        </div>

        {/* Middle: SHAP + LLM summary */}
        <div className="space-y-4">
          {/* SHAP */}
          <div className="card-glow p-5">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
              SHAP Risk Factors <span className="normal-case text-slate-600 font-normal">(+ increases risk / − decreases risk)</span>
            </p>
            {tx.shap_factors && tx.shap_factors.length > 0 ? (
              <ShapChart factors={tx.shap_factors} />
            ) : (
              <p className="text-sm text-slate-500 py-4">No SHAP data available for this transaction.</p>
            )}
          </div>

          {/* LLM Summary */}
          <div className="card-glow p-5">
            <div className="flex items-center gap-2 mb-3">
              <Bot className="w-4 h-4 text-indigo-400" />
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">AI-Generated Explanation</p>
              {tx.summary_source && (
                <span className="ml-auto text-[10px] text-slate-600 bg-slate-800 px-2 py-0.5 rounded-full">
                  {tx.summary_source === 'llm' ? '🤖 LLM' : '📋 Template'}
                </span>
              )}
            </div>
            {tx.llm_summary ? (
              <p className="text-sm text-slate-300 leading-relaxed">{tx.llm_summary}</p>
            ) : (
              <p className="text-sm text-slate-500">No summary available for this transaction.</p>
            )}
            <p className="text-[10px] text-slate-600 mt-3 italic">
              AI explanations are for decision support only. Human analyst makes the final decision.
            </p>
          </div>
        </div>

        {/* Right: decision + merchant */}
        <div className="space-y-4">
          {/* Decision panel */}
          <div className="card-glow p-5">
            <DecisionPanel txId={tx.id} currentStatus={tx.status} onDecision={load} />
          </div>

          {/* Merchant + customer info */}
          <div className="card-glow p-5 space-y-0.5">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Context</p>
            <FactRow icon={Globe} label="Merchant category" value={<span className="capitalize">{tx.merchant_category.replace(/_/g,' ')}</span>} />
            <FactRow icon={User} label="Customer" value={tx.customer_id} />
            <FactRow icon={Globe} label="Home country" value={tx.customer_home_country} />
            <FactRow icon={TrendingUp} label="Avg spend (30d)" value={fmt(tx.avg_amount_30d)} />
          </div>
        </div>
      </div>
    </div>
  );
}
