"""
Application settings — Infrastructure layer.

Follows 12-factor app principles with environment variable configuration.
This is the authoritative location of all settings classes.
tacto/config/settings.py is a backward-compatibility shim that re-exports from here.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application-level settings."""

    name: str = Field(default="TactoFlow", alias="APP_NAME")
    version: str = Field(default="0.0.1", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")

    # AI behaviour
    ai_disable_hours: int = Field(default=12, alias="AI_DISABLE_HOURS")
    ai_reopen_buffer_minutes: int = Field(default=10, alias="AI_REOPEN_BUFFER_MINUTES")
    conversation_history_limit: int = Field(default=10, alias="CONVERSATION_HISTORY_LIMIT")

    # Testing / override flags
    bypass_hours_check: bool = Field(
        default=False,
        alias="BYPASS_HOURS_CHECK",
        description="Set true to treat every restaurant as open (useful for local testing).",
    )

    # Locale defaults
    default_timezone: str = Field(default="America/Cuiaba", alias="DEFAULT_TIMEZONE")

    # Security — API Key auth (empty = disabled)
    api_key: str = Field(default="", alias="API_KEY")

    # Rate limiting — requests per minute per IP (0 = disabled)
    rate_limit_rpm: int = Field(default=60, alias="RATE_LIMIT_RPM")

    # CORS — comma-separated list of allowed origins (empty = use debug mode default)
    # Example: "https://app.example.com,https://admin.example.com"
    cors_origins: str = Field(default="", alias="CORS_ORIGINS")

    # AI Assistant Identity
    attendant_name: str = Field(default="Maria", alias="ATTENDANT_NAME")

    # Circuit Breaker settings
    circuit_breaker_failure_threshold: int = Field(default=5, alias="CIRCUIT_BREAKER_FAILURE_THRESHOLD")
    circuit_breaker_recovery_timeout: float = Field(default=30.0, alias="CIRCUIT_BREAKER_RECOVERY_TIMEOUT")

    # Memory retrieval limits
    memory_short_term_limit: int = Field(default=20, alias="MEMORY_SHORT_TERM_LIMIT")
    memory_medium_term_limit: int = Field(default=5, alias="MEMORY_MEDIUM_TERM_LIMIT")
    memory_long_term_limit: int = Field(default=10, alias="MEMORY_LONG_TERM_LIMIT")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class DatabaseSettings(BaseSettings):
    """PostgreSQL database settings."""

    host: str = Field(default="localhost", alias="DB_HOST")
    port: int = Field(default=5432, alias="DB_PORT")
    user: str = Field(default="tacto", alias="DB_USER")
    password: str = Field(default="tacto", alias="DB_PASSWORD")
    name: str = Field(default="tacto_db", alias="DB_NAME")
    echo: bool = Field(default=False, alias="DB_ECHO")
    pool_size: int = Field(default=5, alias="DB_POOL_SIZE")
    max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def async_url(self) -> str:
        """Build async database URL."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    @property
    def sync_url(self) -> str:
        """Build sync database URL (for migrations)."""
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


class RedisSettings(BaseSettings):
    """Redis settings."""

    host: str = Field(default="localhost", alias="REDIS_HOST")
    port: int = Field(default=6379, alias="REDIS_PORT")
    password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")
    db: int = Field(default=0, alias="REDIS_DB")
    buffer_ttl: int = Field(default=5, alias="REDIS_BUFFER_TTL")
    memory_ttl: int = Field(default=3600, alias="REDIS_MEMORY_TTL")
    buffer_window_seconds: int = Field(default=5, alias="REDIS_BUFFER_WINDOW_SECONDS")
    buffer_lock_ttl: int = Field(default=10, alias="REDIS_BUFFER_LOCK_TTL")
    echo_tracker_ttl: int = Field(default=15, alias="REDIS_ECHO_TRACKER_TTL")
    message_id_tracker_ttl: int = Field(default=300, alias="REDIS_MSG_ID_TRACKER_TTL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def url(self) -> str:
        """Build Redis URL."""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class TactoAPISettings(BaseSettings):
    """Tacto external API settings."""

    base_url: str = Field(default="https://api-externa.tactonuvem.com.br", alias="TACTO_API_BASE_URL")
    auth_url: str = Field(default="https://accounts.tactonuvem.com.br/connect/token", alias="TACTO_AUTH_URL")
    client_id: str = Field(default="integracao-externa", alias="TACTO_CLIENT_ID")
    client_secret: str = Field(default="", alias="TACTO_CLIENT_SECRET")
    default_scope: Optional[str] = Field(default=None, alias="TACTO_DEFAULT_SCOPE")
    http_timeout: int = Field(default=120, alias="TACTO_HTTP_TIMEOUT")
    chave_origem: str = Field(default="", alias="TACTO_CHAVE_ORIGEM")

    # Cache TTLs
    menu_cache_ttl: int = Field(default=3600, alias="TACTO_MENU_CACHE_TTL")
    institutional_cache_ttl: int = Field(default=86400, alias="TACTO_INSTITUTIONAL_CACHE_TTL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("base_url", "auth_url", mode="before")
    @classmethod
    def strip_quotes(cls, v: str) -> str:
        """Remove quotes from URL strings."""
        if isinstance(v, str):
            return v.strip('"').strip("'")
        return v

    @field_validator("default_scope", mode="before")
    @classmethod
    def parse_scope(cls, v: Optional[str]) -> Optional[str]:
        """Parse scope, treating 'None' string as None."""
        if v is None or v == "None" or v == "":
            return None
        return v


class JoinAPISettings(BaseSettings):
    """Join Developer API settings."""

    base_url: str = Field(default="https://api-prd.joindeveloper.com.br", alias="JOIN_API_BASE_URL")
    token_cliente: str = Field(default="", alias="JOIN_TOKEN_CLIENTE")
    http_timeout: int = Field(default=30, alias="JOIN_HTTP_TIMEOUT")

    # Webhook security — HMAC signature validation
    # If set, all webhook requests must include valid X-Hub-Signature-256 header
    webhook_secret: str = Field(default="", alias="JOIN_WEBHOOK_SECRET")

    # Typing simulation (humanized delay before sending)
    typing_chars_per_sec: int = Field(default=40, alias="JOIN_TYPING_CHARS_PER_SEC")
    typing_variance: float = Field(default=0.20, alias="JOIN_TYPING_VARIANCE")
    typing_min_ms: int = Field(default=2000, alias="JOIN_TYPING_MIN_MS")
    typing_max_ms: int = Field(default=12000, alias="JOIN_TYPING_MAX_MS")

    # Retry policy
    retry_max_attempts: int = Field(default=3, alias="JOIN_RETRY_MAX_ATTEMPTS")
    retry_base_delay: float = Field(default=1.0, alias="JOIN_RETRY_BASE_DELAY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def hmac_enabled(self) -> bool:
        """Check if HMAC validation is enabled."""
        return bool(self.webhook_secret)


class LangSmithSettings(BaseSettings):
    """LangSmith observability settings."""

    tracing: bool = Field(default=False, alias="LANGSMITH_TRACING")
    api_key: str = Field(default="", alias="LANGSMITH_API_KEY")
    project: str = Field(default="Tacto-System", alias="LANGSMITH_PROJECT")
    endpoint: str = Field(
        default="https://api.smith.langchain.com", alias="LANGSMITH_ENDPOINT"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class GeminiSettings(BaseSettings):
    """
    Google Gemini AI settings.

    Structure:
    - Global defaults (GEMINI_*): fallback values shared across all agents.
    - Per-level overrides (LEVEL1_*, LEVEL2_*, ...): each agent level can
      independently configure its model, temperature, token limit, and RAG
      search limit. Add a new LEVEL<N>_* block when a new agent level is created.
    """

    # -------------------------------------------------------------------------
    # Credentials & embedding (shared across all levels)
    # -------------------------------------------------------------------------
    api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    embedding_model: str = Field(
        default="models/gemini-embedding-001", alias="EMBEDDING_MODEL"
    )
    embedding_dimension: int = Field(default=768, alias="EMBEDDING_DIMENSION")

    # -------------------------------------------------------------------------
    # Global defaults — used as fallback when no per-level value is set
    # -------------------------------------------------------------------------
    llm_model: str = Field(default="gemini-2.5-flash", alias="LLM_MODEL")
    max_tokens: int = Field(default=2048, alias="GEMINI_MAX_TOKENS")
    temperature: float = Field(default=0.7, alias="GEMINI_TEMPERATURE")
    rag_search_limit: int = Field(default=10, alias="RAG_SEARCH_LIMIT")

    # -------------------------------------------------------------------------
    # Level 1 agent — conversational assistant (basic automation)
    # -------------------------------------------------------------------------
    level1_llm_model: str = Field(default="gemini-2.5-flash", alias="LEVEL1_LLM_MODEL")
    level1_temperature: float = Field(default=0.7, alias="LEVEL1_TEMPERATURE")
    level1_max_tokens: int = Field(default=3000, alias="LEVEL1_MAX_TOKENS")
    level1_rag_search_limit: int = Field(default=10, alias="LEVEL1_RAG_SEARCH_LIMIT")

    # -------------------------------------------------------------------------
    # Level 2 agent — (reserved for future expansion)
    # Add LEVEL2_LLM_MODEL, LEVEL2_TEMPERATURE, LEVEL2_MAX_TOKENS,
    # LEVEL2_RAG_SEARCH_LIMIT here when Level2Agent is implemented.
    # -------------------------------------------------------------------------

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class Settings(BaseSettings):
    """
    Main settings class aggregating all configuration sections.

    Usage:
        settings = get_settings()
        print(settings.app.name)
        print(settings.database.async_url)
    """

    app: AppSettings = Field(default_factory=AppSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    tacto: TactoAPISettings = Field(default_factory=TactoAPISettings)
    join: JoinAPISettings = Field(default_factory=JoinAPISettings)
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    langsmith: LangSmithSettings = Field(default_factory=LangSmithSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are loaded only once.
    """
    return Settings()
