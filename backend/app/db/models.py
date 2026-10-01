"""SQLAlchemy ORM models for FraudLens."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="analyst")  # analyst | admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    decisions = relationship("Decision", back_populates="analyst")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True)  # C00001 etc.
    home_country = Column(String)
    account_age_days = Column(Integer)
    avg_amount_30d = Column(Float)
    risk_profile = Column(String)
    favorite_categories = Column(JSON)  # list[str]
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    transactions = relationship("Transaction", back_populates="customer")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True)  # TX0000001 or DEMO001
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    amount = Column(Float, nullable=False)
    merchant_category = Column(String)
    country = Column(String)
    customer_home_country = Column(String)
    is_foreign = Column(Integer)
    device_is_new = Column(Integer)
    hour_of_day = Column(Integer)
    day_of_week = Column(Integer)
    txns_last_1h = Column(Integer)
    txns_last_24h = Column(Integer)
    avg_amount_30d = Column(Float)
    amount_vs_avg_ratio = Column(Float)
    distance_from_home_km = Column(Float)
    card_present = Column(Integer)
    account_age_days = Column(Integer)

    # Scoring results (populated after ML scoring)
    risk_score = Column(Float, nullable=True)
    risk_level = Column(String, nullable=True)  # low | medium | high | critical
    is_flagged = Column(Boolean, default=False)
    shap_factors = Column(JSON, nullable=True)    # list[dict]
    llm_summary = Column(Text, nullable=True)
    suggested_action = Column(String, nullable=True)  # approve | review | escalate
    summary_source = Column(String, nullable=True)    # llm | template

    # Review status
    status = Column(String, default="pending")  # pending | approved | rejected | escalated
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow)

    customer = relationship("Customer", back_populates="transactions")
    decision = relationship("Decision", back_populates="transaction", uselist=False)


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(String, primary_key=True, default=_uuid)
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False, index=True)
    analyst_id = Column(String, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)   # approve | reject | escalate
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    transaction = relationship("Transaction", back_populates="decision")
    analyst = relationship("User", back_populates="decisions")


class AuditLog(Base):
    """Immutable append-only audit trail."""
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=_uuid)
    event_type = Column(String, nullable=False)   # transaction_scored | decision_made | login
    transaction_id = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
