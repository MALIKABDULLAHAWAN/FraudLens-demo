import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine,
} from 'recharts';
import type { ShapFactor } from '../types/api';

interface Props {
  factors: ShapFactor[];
}

const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: { payload: ShapFactor }[] }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="glass rounded-lg px-3 py-2 text-xs space-y-1 max-w-[200px]">
      <p className="font-semibold text-slate-200">{d.readable_name}</p>
      <p className="text-slate-400">Feature value: <span className="text-slate-200">{d.feature_value}</span></p>
      <p className={d.direction === 'increases_risk' ? 'text-rose-400' : 'text-emerald-400'}>
        SHAP: {d.shap_value > 0 ? '+' : ''}{d.shap_value.toFixed(4)}
        {' '}({d.direction === 'increases_risk' ? '↑ risk' : '↓ risk'})
      </p>
    </div>
  );
};

export default function ShapChart({ factors }: Props) {
  if (!factors.length) return (
    <div className="flex items-center justify-center h-32 text-slate-500 text-sm">No SHAP data available</div>
  );

  const data = [...factors].sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value));

  return (
    <ResponsiveContainer width="100%" height={Math.max(160, data.length * 38)}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 40, top: 4, bottom: 4 }}>
        <XAxis
          type="number"
          tick={{ fill: '#64748b', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => v.toFixed(2)}
        />
        <YAxis
          type="category"
          dataKey="readable_name"
          width={160}
          tick={{ fill: '#94a3b8', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
        <ReferenceLine x={0} stroke="#334155" />
        <Bar dataKey="shap_value" radius={4} maxBarSize={20}>
          {data.map((entry, i) => (
            <Cell
              key={i}
              fill={entry.direction === 'increases_risk' ? '#f43f5e' : '#10b981'}
              fillOpacity={0.85}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
