"""
ML training pipeline for FraudLens.

Steps:
1. Load synthetic transactions
2. Feature engineering
3. Stratified train/test split
4. Train XGBoost with scale_pos_weight for class imbalance
5. Evaluate: precision, recall, F1, PR-AUC, ROC-AUC, confusion matrix
6. Tune threshold to balance precision/recall
7. SHAP TreeExplainer setup
8. Save model + artifacts

NOTE: We do NOT headline accuracy — it is misleading for imbalanced fraud data.
A model that predicts all-legit gets ~98% accuracy but catches 0 fraud.
"""

import json
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore")

ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)

DATA_PATH = Path("data/raw/transactions.parquet")

# Feature columns used by the model
CATEGORICAL_FEATURES = ["merchant_category", "country", "customer_home_country"]
NUMERIC_FEATURES = [
    "amount",
    "hour_of_day",
    "day_of_week",
    "is_foreign",
    "device_is_new",
    "txns_last_1h",
    "txns_last_24h",
    "avg_amount_30d",
    "amount_vs_avg_ratio",
    "distance_from_home_km",
    "card_present",
    "account_age_days",
]
ALL_FEATURES = NUMERIC_FEATURES + [f"{f}_enc" for f in CATEGORICAL_FEATURES]
TARGET = "is_fraud"


def feature_engineer(df: pd.DataFrame, encoders: dict | None = None) -> tuple[pd.DataFrame, dict]:
    """
    Encode categorical features.
    If encoders is None, fit new ones (train mode).
    Otherwise use existing (inference mode).
    """
    df = df.copy()
    fitted_encoders: dict = {}

    for col in CATEGORICAL_FEATURES:
        enc_col = f"{col}_enc"
        if encoders is None:
            le = LabelEncoder()
            df[enc_col] = le.fit_transform(df[col].astype(str))
            fitted_encoders[col] = le
        else:
            le = encoders[col]
            df[enc_col] = df[col].astype(str).apply(
                lambda x: le.transform([x])[0] if x in le.classes_ else -1
            )
            fitted_encoders[col] = le

    return df, (encoders if encoders else fitted_encoders)


def pick_threshold(y_true: np.ndarray, probs: np.ndarray) -> float:
    """
    Choose threshold that maximizes F1 score.
    Returns threshold rounded to 2 decimal places.
    """
    precision_arr, recall_arr, thresholds = precision_recall_curve(y_true, probs)
    f1_scores = 2 * precision_arr * recall_arr / (precision_arr + recall_arr + 1e-9)
    best_idx = np.argmax(f1_scores[:-1])  # last element has no threshold
    threshold = float(thresholds[best_idx])
    return round(threshold, 2)


def evaluate(y_true: np.ndarray, probs: np.ndarray, threshold: float) -> dict:
    """Compute all evaluation metrics."""
    preds = (probs >= threshold).astype(int)
    cm = confusion_matrix(y_true, preds).tolist()
    tn, fp, fn, tp = confusion_matrix(y_true, preds).ravel()

    return {
        "threshold": threshold,
        "precision": round(precision_score(y_true, preds, zero_division=0), 4),
        "recall": round(recall_score(y_true, preds, zero_division=0), 4),
        "f1": round(f1_score(y_true, preds, zero_division=0), 4),
        "pr_auc": round(average_precision_score(y_true, probs), 4),
        "roc_auc": round(roc_auc_score(y_true, probs), 4),
        "confusion_matrix": cm,
        "true_positives": int(tp),
        "false_positives": int(fp),
        "true_negatives": int(tn),
        "false_negatives": int(fn),
        # NOT the headline but included for completeness
        "accuracy": round((tp + tn) / (tp + tn + fp + fn), 4),
    }


def get_shap_factors(
    model: xgb.XGBClassifier,
    row: pd.DataFrame,
    feature_names: list[str],
    top_n: int = 5,
) -> list[dict]:
    """
    Return top N SHAP factors for a single transaction row.
    Each factor includes: feature name, readable name, shap_value, direction.
    """
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(row[feature_names])

    # For XGBoost classifier, shap_values shape: (n_samples, n_features)
    sv = shap_values[0] if isinstance(shap_values, list) else shap_values[0]

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
        "distance_from_home_km": "Distance from Home",
        "card_present": "Card Present",
        "account_age_days": "Account Age (days)",
        "merchant_category_enc": "Merchant Category",
        "country_enc": "Transaction Country",
        "customer_home_country_enc": "Customer Home Country",
    }

    factors = []
    indices = np.argsort(np.abs(sv))[::-1][:top_n]
    for idx in indices:
        feat = feature_names[idx]
        val = float(sv[idx])
        factors.append({
            "feature": feat,
            "readable_name": READABLE_NAMES.get(feat, feat),
            "shap_value": round(val, 4),
            "direction": "increases_risk" if val > 0 else "decreases_risk",
            "feature_value": float(row[feat].iloc[0]),
        })
    return factors


def main():
    print("=" * 60)
    print("FraudLens ML Training Pipeline")
    print("=" * 60)

    # ── Load data ──────────────────────────────────────────────
    print("\n[1/6] Loading data...")
    df = pd.read_parquet(DATA_PATH)
    print(f"  Loaded {len(df):,} transactions | Fraud: {df[TARGET].sum():,} ({df[TARGET].mean()*100:.2f}%)")

    # ── Feature engineering ────────────────────────────────────
    print("\n[2/6] Feature engineering...")
    df, encoders = feature_engineer(df)
    joblib.dump(encoders, ARTIFACTS_DIR / "label_encoders.joblib")

    X = df[ALL_FEATURES]
    y = df[TARGET]

    # ── Stratified split ───────────────────────────────────────
    print("\n[3/6] Stratified train/test split (80/20)...")
    sss = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(sss.split(X, y))
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    print(f"  Train: {len(X_train):,} | Test: {len(X_test):,}")
    print(f"  Test fraud rate: {y_test.mean()*100:.2f}%")

    # Save test set for live threshold preview
    test_df = X_test.copy()
    test_df[TARGET] = y_test.values
    test_df.to_parquet(ARTIFACTS_DIR / "test_set.parquet", index=False)

    # ── Train XGBoost ──────────────────────────────────────────
    print("\n[4/6] Training XGBoost...")
    # scale_pos_weight handles class imbalance: n_negatives / n_positives
    n_pos = y_train.sum()
    n_neg = len(y_train) - n_pos
    scale_pos_weight = n_neg / n_pos
    print(f"  scale_pos_weight = {scale_pos_weight:.1f}")

    model = xgb.XGBClassifier(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="aucpr",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=50,
    )

    # ── Threshold selection ────────────────────────────────────
    print("\n[5/6] Selecting threshold...")
    probs = model.predict_proba(X_test)[:, 1]
    threshold = pick_threshold(y_test.values, probs)
    print(f"  Best threshold (max F1): {threshold}")

    # ── Evaluate ───────────────────────────────────────────────
    print("\n[6/6] Evaluating...")
    metrics = evaluate(y_test.values, probs, threshold)

    print(f"\n{'-'*40}")
    print(f"  Threshold:  {metrics['threshold']}")
    print(f"  Precision:  {metrics['precision']}")
    print(f"  Recall:     {metrics['recall']}")
    print(f"  F1:         {metrics['f1']}")
    print(f"  PR-AUC:     {metrics['pr_auc']}")
    print(f"  ROC-AUC:    {metrics['roc_auc']}")
    print(f"  TP={metrics['true_positives']}  FP={metrics['false_positives']}")
    print(f"  FN={metrics['false_negatives']}  TN={metrics['true_negatives']}")
    print(f"  Accuracy:   {metrics['accuracy']} (not the headline metric)")
    print(f"{'-'*40}")

    # ── Save artifacts ─────────────────────────────────────────
    joblib.dump(model, ARTIFACTS_DIR / "xgb_model.joblib")
    with open(ARTIFACTS_DIR / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    with open(ARTIFACTS_DIR / "feature_names.json", "w") as f:
        json.dump({"features": ALL_FEATURES, "categorical": CATEGORICAL_FEATURES}, f, indent=2)

    print(f"\nArtifacts saved to {ARTIFACTS_DIR}/")
    print("  xgb_model.joblib")
    print("  label_encoders.joblib")
    print("  metrics.json")
    print("  feature_names.json")
    print("  test_set.parquet")


if __name__ == "__main__":
    main()
