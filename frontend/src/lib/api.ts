import axios from 'axios';
import type {
  AuditLogEntry,
  DecisionCreate,
  DecisionResponse,
  LoginRequest,
  ModelMetrics,
  SimulateResponse,
  StatsResponse,
  ThresholdPreview,
  TokenResponse,
  TransactionDetail,
  TransactionSummary,
} from '../types/api';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30_000,
});

// Attach JWT from localStorage to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Redirect to login on 401
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('role');
      localStorage.removeItem('email');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────

export const login = (data: LoginRequest): Promise<TokenResponse> =>
  api.post('/auth/login', data).then((r) => r.data);

// ── Transactions ──────────────────────────────────────────────────────────────

export const getTransactions = (params?: {
  status?: string;
  risk_level?: string;
  is_flagged?: boolean;
  page?: number;
  page_size?: number;
}): Promise<TransactionSummary[]> =>
  api.get('/transactions', { params }).then((r) => r.data);

export const getTransaction = (id: string): Promise<TransactionDetail> =>
  api.get(`/transactions/${id}`).then((r) => r.data);

export const scoreTransaction = (payload: object): Promise<TransactionDetail> =>
  api.post('/transactions/score', payload).then((r) => r.data);

export const simulateTransaction = (kind: 'normal' | 'suspicious'): Promise<SimulateResponse> =>
  api.post(`/transactions/simulate?kind=${kind}`).then((r) => r.data);

export const makeDecision = (id: string, data: DecisionCreate): Promise<DecisionResponse> =>
  api.post(`/transactions/${id}/decision`, data).then((r) => r.data);

// ── Metrics & Stats ───────────────────────────────────────────────────────────

export const getStats = (): Promise<StatsResponse> =>
  api.get('/stats').then((r) => r.data);

export const getModelMetrics = (): Promise<ModelMetrics> =>
  api.get('/metrics/model').then((r) => r.data);

export const getThresholdPreview = (threshold: number): Promise<ThresholdPreview> =>
  api.post(`/metrics/threshold-preview?threshold=${threshold}`).then((r) => r.data);

// ── Audit ─────────────────────────────────────────────────────────────────────

export const getAuditLog = (page = 1): Promise<AuditLogEntry[]> =>
  api.get('/audit-log', { params: { page } }).then((r) => r.data);

export default api;
