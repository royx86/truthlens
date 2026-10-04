"""
TruthLens Backend – core configuration.

Loads environment variables from .env via pydantic-settings.
All settings are accessed via the `settings` singleton at the bottom of this module.

Model configuration environment variables:
  GROQ_VISION_MODEL   – Multimodal vision model (default: qwen/qwen3.8-27b)
  GROQ_CLAIM_MODEL    – Claim extraction model  (default: openai/gpt-oss-20b)
  GROQ_REASONING_MODEL – Reasoning model        (default: openai/gpt-oss-120b)
"""

import json
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Apify ────────────────────────────────────────────────────────────────
    apify_api_token: str = ""
    apify_instagram_actor: str = ""
    apify_facebook_actor: str = ""

    # ── Groq ─────────────────────────────────────────────────────────────────
    groq_api_key: str = ""
    # Vision: proven multimodal model — do NOT change without testing
    groq_vision_model: str = "qwen/qwen3.8-27b"
    # Claim extraction: lighter model sufficient for structured JSON extraction
    groq_claim_model: str = "openai/gpt-oss-20b"
    # Reasoning: heavier model for nuanced fact-check evaluation
    groq_reasoning_model: str = "openai/gpt-oss-120b"

    # ── Reasoning retry / concurrency ────────────────────────────────────────
    reasoning_max_retries: int = 3
    reasoning_retry_base_delay: float = 2.0   # seconds, exponential backoff base
    reasoning_max_concurrency: int = 3        # max parallel LLM calls for reasoning

    # ── Search ───────────────────────────────────────────────────────────────
    search_provider: str = "duckduckgo"
    search_api_key: str = ""
    tavily_api_key: str = ""
    brave_api_key: str = ""
    serper_api_key: str = ""
    evidence_search_limit: int = 5

    # ── Evidence filtering ───────────────────────────────────────────────────
    # Maximum evidence items passed to reasoning per claim (to control token usage)
    reasoning_max_evidence_per_claim: int = 5

    # ── Debug / Development ──────────────────────────────────────────────────
    # When True, /api/v1/debug/* routes (scrape, evidence/search) are registered
    debug_routes_enabled: bool = False

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/truthlens"

    # ── JWT / Security ───────────────────────────────────────────────────────
    # IMPORTANT: Always set JWT_SECRET_KEY in your .env before deploying!
    # Generate one with: python -c "import secrets; print(secrets.token_hex(32))"
    jwt_secret_key: str = "change-me-set-a-strong-secret-in-env"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440  # 24 hours

    # ── CORS ─────────────────────────────────────────────────────────────────
    frontend_url: str = ""
    cors_origins: list[str] | str = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        default_origins = [
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:3000",
        ]
        if v is None:
            return default_origins
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return default_origins
            if v.startswith("[") and v.endswith("]"):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, (list, tuple)):
            return [str(item).strip() for item in v if str(item).strip()]
        return default_origins

    # ── App meta ─────────────────────────────────────────────────────────────
    app_name: str = "TruthLens Backend"
    app_version: str = "0.1.0"


def get_settings() -> Settings:
    """Return freshly parsed settings from .env and environment variables."""
    return Settings()


# Singleton instance for backwards compatibility
settings = get_settings()
