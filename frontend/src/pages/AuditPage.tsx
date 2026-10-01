import { useEffect, useState } from 'react';
import { FileText, RefreshCw } from 'lucide-react';
import { getAuditLog } from '../lib/api';
import type { AuditLogEntry } from '../types/api';
import { fmtDate } from '../lib/utils';

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);

  const load = async () => {
    setLoading(true);
    try {
      const data = await getAuditLog(page);
      setLogs(data);
    } catch {}
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [page]);

  const eventColor = (type: string) => {
    if (type === 'decision_made') return 'text-indigo-400';
    if (type === 'login') return 'text-emerald-400';
    return 'text-slate-400';
  };

  return (
    <div className="flex-1 overflow-auto p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-purple-400" />
          <h1 className="text-2xl font-bold text-white">Audit Log</h1>
          <span className="text-xs bg-purple-500/20 text-purple-300 border border-purple-500/30 px-2 py-0.5 rounded-full">Admin only</span>
        </div>
        <button onClick={load} className="btn-ghost">
          <RefreshCw className={`w-4 h-4 ${loading ? 'spin-slow' : ''}`} />
        </button>
      </div>

      <div className="card-glow overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-800">
              <th className="px-4 py-3">Event</th>
              <th className="px-4 py-3">Transaction</th>
              <th className="px-4 py-3">Details</th>
              <th className="px-4 py-3">Time</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i} className="border-b border-slate-800/50">
                  {[1,2,3,4].map((j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-3 bg-slate-800 rounded animate-pulse w-32" />
                    </td>
                  ))}
                </tr>
              ))
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-12 text-center text-slate-500">No audit events yet.</td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium ${eventColor(log.event_type)}`}>
                      {log.event_type.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-indigo-400">
                    {log.transaction_id ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500 max-w-xs truncate">
                    {log.details ? JSON.stringify(log.details).substring(0, 80) : '—'}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-500 whitespace-nowrap">
                    {fmtDate(log.created_at)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800">
          <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page===1} className="btn-ghost py-1 px-3 text-xs disabled:opacity-30">Previous</button>
          <span className="text-xs text-slate-500">Page {page}</span>
          <button onClick={() => setPage(p => p+1)} disabled={logs.length < 50} className="btn-ghost py-1 px-3 text-xs disabled:opacity-30">Next</button>
        </div>
      </div>
    </div>
  );
}
