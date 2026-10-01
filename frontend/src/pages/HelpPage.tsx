import { useNavigate } from 'react-router-dom';
import {
  Shield, Zap, CheckCircle, BarChart2, ExternalLink, AlertCircle,
  ArrowRight, HelpCircle,
} from 'lucide-react';

const steps = [
  {
    n: 1,
    title: 'Log in',
    desc: 'Use the demo credentials on the login page — click "Analyst" or "Admin" to fill them in automatically.',
    icon: Shield,
  },
  {
    n: 2,
    title: 'Send a test transaction',
    desc: 'Click "Send Test Transaction" on the dashboard, choose Normal or Suspicious, and watch the ML model score it in real time.',
    icon: Zap,
  },
  {
    n: 3,
    title: 'Review a case',
    desc: 'Click any flagged row to open the case detail: see the risk gauge, SHAP explanation, AI summary, and make an Approve / Reject / Escalate decision.',
    icon: CheckCircle,
  },
  {
    n: 4,
    title: 'Explore model metrics',
    desc: 'Visit the Model Metrics page to see precision, recall, F1, and drag the threshold slider to see its live effect on the test set.',
    icon: BarChart2,
  },
];

export default function HelpPage() {
  const navigate = useNavigate();

  return (
    <div className="flex-1 overflow-auto p-6 space-y-6 max-w-3xl">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <HelpCircle className="w-5 h-5 text-indigo-400" />
          <h1 className="text-2xl font-bold text-white">How to Test This Demo</h1>
        </div>
        <p className="text-slate-400 text-sm">Follow these 4 steps to explore every feature of FraudLens in under 5 minutes.</p>
      </div>

      {/* Synthetic data notice */}
      <div className="flex items-start gap-3 card p-4 border-amber-500/20 bg-amber-500/5">
        <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-amber-300/80">
          <span className="font-semibold text-amber-300">All data is 100% synthetic.</span>{' '}
          No real financial data, personal data, or payment information is used anywhere in this demo.
        </p>
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {steps.map((step) => {
          const Icon = step.icon;
          return (
            <div key={step.n} className="card-glow p-5 flex items-start gap-4">
              <div className="flex-shrink-0">
                <div className="w-9 h-9 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
                  <span className="text-indigo-400 font-bold text-sm">{step.n}</span>
                </div>
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Icon className="w-4 h-4 text-indigo-400" />
                  <h3 className="font-semibold text-white">{step.title}</h3>
                </div>
                <p className="text-sm text-slate-400 leading-relaxed">{step.desc}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 gap-3">
        <button onClick={() => navigate('/dashboard')} className="btn-primary justify-center py-3">
          <Zap className="w-4 h-4" /> Go to Dashboard
        </button>
        <button onClick={() => navigate('/metrics')} className="btn-ghost justify-center py-3">
          <BarChart2 className="w-4 h-4" /> View Model Metrics
        </button>
      </div>

      {/* What FraudLens is */}
      <div className="card-glow p-5 space-y-3">
        <h2 className="font-semibold text-white flex items-center gap-2">
          <Shield className="w-4 h-4 text-indigo-400" />
          About FraudLens
        </h2>
        <div className="text-sm text-slate-400 space-y-2 leading-relaxed">
          <p>
            FraudLens is a <strong className="text-slate-300">decision-support tool</strong> for fraud analysts.
            It scores transactions with an XGBoost ML model, explains each score using SHAP values,
            and generates plain-language summaries via an LLM (with template fallback when the LLM is unavailable).
          </p>
          <p>
            <strong className="text-slate-300 flex items-center gap-1">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
              FraudLens supports human analysts; it does not block payments automatically.
            </strong>
          </p>
        </div>
      </div>

      {/* Limitations */}
      <div className="card p-5 border-slate-700/40 space-y-2">
        <h3 className="text-sm font-semibold text-slate-300">Known Limitations</h3>
        <ul className="text-xs text-slate-500 space-y-1 list-disc list-inside">
          <li>Trained on synthetic data — not suitable for production fraud detection.</li>
          <li>The LLM explanation can hallucinate or be inaccurate; always verify manually.</li>
          <li>Perfect training metrics (P=R=F1=1.0) reflect synthetic patterns, not real-world performance.</li>
          <li>SQLite storage — replace with PostgreSQL for production workloads.</li>
          <li>Single-user demo auth — add proper identity management before production use.</li>
        </ul>
      </div>

      {/* GitHub link */}
      <a
        href="https://github.com/your-org/fraudlens"
        target="_blank"
        rel="noopener noreferrer"
        className="btn-ghost w-full justify-center"
      >
      <ExternalLink className="w-4 h-4" />
        View on GitHub
        <ArrowRight className="w-4 h-4 ml-auto" />
      </a>
    </div>
  );
}
