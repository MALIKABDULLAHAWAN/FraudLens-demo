"""
Transaction API routes:
- GET  /api/transactions            — list with filters/pagination
- GET  /api/transactions/{id}       — full case detail
- POST /api/transactions/score      — score a new transaction
- POST /api/transactions/simulate   — generate + score a test case
- POST /api/transactions/{id}/decision — analyst decision
"""

import logging
import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.agent.case_agent import run_case_agent
from backend.app.api.deps import get_current_user
from backend.app.db.models import AuditLog, Customer, Decision, Transaction
from backend.app.db.session import get_db
from backend.app.ml.scorer import get_fraud_model
from backend.app.schemas.schemas import (
    DecisionCreate,
    DecisionResponse,
    SimulateResponse,
    TransactionCreate,
    TransactionDetail,
    TransactionSummary,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/transactions", tags=["transactions"])

MERCHANT_CATEGORIES = [
    "grocery", "electronics", "travel", "restaurant", "clothing",
    "fuel", "entertainment", "healthcare", "hotel", "online_retail",
    "jewelry", "gaming", "crypto_exchange", "money_transfer", "subscription",
]
COUNTRIES = ["US", "GB", "CA", "AU", "DE", "FR", "NG", "RO", "VN", "CN", "BR", "IN"]


def _tx_to_dict(tx: Transaction) -> dict:
    """Convert ORM object to raw dict for scoring."""
    return {
        "transaction_id": tx.id,
        "amount": tx.amount,
        "merchant_category": tx.merchant_category,
        "country": tx.country,
        "customer_home_country": tx.customer_home_country,
        "is_foreign": tx.is_foreign,
        "device_is_new": tx.device_is_new,
        "hour_of_day": tx.hour_of_day,
        "day_of_week": tx.day_of_week,
        "txns_last_1h": tx.txns_last_1h,
        "txns_last_24h": tx.txns_last_24h,
        "avg_amount_30d": tx.avg_amount_30d,
        "amount_vs_avg_ratio": tx.amount_vs_avg_ratio,
        "distance_from_home_km": tx.distance_from_home_km,
        "card_present": tx.card_present,
        "account_age_days": tx.account_age_days,
    }


def _get_customer_history(customer_id: str, exclude_tx_id: str, db: Session) -> list[dict]:
    """Fetch last 10 transactions for customer history panel."""
    txns = (
        db.query(Transaction)
        .filter(Transaction.customer_id == customer_id, Transaction.id != exclude_tx_id)
        .order_by(Transaction.timestamp.desc())
        .limit(10)
        .all()
    )
    return [{"amount": t.amount, "merchant_category": t.merchant_category, "country": t.country,
              "timestamp": str(t.timestamp), "risk_score": t.risk_score} for t in txns]


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[TransactionSummary])
def list_transactions(
    status: str | None = Query(None, description="pending|approved|rejected|escalated"),
    risk_level: str | None = Query(None, description="low|medium|high|critical"),
    is_flagged: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    q = db.query(Transaction)
    if status:
        q = q.filter(Transaction.status == status)
    if risk_level:
        q = q.filter(Transaction.risk_level == risk_level)
    if is_flagged is not None:
        q = q.filter(Transaction.is_flagged == is_flagged)

    q = q.order_by(Transaction.created_at.desc())
    offset = (page - 1) * page_size
    txns = q.offset(offset).limit(page_size).all()

    return [
        TransactionSummary(
            id=t.id,
            customer_id=t.customer_id,
            timestamp=t.timestamp,
            amount=t.amount,
            merchant_category=t.merchant_category,
            country=t.country,
            risk_score=t.risk_score,
            risk_level=t.risk_level,
            is_flagged=t.is_flagged or False,
            status=t.status,
            suggested_action=t.suggested_action,
        )
        for t in txns
    ]


# ── Detail ────────────────────────────────────────────────────────────────────

@router.get("/{tx_id}", response_model=TransactionDetail)
def get_transaction(
    tx_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionDetail.model_validate(tx)


# ── Score ─────────────────────────────────────────────────────────────────────

@router.post("/score", response_model=TransactionDetail)
async def score_transaction(
    body: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: object = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    model = get_fraud_model()

    # Derive fields if not provided
    is_foreign = body.is_foreign if body.is_foreign is not None else int(body.country != body.customer_home_country)
    avr = body.amount_vs_avg_ratio if body.amount_vs_avg_ratio is not None else round(body.amount / max(body.avg_amount_30d, 1), 3)

    tx_dict = {
        "amount": body.amount,
        "merchant_category": body.merchant_category,
        "country": body.country,
        "customer_home_country": body.customer_home_country,
        "is_foreign": is_foreign,
        "device_is_new": body.device_is_new,
        "hour_of_day": body.hour_of_day if body.hour_of_day is not None else now.hour,
        "day_of_week": body.day_of_week if body.day_of_week is not None else now.weekday(),
        "txns_last_1h": body.txns_last_1h,
        "txns_last_24h": body.txns_last_24h,
        "avg_amount_30d": body.avg_amount_30d,
        "amount_vs_avg_ratio": avr,
        "distance_from_home_km": body.distance_from_home_km,
        "card_present": body.card_present,
        "account_age_days": body.account_age_days,
    }

    score_result = model.score(tx_dict)

    # Persist transaction
    tx_id = f"TX{int(now.timestamp() * 1000) % 10_000_000:07d}"
    tx = Transaction(
        id=tx_id,
        customer_id=body.customer_id,
        timestamp=now,
        status="pending" if score_result["is_flagged"] else "approved",
        **{k: v for k, v in tx_dict.items()},
        risk_score=score_result["risk_score"],
        risk_level=score_result["risk_level"],
        is_flagged=score_result["is_flagged"],
        shap_factors=score_result["shap_factors"],
        suggested_action=score_result["suggested_action"],
    )

    # Run case agent for summary if flagged
    if score_result["is_flagged"]:
        agent_result = await run_case_agent(tx_dict, score_result)
        tx.llm_summary = agent_result["summary"]
        tx.summary_source = agent_result["summary_source"]

    db.add(tx)
    db.add(AuditLog(
        event_type="transaction_scored",
        transaction_id=tx.id,
        details={"risk_score": score_result["risk_score"], "is_flagged": score_result["is_flagged"]},
    ))
    db.commit()
    db.refresh(tx)
    return TransactionDetail.model_validate(tx)


# ── Simulate ──────────────────────────────────────────────────────────────────

@router.post("/simulate", response_model=SimulateResponse)
async def simulate_transaction(
    kind: str = Query("suspicious", pattern="^(normal|suspicious)$"),
    db: Session = Depends(get_db),
    current_user: object = Depends(get_current_user),
):
    """Generate a realistic test transaction, score it, return result."""
    model = get_fraud_model()
    now = datetime.now(timezone.utc)

    # Get a random customer from DB
    customers = db.query(Customer).all()
    if not customers:
        raise HTTPException(status_code=503, detail="No customers seeded. Run seed_db first.")
    cust = random.choice(customers)

    if kind == "suspicious":
        foreign = random.choice([c for c in COUNTRIES if c != cust.home_country])
        tx_dict = {
            "amount": round(cust.avg_amount_30d * random.uniform(5, 10), 2),
            "merchant_category": random.choice(["electronics", "crypto_exchange", "money_transfer"]),
            "country": foreign,
            "customer_home_country": cust.home_country,
            "is_foreign": 1,
            "device_is_new": 1,
            "hour_of_day": random.randint(1, 4),
            "day_of_week": now.weekday(),
            "txns_last_1h": random.randint(4, 9),
            "txns_last_24h": random.randint(8, 18),
            "avg_amount_30d": cust.avg_amount_30d,
            "amount_vs_avg_ratio": round(random.uniform(5, 10), 3),
            "distance_from_home_km": round(random.uniform(2000, 8000), 1),
            "card_present": 0,
            "account_age_days": cust.account_age_days,
        }
    else:
        fav_cats = cust.favorite_categories or ["grocery"]
        tx_dict = {
            "amount": round(cust.avg_amount_30d * random.uniform(0.5, 1.5), 2),
            "merchant_category": random.choice(fav_cats),
            "country": cust.home_country,
            "customer_home_country": cust.home_country,
            "is_foreign": 0,
            "device_is_new": 0,
            "hour_of_day": random.randint(9, 18),
            "day_of_week": now.weekday(),
            "txns_last_1h": random.randint(0, 1),
            "txns_last_24h": random.randint(1, 4),
            "avg_amount_30d": cust.avg_amount_30d,
            "amount_vs_avg_ratio": round(random.uniform(0.5, 1.5), 3),
            "distance_from_home_km": round(random.uniform(0, 50), 1),
            "card_present": 1,
            "account_age_days": cust.account_age_days,
        }

    score_result = model.score(tx_dict)
    tx_id = f"SIM{int(now.timestamp() * 1000) % 10_000_000:07d}"

    tx = Transaction(
        id=tx_id,
        customer_id=cust.id,
        timestamp=now,
        status="pending" if score_result["is_flagged"] else "approved",
        **tx_dict,
        risk_score=score_result["risk_score"],
        risk_level=score_result["risk_level"],
        is_flagged=score_result["is_flagged"],
        shap_factors=score_result["shap_factors"],
        suggested_action=score_result["suggested_action"],
    )

    if score_result["is_flagged"]:
        agent_result = await run_case_agent(tx_dict, score_result)
        tx.llm_summary = agent_result["summary"]
        tx.summary_source = agent_result["summary_source"]

    db.add(tx)
    db.commit()
    db.refresh(tx)

    return SimulateResponse(
        transaction=TransactionDetail.model_validate(tx),
        message=f"Simulated {kind} transaction scored: {score_result['risk_level']} risk ({score_result['risk_score']:.3f})",
    )


# ── Decision ──────────────────────────────────────────────────────────────────

@router.post("/{tx_id}/decision", response_model=DecisionResponse)
def make_decision(
    tx_id: str,
    body: DecisionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if tx.status not in ("pending",):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transaction already has status '{tx.status}'",
        )

    now = datetime.now(timezone.utc)
    tx.status = body.action + "d" if body.action in ("approve", "reject") else "escalated"
    tx.reviewed_at = now

    decision = Decision(
        transaction_id=tx_id,
        analyst_id=current_user.id,
        action=body.action,
        note=body.note,
    )
    db.add(decision)

    db.add(AuditLog(
        event_type="decision_made",
        transaction_id=tx_id,
        user_id=current_user.id,
        details={"action": body.action, "note": body.note},
    ))
    db.commit()

    return DecisionResponse(
        transaction_id=tx_id,
        action=body.action,
        analyst_email=current_user.email,
        note=body.note,
        created_at=now,
    )
