"""
LangGraph case-agent and LLM client.

Graph nodes:
  1. load_history  — fetch recent transactions for context
  2. build_evidence — format SHAP factors into structured evidence
  3. generate_summary — call LLM (with timeout + fallback to template)
  4. return_result  — package the final CaseResult

If the LLM is unavailable, slow (>LLM_TIMEOUT seconds), or errors,
the agent falls back to a deterministic template built from top SHAP factors.
The app NEVER fails because of the LLM.
"""

import asyncio
import logging
import time
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── LLM client factory ────────────────────────────────────────────────────────


def _make_llm_client():
    """Return an async OpenAI-compatible client, or None if unavailable."""
    try:
        from openai import AsyncOpenAI
        return AsyncOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
        )
    except Exception as exc:
        logger.warning(f"LLM client init failed: {exc}")
        return None


# ── Template fallback ─────────────────────────────────────────────────────────


def _template_summary(score_result: dict, tx: dict) -> str:
    """
    Deterministic rule-based summary from SHAP factors.
    Used when LLM is unavailable or times out.
    """
    factors = score_result.get("shap_factors", [])
    risk_level = score_result.get("risk_level", "unknown")
    score = score_result.get("risk_score", 0)
    action = score_result.get("suggested_action", "review")

    # Collect top risk-increasing factors
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


# ── LangGraph state ───────────────────────────────────────────────────────────


class AgentState(TypedDict):
    transaction: dict
    score_result: dict
    customer_history: list[dict]
    evidence: str
    summary: str
    summary_source: str  # "llm" | "template"
    risk_level: str
    suggested_action: str


# ── Graph nodes ───────────────────────────────────────────────────────────────


def load_history_node(state: AgentState) -> dict:
    """
    In a production system this would query the DB.
    For the agent graph we pass pre-loaded history in state.
    """
    return {}  # history already in state from caller


def build_evidence_node(state: AgentState) -> dict:
    """Format SHAP factors into a human-readable evidence string for the LLM prompt."""
    sr = state["score_result"]
    tx = state["transaction"]
    factors = sr.get("shap_factors", [])

    lines = [
        f"Transaction ID: {tx.get('transaction_id', 'N/A')}",
        f"Amount: ${tx.get('amount', 0):.2f}",
        f"Merchant Category: {tx.get('merchant_category', 'N/A')}",
        f"Country: {tx.get('country', 'N/A')} (home: {tx.get('customer_home_country', 'N/A')})",
        f"Risk Score: {sr.get('risk_score', 0):.3f} ({sr.get('risk_level', 'N/A')})",
        "",
        "Top SHAP factors (+ = increases fraud risk, - = decreases):",
    ]
    for f in factors:
        sign = "+" if f["direction"] == "increases_risk" else "-"
        lines.append(f"  {sign} {f['readable_name']}: SHAP={f['shap_value']:.3f} (value={f['feature_value']})")

    # Recent history snippet
    history = state.get("customer_history", [])
    if history:
        lines.append("")
        lines.append(f"Recent transactions (last {len(history)}):")
        for h in history[:5]:
            lines.append(f"  ${h.get('amount', 0):.2f} at {h.get('merchant_category', '?')} [{h.get('country', '?')}]")

    return {"evidence": "\n".join(lines)}


async def generate_summary_node(state: AgentState) -> dict:
    """
    Call LLM with timeout. Falls back to template on any failure.
    """
    client = _make_llm_client()

    if client is None:
        return {
            "summary": _template_summary(state["score_result"], state["transaction"]),
            "summary_source": "template",
        }

    system_prompt = (
        "You are FraudLens, an AI assistant that helps human fraud analysts review transactions. "
        "Your role is DECISION SUPPORT only — you never block payments. "
        "Provide a concise (3–5 sentence) plain-language summary of why this transaction was flagged, "
        "what the key risk signals are, and a suggested action. "
        "Be factual, reference the SHAP evidence provided, and end with: "
        "'FraudLens supports human analysts; it does not block payments automatically.'"
    )
    user_prompt = (
        "Please summarize this transaction case for the analyst:\n\n"
        + state["evidence"]
    )

    try:
        t0 = time.monotonic()
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=300,
                temperature=0.3,
            ),
            timeout=settings.LLM_TIMEOUT,
        )
        elapsed = time.monotonic() - t0
        summary = response.choices[0].message.content.strip()
        logger.info(f"LLM summary generated in {elapsed:.2f}s")
        return {"summary": summary, "summary_source": "llm"}

    except asyncio.TimeoutError:
        logger.warning(f"LLM timed out after {settings.LLM_TIMEOUT}s — using template")
    except Exception as exc:
        logger.warning(f"LLM error: {exc} — using template")

    return {
        "summary": _template_summary(state["score_result"], state["transaction"]),
        "summary_source": "template",
    }


def finalize_node(state: AgentState) -> dict:
    """Package the final result."""
    return {
        "risk_level": state["score_result"].get("risk_level", "unknown"),
        "suggested_action": state["score_result"].get("suggested_action", "review"),
    }


# ── Graph assembly ────────────────────────────────────────────────────────────


def _build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("load_history", load_history_node)
    graph.add_node("build_evidence", build_evidence_node)
    graph.add_node("generate_summary", generate_summary_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("load_history")
    graph.add_edge("load_history", "build_evidence")
    graph.add_edge("build_evidence", "generate_summary")
    graph.add_edge("generate_summary", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


_case_graph = _build_graph()


# ── Public interface ──────────────────────────────────────────────────────────


async def run_case_agent(
    transaction: dict,
    score_result: dict,
    customer_history: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Run the full case agent graph and return a structured result.
    Always returns a valid dict — never raises.
    """
    initial_state: AgentState = {
        "transaction": transaction,
        "score_result": score_result,
        "customer_history": customer_history or [],
        "evidence": "",
        "summary": "",
        "summary_source": "template",
        "risk_level": "",
        "suggested_action": "",
    }

    try:
        final_state = await _case_graph.ainvoke(initial_state)
        return {
            "summary": final_state.get("summary", ""),
            "summary_source": final_state.get("summary_source", "template"),
            "risk_level": final_state.get("risk_level", score_result.get("risk_level")),
            "suggested_action": final_state.get("suggested_action", score_result.get("suggested_action")),
            "evidence": final_state.get("evidence", ""),
        }
    except Exception as exc:
        logger.error(f"Case agent failed: {exc} — using fallback")
        return {
            "summary": _template_summary(score_result, transaction),
            "summary_source": "template",
            "risk_level": score_result.get("risk_level", "unknown"),
            "suggested_action": score_result.get("suggested_action", "review"),
            "evidence": "",
        }
