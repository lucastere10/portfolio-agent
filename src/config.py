"""Application configuration loaded from environment variables."""

from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".enV"),
        extra="ignore",
        populate_by_name=True,
        case_sensitive=False,
        env_prefix="PORTFOLIO_AGENT_"
    )

    # LLM provider selection (LLM_PROVIDER has no PORTFOLIO_AGENT_ prefix in .env)
    llm_provider: Literal["gemini", "openai"] = Field(
        default="gemini",
        validation_alias=AliasChoices("LLM_PROVIDER", "PORTFOLIO_AGENT_LLM_PROVIDER"),
    )

    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4.1-mini")
    openai_base_url: str = Field(default="https://api.openai.com/v1")

    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-2.0-flash")

    # App
    app_name: str = "portfolio-agent"
    app_version: str = Field(
        default="0.1.0",
        validation_alias=AliasChoices("APP_VERSION", "PORTFOLIO_AGENT_APP_VERSION"),
    )
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "https://localhost:3000"],
        validation_alias=AliasChoices("CORS_ORIGINS", "PORTFOLIO_AGENT_CORS_ORIGINS"),
    )
    frontend_base_url: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices(
            "PORTFOLIO_WEB_BASE_URL",
            "PORTFOLIO_AGENT_FRONTEND_BASE_URL",
        ),
    )
    debug: bool = Field(
        default=False,
        validation_alias=AliasChoices("DEBUG", "PORTFOLIO_AGENT_DEBUG"),
    )

    # Session (ADK-backed in-memory store; swap BaseSessionService for Redis later)
    session_ttl_seconds: int = Field(
        default=1800,
        validation_alias=AliasChoices(
            "SESSION_TTL_SECONDS",
            "PORTFOLIO_AGENT_SESSION_TTL_SECONDS",
        ),
    )
    session_max_messages: int = Field(
        default=20,
        validation_alias=AliasChoices(
            "SESSION_MAX_MESSAGES",
            "PORTFOLIO_AGENT_SESSION_MAX_MESSAGES",
        ),
    )
    default_user_id: str = "portfolio-visitor"

settings = Settings()
