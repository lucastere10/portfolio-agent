"""Application configuration loaded from environment variables."""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".enV"),
        extra="ignore",
        populate_by_name=True,
        case_sensitive=False,
        env_prefix="PORTFOLIO_AGENT_",
    )

    # Preferred model: provider:model_id (fallbacks live in providers/registry.py)
    llm_model: str = Field(
        default="openai:gpt-5.6-luna",
        validation_alias=AliasChoices("LLM_MODEL", "PORTFOLIO_AGENT_LLM_MODEL"),
    )

    openai_api_key: str = Field(default="")
    openai_base_url: str = Field(default="https://api.openai.com/v1")

    gemini_api_key: str = Field(default="")

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
