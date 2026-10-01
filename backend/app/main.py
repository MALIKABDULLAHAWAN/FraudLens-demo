"""
FastAPI application factory.

Startup sequence:
1. Seed DB (tables + users + demo data)
2. Load ML model into memory
3. Register routers + middleware
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.core.monitoring import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    router as metrics_router,
)
from backend.app.api.auth import router as auth_router
from backend.app.api.transactions import router as tx_router
from backend.app.api.metrics import router as api_metrics_router

logger = logging.getLogger(__name__)
settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup tasks."""
    logger.info("FraudLens starting up...")

    # Seed database
    from backend.app.db.seed import seed_all
    seed_all()

    # Warm up ML model (loads into memory once)
    try:
        from backend.app.ml.scorer import get_fraud_model
        get_fraud_model()
        logger.info("ML model loaded and ready")
    except FileNotFoundError as e:
        logger.warning(f"ML model not found: {e}. Run scripts/train.py to train.")

    logger.info("FraudLens ready")
    yield
    logger.info("FraudLens shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="FraudLens API",
        description=(
            "Explainable fraud-review assistant. "
            "All data is synthetic — this is a demo application."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # ── CORS ──────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request instrumentation middleware ────────────────────
    @app.middleware("http")
    async def instrument(request: Request, call_next):
        t0 = time.monotonic()
        response = await call_next(request)
        elapsed = time.monotonic() - t0

        path = request.url.path
        if settings.METRICS_ENABLED and not path.startswith("/metrics"):
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=path,
                status_code=str(response.status_code),
            ).inc()
            REQUEST_LATENCY.labels(endpoint=path).observe(elapsed)

        return response

    # ── Routers ───────────────────────────────────────────────
    app.include_router(auth_router)
    app.include_router(tx_router)
    app.include_router(api_metrics_router)
    app.include_router(metrics_router)

    # ── Health ────────────────────────────────────────────────
    @app.get("/health", tags=["monitoring"])
    def health():
        return {"status": "ok", "version": "1.0.0"}

    # ── Serve React SPA (production) ──────────────────────────
    static_dir = Path("frontend/dist")
    if static_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def serve_spa(full_path: str):
            # Don't catch API routes
            if full_path.startswith("api/") or full_path in ("health", "metrics"):
                from fastapi import HTTPException
                raise HTTPException(status_code=404)
            index = static_dir / "index.html"
            return FileResponse(str(index))

    return app


app = create_app()
