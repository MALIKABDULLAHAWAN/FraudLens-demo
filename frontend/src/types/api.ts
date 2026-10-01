// API type definitions matching the FastAPI schemas

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: string;
  email: string;
}

export interface ShapFactor {
  feature: string;
  readable_name: string;
  shap_value: number;
  direction: 'increases_risk' | 'decreases_risk';
  feature_value: number;
}

export interface TransactionSummary {
  id: string;
  customer_id: string;
  timestamp: string;
  amount: number;
  merchant_category: string;
  country: string;
  risk_score: number | null;
  risk_level: 'low' | 'medium' | 'high' | 'critical' | null;
  is_flagged: boolean;
  status: 'pending' | 'approved' | 'rejected' | 'escalated';
  suggested_action: string | null;
}

export interface TransactionDetail extends TransactionSummary {
  customer_home_country: string;
  is_foreign: number;
  device_is_new: number;
  hour_of_day: number;
  day_of_week: number;
  txns_last_1h: number;
  txns_last_24h: number;
  avg_amount_30d: number;
  amount_vs_avg_ratio: number;
  distance_from_home_km: number;
  card_present: number;
  account_age_days: number;
  shap_factors: ShapFactor[] | null;
  llm_summary: string | null;
  summary_source: 'llm' | 'template' | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface DecisionCreate {
  action: 'approve' | 'reject' | 'escalate';
  note?: string;
}

export interface DecisionResponse {
  transaction_id: string;
  action: string;
  analyst_email: string;
  note?: string;
  created_at: string;
}

export interface StatsResponse {
  total_transactions: number;
  pending_review: number;
  flagged_today: number;
  approved: number;
  rejected: number;
  escalated: number;
  flagged_rate: number;
  avg_review_time_minutes: number | null;
}

export interface ModelMetrics {
  threshold: number;
  precision: number;
  recall: number;
  f1: number;
  pr_auc: number;
  roc_auc: number;
  confusion_matrix: number[][];
  true_positives: number;
  false_positives: number;
  true_negatives: number;
  false_negatives: number;
}

export interface ThresholdPreview {
  threshold: number;
  precision: number;
  recall: number;
  false_positive_rate: number;
  true_positives: number;
  false_positives: number;
  true_negatives: number;
  false_negatives: number;
}

export interface SimulateResponse {
  transaction: TransactionDetail;
  message: string;
}

export interface AuditLogEntry {
  id: string;
  event_type: string;
  transaction_id: string | null;
  user_id: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}
