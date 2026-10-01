import { scoreColor } from '../lib/utils';

interface Props {
  score: number | null;
  size?: number;
}

export default function RiskGauge({ score, size = 160 }: Props) {
  const s = score ?? 0;
  const radius = 54;
  const circumference = Math.PI * radius; // half circle arc
  const strokeDash = circumference * Math.min(Math.max(s, 0), 1);
  const color = scoreColor(score);
  const label = score === null ? 'N/A' :
    s >= 0.80 ? 'CRITICAL' :
    s >= 0.55 ? 'HIGH' :
    s >= 0.30 ? 'MEDIUM' : 'LOW';

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size / 2 + 20} viewBox="0 0 120 75">
        {/* Track */}
        <path
          d="M 10 65 A 54 54 0 0 1 110 65"
          fill="none"
          stroke="#1e293b"
          strokeWidth="10"
          strokeLinecap="round"
        />
        {/* Score arc */}
        <path
          d="M 10 65 A 54 54 0 0 1 110 65"
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${strokeDash} ${circumference}`}
          style={{ transition: 'stroke-dasharray 0.8s cubic-bezier(0.4,0,0.2,1), stroke 0.4s' }}
          filter={`drop-shadow(0 0 6px ${color}88)`}
        />
        {/* Score text */}
        <text x="60" y="58" textAnchor="middle" fontSize="20" fontWeight="700" fill="white">
          {score !== null ? (s * 100).toFixed(0) : '—'}
        </text>
        <text x="60" y="70" textAnchor="middle" fontSize="7" fill={color} fontWeight="600" letterSpacing="1">
          {label}
        </text>
      </svg>
      <p className="text-xs text-slate-500">Risk Score</p>
    </div>
  );
}
