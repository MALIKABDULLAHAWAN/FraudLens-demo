"""
Precompute SHAP explanations and template summaries for the 40 demo cases.

This runs once after training so demo cases load instantly without blocking LLM calls.
Output: data/raw/demo_cases_scored.json
"""

import json
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.ml.scorer import FraudModel, CATEGORICAL_FEATURES


def _template_summary(score_result: dict, tx: dict) -> str:
    """Inline template (mirrors agent/case_agent.py fallback for standalone use)."""
    factors = score_result.get("shap_factors", [])
    risk_level = score_result.get("risk_level", "unknown")
    score = score_result.get("risk_score", 0)
    action = score_result.get("suggested_action", "review")

    risk_factors = [f for f in factors if f["direction"] == "increases_risk"]
    safe_factors = [f for f in factors if f["direction"] == "decreases_risk"]

    risk_desc = ""
    if risk_factors:
        names = [f["readable_name"] for f in risk_factors[:3]]
        risk_desc = "Key risk signals: " + ", ".join(names) + ". "

    safe_desc = ""
    if safe_factors:
        names = [f["readable_name"] for f in safe_factors[:2]]
        safe_desc = f"Mitigating factors: {', '.join(names)}. "

    action_map = {
        "escalate": "Escalation to a senior analyst is recommended.",
        "review": "Manual review is advised before approving.",
        "approve": "No significant risk signals detected; safe to approve.",
    }

    return (
        f"[Auto-generated summary] This transaction has a {risk_level} risk score of {score:.2f}. "
        f"{risk_desc}"
        f"{safe_desc}"
        f"{action_map.get(action, 'Review required.')} "
        f"Note: FraudLens supports human analysts; it does not block payments automatically."
    )


def main():
    demo_path = Path("data/raw/demo_cases.json")
    if not demo_path.exists():
        print("ERROR: data/raw/demo_cases.json not found. Run scripts/generate_data.py first.")
        sys.exit(1)

    model_path = Path("artifacts/xgb_model.joblib")
    if not model_path.exists():
        print("ERROR: artifacts/xgb_model.joblib not found. Run scripts/train.py first.")
        sys.exit(1)

    print("Loading model...")
    fraud_model = FraudModel()

    with open(demo_path) as f:
        cases = json.load(f)

    print(f"Scoring {len(cases)} demo cases...")
    scored = []
    for case in cases:
        try:
            score_result = fraud_model.score(case)
            summary = _template_summary(score_result, case)

            enriched = {**case}
            enriched["risk_score"] = score_result["risk_score"]
            enriched["risk_level"] = score_result["risk_level"]
            enriched["is_flagged"] = score_result["is_flagged"]
            enriched["shap_factors"] = score_result["shap_factors"]
            enriched["suggested_action"] = score_result["suggested_action"]
            enriched["llm_summary"] = summary
            enriched["summary_source"] = "template"
            scored.append(enriched)
        except Exception as e:
            print(f"  Warning: Failed to score {case.get('transaction_id')}: {e}")
            scored.append(case)

    out_path = Path("data/raw/demo_cases_scored.json")
    with open(out_path, "w") as f:
        json.dump(scored, f, indent=2, default=str)

    flagged = sum(1 for c in scored if c.get("is_flagged"))
    print(f"\nDone: {len(scored)} cases scored, {flagged} flagged.")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()
