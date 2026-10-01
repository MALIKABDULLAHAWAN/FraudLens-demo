"""
Prometheus metrics instrumentation.
Exported at /metrics (text format) and available as Python counters.
"""

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter, Response

router = APIRouter(tags=["monitoring"])

# ── Metrics ───────────────────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "fraudlens_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "fraudlens_request_duration_seconds",
    "HTTP request latency",
    ["endpoint"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

TRANSACTIONS_SCORED = Counter(
    "fraudlens_transactions_scored_total",
    "Total transactions scored by the ML model",
)

TRANSACTIONS_FLAGGED = Counter(
    "fraudlens_transactions_flagged_total",
    "Transactions flagged as potentially fraudulent",
)

DECISIONS_MADE = Counter(
    "fraudlens_decisions_total",
    "Analyst decisions made",
    ["action"],  # approve | reject | escalate
)

LLM_CALLS = Counter(
    "fraudlens_llm_calls_total",
    "LLM summary generation attempts",
    ["source"],  # llm | template
)


@router.get("/metrics", include_in_schema=False)
def prometheus_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
