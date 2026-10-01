import { useEffect, useState, useCallback } from 'react';
import { getModelMetrics, getThresholdPreview } from '../lib/api';
import type { ModelMetrics, ThresholdPreview } from '../types/api';
import { Info, Sliders } from 'lucide-react';
import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer,
  Tooltip as ReTooltip,
} from 'recharts';

function MetricCard({ label, value, color, desc }: {
  label: string; value: string; color: string; desc: string;
}) {
  return (
    <div className="card p-4 flex flex-col gap-1">
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      <p className="text-sm font-medium text-slate-300">{label}</p>
      <p className="text-xs text-slate-500">{desc}</p>
    </div>
  );
}

function ConfusionMatrix({ tp, fp, tn, fn }: { tp: number; fp: number; tn: number; fn: number }) {
  return (
    <div className="inline-grid grid-cols-3 gap-1 text-xs">
      <div />
      <div className="text-center text-slate-500 py-1 font-semibold">Pred: Fraud</div>
      <div className="text-center text-slate-500 py-1 font-semibold">Pred: Legit</div>
      <div className="text-slate-500 font-semibold flex items-center">Actual: Fraud</div>
      <div className="bg-emerald-500/15 border border-emerald-500/30 rounded-lg p-3 text-center">
        <p className="text-emerald-400 font-bold text-lg">{tp}</p>
        <p className="text-emerald-600 text-[10px]">True Pos</p>
      </div>
      <div className="bg-rose-500/10 border border-rose-500/20 rounded-lg p-3 text-center">
        <p className="text-rose-400 font-bold text-lg">{fn}</p>
        <p className="text-rose-600 text-[10px]">False Neg</p>
      </div>
      <div className="text-slate-500 font-semibold flex items-center">Actual: Legit</div>
      <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-center">
        <p className="text-amber-400 font-bold text-lg">{fp}</p>
        <p className="text-amber-600 text-[10px]">False Pos</p>
      </div>
      <div className="bg-slate-500/10 border border-slate-700 rounded-lg p-3 text-center">
        <p className="text-slate-300 font-bold text-lg">{tn}</p>
        <p className="text-slate-500 text-[10px]">True Neg</p>
      </div>
    </div>
  );
}

export default function MetricsPage() {
  const [metrics, setMetrics] = useState<ModelMetrics | null>(null);
  const [preview, setPreview] = useState<ThresholdPreview | null>(null);
  const [threshold, setThreshold] = useState(0.5);
  const [loading, setLoading] = useState(true);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    getModelMetrics()
      .then((m) => {
        setMetrics(m);
        setThreshold(m.threshold);
        setPreview({
          threshold: m.threshold,
          precision: m.precision,
          recall: m.recall,
          false_positive_rate: m.false_positives / (m.false_positives + m.true_negatives) || 0,
          true_positives: m.true_positives,
          false_positives: m.false_positives,
          true_negatives: m.true_negatives,
          false_negatives: m.false_negatives,
        });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSlider = useCallback(async (val: number) => {
    setThreshold(val);
    setPreviewLoading(true);
    try {
      const p = await getThresholdPreview(val);
      setPreview(p);
    } catch {}
    finally { setPreviewLoading(false); }
  }, []);

  const radarData = metrics
    ? [
        { metric: 'Precision', value: metrics.precision * 100 },
        { metric: 'Recall', value: metrics.recall * 100 },
        { metric: 'F1', value: metrics.f1 * 100 },
        { metric: 'PR-AUC', value: metrics.pr_auc * 100 },
        { metric: 'ROC-AUC', value: metrics.roc_auc * 100 },
      ]
    : [];

  if (loading) return (
    <div className="flex-1 flex items-center justify-center">
      <span className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full spin-slow" />
    </div>
  );

  if (!metrics) return (
    <div className="flex-1 flex items-center justify-center text-slate-500">
      Model metrics unavailable. Train the model first.
    </div>
  );

  return (
    <div className="flex-1 overflow-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Model Metrics</h1>
        <p className="text-slate-400 text-sm mt-0.5">XGBoost trained on 50,000 synthetic transactions · All data is synthetic</p>
      </div>

      {/* Why not accuracy */}
      <div className="card p-4 border-indigo-500/20 bg-indigo-500/5 flex gap-3">
        <Info className="w-5 h-5 text-indigo-400 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-slate-300">
          <p className="font-semibold text-indigo-300 mb-1">Why we don't headline accuracy</p>
          <p className="text-slate-400 leading-relaxed">
            With ~2% fraud rate, a model that predicts "legitimate" for every transaction achieves 98% accuracy
            — yet catches zero fraud. We optimize instead for <strong className="text-slate-300">Precision</strong> (fewer false alarms)
            and <strong className="text-slate-300">Recall</strong> (fewer missed frauds), summarized by{' '}
            <strong className="text-slate-300">F1</strong> and <strong className="text-slate-300">PR-AUC</strong>.
          </p>
        </div>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Precision" value={(metrics.precision * 100).toFixed(1) + '%'} color="text-emerald-400" desc="Of flagged txns, how many are real fraud" />
        <MetricCard label="Recall" value={(metrics.recall * 100).toFixed(1) + '%'} color="text-blue-400" desc="Of real fraud, how many we caught" />
        <MetricCard label="F1 Score" value={(metrics.f1 * 100).toFixed(1) + '%'} color="text-indigo-400" desc="Harmonic mean of precision & recall" />
        <MetricCard label="PR-AUC" value={metrics.pr_auc.toFixed(4)} color="text-purple-400" desc="Area under precision-recall curve" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Radar chart */}
        <div className="card-glow p-5">
          <p className="text-sm font-semibold text-slate-300 mb-4">Performance Radar</p>
          <ResponsiveContainer width="100%" height={240}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#1e293b" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: '#64748b', fontSize: 12 }} />
              <Radar
                name="Score"
                dataKey="value"
                stroke="#6366f1"
                fill="#6366f1"
                fillOpacity={0.25}
                strokeWidth={2}
              />
              <ReTooltip
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
              formatter={((v: unknown) => [`${typeof v === 'number' ? v.toFixed(1) : String(v)}%`, 'Score']) as any}
                contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: '#94a3b8' }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Confusion matrix */}
        <div className="card-glow p-5">
          <p className="text-sm font-semibold text-slate-300 mb-4">Confusion Matrix (threshold={metrics.threshold})</p>
          <ConfusionMatrix
            tp={metrics.true_positives}
            fp={metrics.false_positives}
            tn={metrics.true_negatives}
            fn={metrics.false_negatives}
          />
        </div>
      </div>

      {/* Threshold slider */}
      <div className="card-glow p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-indigo-400" />
          <p className="text-sm font-semibold text-slate-300">Live Threshold Preview</p>
          <span className="ml-auto text-xs text-slate-500">
            Computed on the held-out test set
          </span>
        </div>
        <p className="text-xs text-slate-400">
          Drag to see how the threshold affects precision, recall, and false-positive rate. Lower threshold = flag more (higher recall, lower precision).
        </p>

        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>0.01 (flag everything)</span>
            <span className="text-indigo-400 font-semibold text-sm">Threshold: {threshold.toFixed(2)}</span>
            <span>0.99 (flag nothing)</span>
          </div>
          <input
            id="threshold-slider"
            type="range"
            min={0.01}
            max={0.99}
            step={0.01}
            value={threshold}
            onChange={(e) => handleSlider(parseFloat(e.target.value))}
            className="w-full accent-indigo-500"
          />
        </div>

        {preview && (
          <div className={`grid grid-cols-3 gap-4 ${previewLoading ? 'opacity-50' : ''} transition-opacity`}>
            {[
              { label: 'Precision', value: (preview.precision * 100).toFixed(1) + '%', color: 'text-emerald-400' },
              { label: 'Recall', value: (preview.recall * 100).toFixed(1) + '%', color: 'text-blue-400' },
              { label: 'False Positive Rate', value: (preview.false_positive_rate * 100).toFixed(1) + '%', color: 'text-amber-400' },
            ].map(({ label, value, color }) => (
              <div key={label} className="card p-3 text-center">
                <p className={`text-xl font-bold ${color}`}>{value}</p>
                <p className="text-xs text-slate-500 mt-0.5">{label}</p>
              </div>
            ))}
            <div className="card p-3 text-center col-span-3 grid grid-cols-4 gap-2 text-xs">
              {[
                { label: 'TP', val: preview.true_positives, color: 'text-emerald-400' },
                { label: 'FP', val: preview.false_positives, color: 'text-amber-400' },
                { label: 'FN', val: preview.false_negatives, color: 'text-rose-400' },
                { label: 'TN', val: preview.true_negatives, color: 'text-slate-300' },
              ].map(({ label, val, color }) => (
                <div key={label}>
                  <p className={`font-bold text-base ${color}`}>{val}</p>
                  <p className="text-slate-600">{label}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
