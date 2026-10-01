"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: str


# ── SHAP factor ───────────────────────────────────────────────────────────────

class ShapFactor(BaseModel):
    feature: str
    readable_name: str
    shap_value: float
    direction: str  # "increases_risk" | "decreases_risk"
    feature_value: float


# ── Transaction ───────────────────────────────────────────────────────────────

class TransactionCreate(BaseModel):
    """Payload for scoring a new transaction."""
    customer_id: str
    amount: float = Field(gt=0)
    merchant_category: str
    country: str
    customer_home_country: str
    device_is_new: int = Field(ge=0, le=1)
    txns_last_1h: int = Field(ge=0)
    txns_last_24h: int = Field(ge=0)
    avg_amount_30d: float = Field(gt=0)
    distance_from_home_km: float = Field(ge=0)
    card_present: int = Field(ge=0, le=1)
    account_age_days: int = Field(ge=0)
    # Optional overrides
    hour_of_day: Optional[int] = None
    day_of_week: Optional[int] = None
    amount_vs_avg_ratio: Optional[float] = None
    is_foreign: Optional[int] = None


class TransactionSummary(BaseModel):
    """Compact view for the review queue table."""
    id: str
    customer_id: str
    timestamp: datetime
    amount: float
    merchant_category: str
    country: str
    risk_score: Optional[float]
    risk_level: Optional[str]
    is_flagged: bool
    status: str
    suggested_action: Optional[str]

    class Config:
        from_attributes = True


class TransactionDetail(BaseModel):
    """Full case detail with SHAP + summary."""
    id: str
    customer_id: str
    timestamp: datetime
    amount: float
    merchant_category: str
    country: str
    customer_home_country: str
    is_foreign: int
    device_is_new: int
    hour_of_day: int
    day_of_week: int
    txns_last_1h: int
    txns_last_24h: int
    avg_amount_30d: float
    amount_vs_avg_ratio: float
    distance_from_home_km: float
    card_present: int
    account_age_days: int
    risk_score: Optional[float]
    risk_level: Optional[str]
    is_flagged: bool
    shap_factors: Optional[list[ShapFactor]]
    llm_summary: Optional[str]
    summary_source: Optional[str]
    suggested_action: Optional[str]
    status: str
    reviewed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Decision ──────────────────────────────────────────────────────────────────

class DecisionCreate(BaseModel):
    action: str = Field(pattern="^(approve|reject|escalate)$")
    note: Optional[str] = None


class DecisionResponse(BaseModel):
    transaction_id: str
    action: str
    analyst_email: str
    note: Optional[str]
    created_at: datetime


# ── Stats / Metrics ───────────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    total_transactions: int
    pending_review: int
    flagged_today: int
    approved: int
    rejected: int
    escalated: int
    flagged_rate: float
    avg_review_time_minutes: Optional[float]


class ModelMetricsResponse(BaseModel):
    threshold: float
    precision: float
    recall: float
    f1: float
    pr_auc: float
    roc_auc: float
    confusion_matrix: list[list[int]]
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int


class ThresholdPreviewResponse(BaseModel):
    threshold: float
    precision: float
    recall: float
    false_positive_rate: float
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int


# ── Audit ─────────────────────────────────────────────────────────────────────

class AuditLogEntry(BaseModel):
    id: str
    event_type: str
    transaction_id: Optional[str]
    user_id: Optional[str]
    details: Optional[dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Simulate ──────────────────────────────────────────────────────────────────

class SimulateResponse(BaseModel):
    transaction: TransactionDetail
    message: str
