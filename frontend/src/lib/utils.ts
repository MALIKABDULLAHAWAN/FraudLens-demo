

/** Format currency */
export const fmt = (amount: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

/** Format date/time */
export const fmtDate = (iso: string) =>
  new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });

/** Risk level → badge class */
export const riskBadgeClass = (level: string | null) => {
  switch (level) {
    case 'low':      return 'badge-low';
    case 'medium':   return 'badge-medium';
    case 'high':     return 'badge-high';
    case 'critical': return 'badge-critical';
    default:         return 'badge-pending';
  }
};

/** Status → badge class */
export const statusBadgeClass = (status: string) => {
  switch (status) {
    case 'approved':  return 'badge-approved';
    case 'rejected':  return 'badge-rejected';
    case 'escalated': return 'badge-escalated';
    default:          return 'badge-pending';
  }
};

/** Risk score (0–1) → color string */
export const scoreColor = (score: number | null) => {
  if (score === null) return '#64748b';
  if (score >= 0.80) return '#f43f5e';
  if (score >= 0.55) return '#f97316';
  if (score >= 0.30) return '#f59e0b';
  return '#10b981';
};

/** Capitalize first letter */
export const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
