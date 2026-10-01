"""
pytest tests for FraudLens backend.
Tests: scoring, API auth, decision flow, LLM fallback.

Run with: pytest backend/tests/ -v
"""

import json
import pytest
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.models import Base, User
from backend.app.core.security import hash_password
from backend.app.db.session import get_db

# ── Test DB setup ─────────────────────────────────────────────────────────────

TEST_DB_URL = "sqlite:///./test_fraudlens.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestSessionLocal()
    # Seed test users
    for u in [
        {"email": "demo@fraudlens.app", "password": "Demo@1234", "role": "analyst"},
        {"email": "admin@fraudlens.app", "password": "Admin@1234", "role": "admin"},
    ]:
        if not db.query(User).filter(User.email == u["email"]).first():
            db.add(User(
                email=u["email"],
                hashed_password=hash_password(u["password"]),
                role=u["role"],
            ))
    db.commit()
    db.close()
    yield
    # Cleanup — ignore Windows file lock on teardown
    Base.metadata.drop_all(bind=engine)
    try:
        Path("test_fraudlens.db").unlink(missing_ok=True)
    except PermissionError:
        pass  # Windows may keep file locked briefly


@pytest.fixture(scope="session")
def client(setup_test_db):
    """Test client with DB overrides and mocked ML model."""
    from backend.app.main import app
    from backend.app.ml.scorer import get_fraud_model

    app.dependency_overrides[get_db] = override_get_db

    # Mock the ML model so tests don't require trained artifacts
    mock_model = _make_mock_model()

    with patch("backend.app.ml.scorer.get_fraud_model", return_value=mock_model):
        with patch("backend.app.api.transactions.get_fraud_model", return_value=mock_model):
            with TestClient(app, raise_server_exceptions=False) as c:
                yield c


def _make_mock_model():
    """Create a mock FraudModel that returns deterministic results."""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.threshold = 0.5
    mock.metrics = {
        "threshold": 0.5, "precision": 0.85, "recall": 0.78,
        "f1": 0.81, "pr_auc": 0.87, "roc_auc": 0.95,
        "confusion_matrix": [[9500, 100], [22, 78]],
        "true_positives": 78, "false_positives": 100,
        "true_negatives": 9500, "false_negatives": 22,
        "accuracy": 0.9878,
    }
    mock.score.return_value = {
        "risk_score": 0.82,
        "risk_level": "high",
        "is_flagged": True,
        "shap_factors": [
            {"feature": "amount_vs_avg_ratio", "readable_name": "Amount vs Customer Avg",
             "shap_value": 0.45, "direction": "increases_risk", "feature_value": 7.5},
        ],
        "suggested_action": "escalate",
        "threshold_used": 0.5,
    }
    mock.threshold_preview.return_value = {
        "threshold": 0.6, "precision": 0.88, "recall": 0.72,
        "false_positive_rate": 0.02, "true_positives": 72,
        "false_positives": 80, "true_negatives": 9520, "false_negatives": 28,
    }
    return mock


# ── Helper: get auth token ────────────────────────────────────────────────────

def get_token(client, email: str, password: str) -> str:
    # Clear rate limiter state so tests don't trip the 5-req/min limit
    from backend.app.api.auth import _login_attempts
    _login_attempts.clear()
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


# ═══════════════════════════════════════════════════════════════════════════════
# Test: Auth
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuth:
    def test_login_success_analyst(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "demo@fraudlens.app", "password": "Demo@1234"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["role"] == "analyst"
        assert data["email"] == "demo@fraudlens.app"

    def test_login_success_admin(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "admin@fraudlens.app", "password": "Admin@1234"
        })
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    def test_login_wrong_password(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "demo@fraudlens.app", "password": "wrong"
        })
        assert resp.status_code == 401

    def test_login_unknown_user(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "nobody@example.com", "password": "anything"
        })
        assert resp.status_code == 401

    def test_protected_endpoint_no_token(self, client):
        resp = client.get("/api/transactions")
        assert resp.status_code == 401

    def test_protected_endpoint_bad_token(self, client):
        resp = client.get("/api/transactions", headers={"Authorization": "Bearer badtoken"})
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# Test: Transactions + Scoring
# ═══════════════════════════════════════════════════════════════════════════════

class TestTransactions:
    @pytest.fixture(autouse=True)
    def token(self, client):
        self.token = get_token(client, "demo@fraudlens.app", "Demo@1234")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_list_transactions(self, client):
        resp = client.get("/api/transactions", headers=self.headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_transactions_filter_status(self, client):
        resp = client.get("/api/transactions?status=pending", headers=self.headers)
        assert resp.status_code == 200

    def test_score_transaction(self, client):
        payload = {
            "customer_id": "C00001",
            "amount": 1500.0,
            "merchant_category": "electronics",
            "country": "NG",
            "customer_home_country": "US",
            "device_is_new": 1,
            "txns_last_1h": 5,
            "txns_last_24h": 12,
            "avg_amount_30d": 200.0,
            "distance_from_home_km": 5000.0,
            "card_present": 0,
            "account_age_days": 180,
        }
        resp = client.post("/api/transactions/score", json=payload, headers=self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "risk_score" in data
        assert "shap_factors" in data
        assert data["risk_score"] == 0.82  # from mock

    def test_get_nonexistent_transaction(self, client):
        resp = client.get("/api/transactions/NOTEXIST", headers=self.headers)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# Test: Decision Flow
# ═══════════════════════════════════════════════════════════════════════════════

class TestDecisionFlow:
    @pytest.fixture(autouse=True)
    def setup(self, client):
        self.token = get_token(client, "demo@fraudlens.app", "Demo@1234")
        self.headers = {"Authorization": f"Bearer {self.token}"}

        # Create a transaction to decide on
        payload = {
            "customer_id": "C00001",
            "amount": 2000.0,
            "merchant_category": "crypto_exchange",
            "country": "RO",
            "customer_home_country": "US",
            "device_is_new": 1,
            "txns_last_1h": 7,
            "txns_last_24h": 15,
            "avg_amount_30d": 150.0,
            "distance_from_home_km": 7000.0,
            "card_present": 0,
            "account_age_days": 90,
        }
        resp = client.post("/api/transactions/score", json=payload, headers=self.headers)
        assert resp.status_code == 200
        self.tx_id = resp.json()["id"]

    def test_approve_transaction(self, client):
        resp = client.post(
            f"/api/transactions/{self.tx_id}/decision",
            json={"action": "approve", "note": "Looks legitimate"},
            headers=self.headers,
        )
        assert resp.status_code == 200
        assert resp.json()["action"] == "approve"

    def test_double_decision_rejected(self, client):
        # Create a SEPARATE transaction for this test to avoid state contamination
        payload = {
            "customer_id": "C00001",
            "amount": 3000.0,
            "merchant_category": "jewelry",
            "country": "NG",
            "customer_home_country": "US",
            "device_is_new": 1,
            "txns_last_1h": 6,
            "txns_last_24h": 14,
            "avg_amount_30d": 200.0,
            "distance_from_home_km": 6000.0,
            "card_present": 0,
            "account_age_days": 90,
        }
        resp = client.post("/api/transactions/score", json=payload, headers=self.headers)
        assert resp.status_code == 200
        tx_id = resp.json()["id"]
        # First decision: should succeed
        r1 = client.post(
            f"/api/transactions/{tx_id}/decision",
            json={"action": "approve"},
            headers=self.headers,
        )
        assert r1.status_code == 200
        # Second decision: should fail with 409
        r2 = client.post(
            f"/api/transactions/{tx_id}/decision",
            json={"action": "reject"},
            headers=self.headers,
        )
        assert r2.status_code == 409

    def test_invalid_action_rejected(self, client):
        payload2 = {
            "customer_id": "C00001",
            "amount": 50.0,
            "merchant_category": "grocery",
            "country": "US",
            "customer_home_country": "US",
            "device_is_new": 0,
            "txns_last_1h": 0,
            "txns_last_24h": 2,
            "avg_amount_30d": 100.0,
            "distance_from_home_km": 5.0,
            "card_present": 1,
            "account_age_days": 730,
        }
        resp2 = client.post("/api/transactions/score", json=payload2, headers=self.headers)
        tx2_id = resp2.json()["id"]

        resp = client.post(
            f"/api/transactions/{tx2_id}/decision",
            json={"action": "delete"},  # invalid
            headers=self.headers,
        )
        assert resp.status_code == 422  # Pydantic validation error


# ═══════════════════════════════════════════════════════════════════════════════
# Test: LLM Fallback
# ═══════════════════════════════════════════════════════════════════════════════

class TestLLMFallback:
    """Verify the app works correctly when LLM is unavailable."""

    def test_template_summary_generated(self):
        """Template summary should always return a non-empty string."""
        from backend.app.agent.case_agent import _template_summary

        score_result = {
            "risk_score": 0.85,
            "risk_level": "high",
            "suggested_action": "escalate",
            "shap_factors": [
                {"readable_name": "Amount vs Customer Avg", "direction": "increases_risk", "shap_value": 0.4},
                {"readable_name": "New Device", "direction": "increases_risk", "shap_value": 0.3},
                {"readable_name": "Card Present", "direction": "decreases_risk", "shap_value": -0.1},
            ],
        }
        tx = {"transaction_id": "TEST001", "amount": 500}
        summary = _template_summary(score_result, tx)
        assert isinstance(summary, str)
        assert len(summary) > 50
        assert "high" in summary
        assert "FraudLens supports human analysts" in summary

    def test_agent_with_llm_timeout(self):
        """Agent should return template summary on LLM timeout."""
        import asyncio
        from backend.app.agent.case_agent import run_case_agent

        score_result = {
            "risk_score": 0.75,
            "risk_level": "high",
            "suggested_action": "escalate",
            "is_flagged": True,
            "shap_factors": [
                {"readable_name": "Foreign Transaction", "direction": "increases_risk", "shap_value": 0.5},
            ],
        }
        tx = {
            "transaction_id": "TESTTO01",
            "amount": 999.0,
            "merchant_category": "electronics",
            "country": "NG",
            "customer_home_country": "US",
        }

        async def run():
            with patch("backend.app.agent.case_agent._make_llm_client") as mock_client:
                # Simulate client that times out
                mock_instance = AsyncMock()
                mock_instance.chat.completions.create = AsyncMock(
                    side_effect=asyncio.TimeoutError()
                )
                mock_client.return_value = mock_instance

                result = await run_case_agent(tx, score_result)
                return result

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result["summary_source"] == "template"
        assert len(result["summary"]) > 0
        assert result["risk_level"] == "high"

    def test_agent_with_llm_error(self):
        """Agent should return template summary on any LLM exception."""
        import asyncio
        from backend.app.agent.case_agent import run_case_agent

        score_result = {
            "risk_score": 0.80, "risk_level": "critical",
            "suggested_action": "escalate", "is_flagged": True,
            "shap_factors": [],
        }
        tx = {"transaction_id": "TESTERR1", "amount": 5000.0, "country": "RO"}

        async def run():
            with patch("backend.app.agent.case_agent._make_llm_client") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.chat.completions.create = AsyncMock(
                    side_effect=ConnectionError("LLM service down")
                )
                mock_client.return_value = mock_instance
                return await run_case_agent(tx, score_result)

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result["summary_source"] == "template"


# ═══════════════════════════════════════════════════════════════════════════════
# Test: Health + Metrics
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthAndMetrics:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_prometheus_metrics(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "fraudlens" in resp.text or "python" in resp.text

    def test_model_metrics_requires_auth(self, client):
        resp = client.get("/api/metrics/model")
        assert resp.status_code == 401
