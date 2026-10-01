"""
Application settings loaded from environment variables.
Never hardcode secrets — read from .env or container environment.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ───────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./fraudlens.db"

    # ── Auth ───────────────────────────────────────────────────
    SECRET_KEY: str = "dev-secret-change-in-production-use-32-hex-chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # ── ML ────────────────────────────────────────────────────
    MODEL_PATH: str = "artifacts/xgb_model.joblib"
    FRAUD_THRESHOLD: float = 0.5  # overridable at runtime

    # ── LLM ───────────────────────────────────────────────────
    LLM_BASE_URL: str = "http://localhost:11434/v1"
    LLM_API_KEY: str = "ollama"
    LLM_MODEL: str = "llama3.1"
    LLM_TIMEOUT: int = 8  # seconds before falling back to template

    # ── App ───────────────────────────────────────────────────
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8000"

    # ── Monitoring ────────────────────────────────────────────
    METRICS_ENABLED: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def artifacts_dir(self) -> Path:
        return Path(self.MODEL_PATH).parent

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
