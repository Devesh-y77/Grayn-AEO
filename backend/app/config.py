"""
Grayn AEO — Application Configuration

All settings are loaded from environment variables (or .env file).
Secrets are never committed. Provider modes auto-select based on
whether the corresponding API key is present.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """Typed, validated application settings."""

    # ── Project ───────────────────────────────────────────
    PROJECT_NAME: str = "Grayn AEO"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = False
    CORS_ORIGINS: list[str] = ["*"]

    # ── Supabase ──────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    DATABASE_URL: str = ""

    # ── Admin ─────────────────────────────────────────────
    ADMIN_TOKEN: str = "change-me-in-production"
    
    # ── MCP & External Services ───────────────────────────
    MCP_AUTH_TOKEN: str = ""
    GRAYN_AEO_API_KEY: str = ""

    # ── AI Providers ──────────────────────────────────────
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    GROK_API_KEY: str = ""
    PERPLEXITY_API_KEY: str = ""

    # ── Feature Flags ─────────────────────────────────────
    USE_MOCK_PROVIDERS: bool = False

    # ── CORS ──────────────────────────────────────────────
    CORS_ORIGINS: str = "*"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def openai_available(self) -> bool:
        return bool(self.OPENAI_API_KEY) and not self.USE_MOCK_PROVIDERS

    @property
    def gemini_available(self) -> bool:
        return bool(self.GEMINI_API_KEY) and not self.USE_MOCK_PROVIDERS

    @property
    def anthropic_available(self) -> bool:
        return bool(self.ANTHROPIC_API_KEY) and not self.USE_MOCK_PROVIDERS

    @property
    def groq_available(self) -> bool:
        return bool(self.GROQ_API_KEY) and not self.USE_MOCK_PROVIDERS

    @property
    def deepseek_available(self) -> bool:
        return bool(self.DEEPSEEK_API_KEY) and not self.USE_MOCK_PROVIDERS

    @property
    def perplexity_available(self) -> bool:
        return bool(self.PERPLEXITY_API_KEY) and not self.USE_MOCK_PROVIDERS

    @property
    def grok_available(self) -> bool:
        return bool(self.GROK_API_KEY) and not self.USE_MOCK_PROVIDERS

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton — one Settings instance per process."""
    return Settings()
