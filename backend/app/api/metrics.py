"""Metrics and stats API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, require_admin
from backend.app.db.models import AuditLog, Decision, Transaction
from backend.app.db.session import get_db
from backend.app.ml.scorer import get_fraud_model
from backend.app.schemas.schemas import (
    AuditLogEntry,
    ModelMetricsResponse,
    StatsResponse,
    ThresholdPreviewResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["metrics"])


@router.get("/metrics/model", response_model=ModelMetricsResponse)
def get_model_metrics(_: object = Depends(get_current_user)):
    """Return saved training metrics (precision, recall, F1, PR-AUC, confusion matrix)."""
    model = get_fraud_model()
    m = model.metrics
    return ModelMetricsResponse(
        threshold=m["threshold"],
        precision=m["precision"],
        recall=m["recall"],
        f1=m["f1"],
        pr_auc=m["pr_auc"],
        roc_auc=m["roc_auc"],
        confusion_matrix=m["confusion_matrix"],
        true_positives=m["true_positives"],
        false_positives=m["false_positives"],
        true_negatives=m["true_negatives"],
        false_negatives=m["false_negatives"],
    )


@router.post("/metrics/threshold-preview", response_model=ThresholdPreviewResponse)
def threshold_preview(
    threshold: float = Query(ge=0.01, le=0.99),
    _: object = Depends(get_current_user),
):
    """Live threshold preview — recomputes precision/recall/FPR on test set."""
    model = get_fraud_model()
    result = model.threshold_preview(threshold)
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return ThresholdPreviewResponse(**result)


@router.get("/stats", response_model=StatsResponse)
def get_stats(
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    """Dashboard KPI counts."""
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import func

    today = datetime.now(timezone.utc).date()
    today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)

    total = db.query(func.count(Transaction.id)).scalar() or 0
    pending = db.query(func.count(Transaction.id)).filter(Transaction.status == "pending").scalar() or 0
    flagged_today = db.query(func.count(Transaction.id)).filter(
        Transaction.is_flagged == True,
        Transaction.created_at >= today_start,
    ).scalar() or 0
    approved = db.query(func.count(Transaction.id)).filter(Transaction.status == "approved").scalar() or 0
    rejected = db.query(func.count(Transaction.id)).filter(Transaction.status == "rejected").scalar() or 0
    escalated = db.query(func.count(Transaction.id)).filter(Transaction.status == "escalated").scalar() or 0
    total_flagged = db.query(func.count(Transaction.id)).filter(Transaction.is_flagged == True).scalar() or 0

    flagged_rate = round(total_flagged / total, 4) if total > 0 else 0.0

    # Average review time: from created_at to reviewed_at for decided transactions
    decided = db.query(Transaction).filter(Transaction.reviewed_at.isnot(None)).limit(200).all()
    if decided:
        deltas = [
            (t.reviewed_at - t.created_at).total_seconds() / 60
            for t in decided
            if t.reviewed_at and t.created_at
        ]
        avg_review_time = round(sum(deltas) / len(deltas), 1) if deltas else None
    else:
        avg_review_time = None

    return StatsResponse(
        total_transactions=total,
        pending_review=pending,
        flagged_today=flagged_today,
        approved=approved,
        rejected=rejected,
        escalated=escalated,
        flagged_rate=flagged_rate,
        avg_review_time_minutes=avg_review_time,
    )


@router.get("/audit-log", response_model=list[AuditLogEntry])
def get_audit_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),  # admin only
):
    offset = (page - 1) * page_size
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size).all()
    return [AuditLogEntry.model_validate(log) for log in logs]
