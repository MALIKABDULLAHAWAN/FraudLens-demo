"""
Database seeding: creates tables and seeds demo users + customers + precomputed transactions.
Run once on startup if DB is empty.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.core.security import hash_password
from backend.app.db.models import AuditLog, Base, Customer, Transaction, User
from backend.app.db.session import engine, SessionLocal

logger = logging.getLogger(__name__)


def create_tables():
    Base.metadata.create_all(bind=engine)
    logger.info("DB tables created/verified")


def seed_users(db: Session) -> None:
    """Seed demo users if they don't exist."""
    demo_users = [
        {"email": "demo@fraudlens.app",     "password": "Demo@1234",   "role": "analyst"},
        {"email": "admin@fraudlens.app",    "password": "Admin@1234",  "role": "admin"},
        {"email": "analyst@fraudlens.com",  "password": "analyst123",  "role": "analyst"},
        {"email": "admin@fraudlens.com",    "password": "admin123",    "role": "admin"},
    ]
    for u in demo_users:
        if not db.query(User).filter(User.email == u["email"]).first():
            db.add(User(
                email=u["email"],
                hashed_password=hash_password(u["password"]),
                role=u["role"],
            ))
    db.commit()
    logger.info("Demo users seeded")


def seed_customers(db: Session) -> None:
    """Load synthetic customers from CSV if not already seeded."""
    if db.query(Customer).count() > 0:
        logger.info("Customers already seeded, skipping")
        return

    customers_path = Path("data/raw/customers.csv")
    if not customers_path.exists():
        logger.warning("customers.csv not found — run scripts/generate_data.py first")
        return

    import pandas as pd
    df = pd.read_csv(customers_path)
    for _, row in df.iterrows():
        fav = json.loads(row["favorite_categories"]) if isinstance(row["favorite_categories"], str) else []
        db.add(Customer(
            id=row["customer_id"],
            home_country=row["home_country"],
            account_age_days=int(row["account_age_days"]),
            avg_amount_30d=float(row["avg_amount_30d"]),
            risk_profile=row["risk_profile"],
            favorite_categories=fav,
        ))
    db.commit()
    logger.info(f"Seeded {len(df)} customers")


def seed_demo_transactions(db: Session) -> None:
    """
    Load precomputed demo cases (with SHAP + summaries).
    These are the 40 seeded cases that load instantly in the demo.
    """
    demo_path = Path("data/raw/demo_cases_scored.json")
    if not demo_path.exists():
        logger.warning("demo_cases_scored.json not found — run scripts/precompute_demo.py first")
        # Fall back to unscored demo cases for basic structure
        demo_path = Path("data/raw/demo_cases.json")
        if not demo_path.exists():
            return

    if db.query(Transaction).filter(Transaction.id.like("DEMO%")).count() > 0:
        logger.info("Demo transactions already seeded, skipping")
        return

    with open(demo_path) as f:
        cases = json.load(f)

    seeded = 0
    for case in cases:
        tx_id = case.get("transaction_id", f"DEMO{seeded+1:03d}")
        if db.query(Transaction).filter(Transaction.id == tx_id).first():
            continue

        # Ensure customer exists
        cid = case.get("customer_id", "C00001")
        if not db.query(Customer).filter(Customer.id == cid).first():
            cid = "C00001"

        risk_score = case.get("risk_score")
        risk_level = case.get("risk_level", "low")
        is_flagged = case.get("is_flagged", False)

        ts_raw = case.get("timestamp", str(datetime.now(timezone.utc)))
        if isinstance(ts_raw, str):
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except ValueError:
                ts = datetime.now(timezone.utc)
        else:
            ts = datetime.now(timezone.utc)

        tx = Transaction(
            id=tx_id,
            customer_id=cid,
            timestamp=ts,
            amount=float(case.get("amount", 0)),
            merchant_category=case.get("merchant_category", ""),
            country=case.get("country", ""),
            customer_home_country=case.get("customer_home_country", ""),
            is_foreign=int(case.get("is_foreign", 0)),
            device_is_new=int(case.get("device_is_new", 0)),
            hour_of_day=int(case.get("hour_of_day", 12)),
            day_of_week=int(case.get("day_of_week", 1)),
            txns_last_1h=int(case.get("txns_last_1h", 0)),
            txns_last_24h=int(case.get("txns_last_24h", 0)),
            avg_amount_30d=float(case.get("avg_amount_30d", 100)),
            amount_vs_avg_ratio=float(case.get("amount_vs_avg_ratio", 1.0)),
            distance_from_home_km=float(case.get("distance_from_home_km", 0)),
            card_present=int(case.get("card_present", 1)),
            account_age_days=int(case.get("account_age_days", 365)),
            risk_score=float(risk_score) if risk_score is not None else None,
            risk_level=risk_level,
            is_flagged=is_flagged,
            shap_factors=case.get("shap_factors"),
            llm_summary=case.get("llm_summary"),
            summary_source=case.get("summary_source", "template"),
            suggested_action=case.get("suggested_action"),
            status="pending" if is_flagged else "approved",
        )
        db.add(tx)
        seeded += 1

    db.commit()
    logger.info(f"Seeded {seeded} demo transactions")


def seed_all() -> None:
    """Entry point: called at app startup if DB is empty."""
    create_tables()
    db = SessionLocal()
    try:
        seed_users(db)
        seed_customers(db)
        seed_demo_transactions(db)
    finally:
        db.close()
