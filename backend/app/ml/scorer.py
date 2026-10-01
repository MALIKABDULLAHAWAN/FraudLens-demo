"""
ML inference module: loads trained XGBoost model and runs scoring + SHAP.

Designed as a singleton so the model loads once at startup and stays in memory.
"""

import json
import logging
from pathlib import Path
from functools import lru_cache
from typing import Any

import joblib
import numpy as np
import pandas as pd
import shap

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Human-readable feature names for UI display
READABLE_NAMES = {
    "amount": "Transaction Amount",
    "hour_of_day": "Hour of Day",
    "day_of_week": "Day of Week",
    "is_foreign": "Foreign Transaction",
    "device_is_new": "New Device",
    "txns_last_1h": "Transactions (last 1h)",
    "txns_last_24h": "Transactions (last 24h)",
    "avg_amount_30d": "Avg Amount (30d)",
    "amount_vs_avg_ratio": "Amount vs Customer Avg",
    "distance_from_home_km": "Distance from Home (km)",
    "card_present": "Card Present",
    "account_age_days": "Account Age (days)",
    "merchant_category_enc": "Merchant Category",
    "country_enc": "Transaction Country",
    "customer_home_country_enc": "Customer Home Country",
}

CATEGORICAL_FEATURES = ["merchant_category", "country", "customer_home_country"]
NUMERIC_FEATURES = [
    "amount", "hour_of_day", "day_of_week", "is_foreign", "device_is_new",
    "txns_last_1h", "txns_last_24h", "avg_amount_30d", "amount_vs_avg_ratio",
    "distance_from_home_km", "card_present", "account_age_days",
]
ALL_FEATURES = NUMERIC_FEATURES + [f"{f}_enc" for f in CATEGORICAL_FEATURES]


def _risk_level(score: float) -> str:
    if score < 0.30:
        return "low"
    elif score < 0.55:
        return "medium"
    elif score < 0.80:
        return "high"
    return "critical"


def _suggested_action(score: float, risk_level: str) -> str:
    if risk_level in ("high", "critical"):
        return "escalate"
    elif risk_level == "medium":
        return "review"
    return "approve"


class FraudModel:
    """Singleton wrapper around the XGBoost model + SHAP explainer."""

    def __init__(self):
        artifacts_dir = settings.artifacts_dir
        model_path = Path(settings.MODEL_PATH)

        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {model_path}. Run scripts/train.py first."
            )

        logger.info(f"Loading model from {model_path}")
        self.model = joblib.load(model_path)
        self.encoders: dict = joblib.load(artifacts_dir / "label_encoders.joblib")
        self.explainer = shap.TreeExplainer(self.model)

        with open(artifacts_dir / "metrics.json") as f:
            self.metrics: dict = json.load(f)

        # Runtime-configurable threshold (can be overridden via env or API)
        self.threshold: float = settings.FRAUD_THRESHOLD

        logger.info(f"Model loaded. Threshold={self.threshold}")

    def _encode_row(self, tx: dict) -> pd.DataFrame:
        """Convert a raw transaction dict into model-ready DataFrame."""
        row = {}
        for feat in NUMERIC_FEATURES:
            row[feat] = float(tx.get(feat, 0))

        for col in CATEGORICAL_FEATURES:
            enc_col = f"{col}_enc"
            le = self.encoders[col]
            val = str(tx.get(col, ""))
            if val in le.classes_:
                row[enc_col] = int(le.transform([val])[0])
            else:
                row[enc_col] = -1  # unseen category

        return pd.DataFrame([row])[ALL_FEATURES]

    def score(self, tx: dict, threshold: float | None = None) -> dict[str, Any]:
        """
        Score a single transaction.
        Returns: risk_score, risk_level, is_flagged, shap_factors, suggested_action
        """
        th = threshold if threshold is not None else self.threshold
        df_row = self._encode_row(tx)

        prob = float(self.model.predict_proba(df_row)[0, 1])
        is_flagged = prob >= th
        level = _risk_level(prob)

        # SHAP explanation
        shap_values = self.explainer.shap_values(df_row)
        sv = shap_values[0] if isinstance(shap_values, list) else shap_values[0]

        factors = []
        top_indices = np.argsort(np.abs(sv))[::-1][:5]
        for idx in top_indices:
            feat = ALL_FEATURES[idx]
            val = float(sv[idx])
            factors.append({
                "feature": feat,
                "readable_name": READABLE_NAMES.get(feat, feat),
                "shap_value": round(val, 4),
                "direction": "increases_risk" if val > 0 else "decreases_risk",
                "feature_value": float(df_row[feat].iloc[0]),
            })

        return {
            "risk_score": round(prob, 4),
            "risk_level": level,
            "is_flagged": is_flagged,
            "shap_factors": factors,
            "suggested_action": _suggested_action(prob, level),
            "threshold_used": th,
        }

    def threshold_preview(self, threshold: float) -> dict[str, Any]:
        """
        Recompute precision/recall/FPR on the saved test set for a given threshold.
        Used by the model metrics slider in the UI.
        """
        from pathlib import Path
        test_path = settings.artifacts_dir / "test_set.parquet"
        if not test_path.exists():
            return {"error": "Test set not found. Retrain to generate it."}

        test_df = pd.read_parquet(test_path)
        y_true = test_df["is_fraud"].values
        X_test = test_df[ALL_FEATURES]
        probs = self.model.predict_proba(X_test)[:, 1]
        preds = (probs >= threshold).astype(int)

        from sklearn.metrics import precision_score, recall_score, confusion_matrix
        tp = int(((preds == 1) & (y_true == 1)).sum())
        fp = int(((preds == 1) & (y_true == 0)).sum())
        tn = int(((preds == 0) & (y_true == 0)).sum())
        fn = int(((preds == 0) & (y_true == 1)).sum())
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

        return {
            "threshold": threshold,
            "precision": round(precision_score(y_true, preds, zero_division=0), 4),
            "recall": round(recall_score(y_true, preds, zero_division=0), 4),
            "false_positive_rate": round(fpr, 4),
            "true_positives": tp,
            "false_positives": fp,
            "true_negatives": tn,
            "false_negatives": fn,
        }


@lru_cache(maxsize=1)
def get_fraud_model() -> FraudModel:
    """Return the singleton model instance (loaded once at first call)."""
    return FraudModel()
