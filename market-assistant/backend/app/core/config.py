from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Provider -> the settings field holding its API key. A prod deploy must supply
# the key for whichever LLM_PROVIDER is configured (see the prod guard below).
_PROVIDER_KEY_FIELD = {
    "groq": "GROQ_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Deployment environment. Fail-closed: the default is "prod" so a deploy
    # that forgets to set ENV runs with the dev auth stub DISABLED (see
    # app.core.auth._NON_PROD_ENVS, which admits the stub only for "dev"/"test").
    # Local dev must set ENV=dev; the test suite pins ENV=test (tests/conftest).
    # Only "test" mounts the test-only replay route (see app.main).
    env: str = "prod"
    database_url: str = "postgresql+asyncpg://market:market@localhost:5434/market_assistant"
    redis_url: str = "redis://localhost:6379/0"
    UNIVERSE_SIZE: int = 20
    UNIVERSE_QUOTE_ASSET: str = "USDT"
    BINANCE_WS_BASE_URL: str = "wss://stream.binance.com:9443"
    WS_MAX_BACKOFF_S: float = 60.0
    BACKFILL_RATE_LIMIT_MS: int = 250
    NEWS_FEED_URLS: list[str] = []
    EQUITY_POLL_INTERVAL_MIN: int = 15
    EQUITY_DELAY_MINUTES: int = 15

    # Chat assistant (Phase 10). Tests use a scripted provider, so keys may be unset.
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-sonnet-5"
    CHAT_RATE_LIMIT: int = 30
    CHAT_RATE_WINDOW_SECONDS: int = 3600

    # --- Phase 11: auth (Supabase JWT verification) ---
    jwt_secret: str = ""              # HS256 shared secret (Supabase legacy / local dev / tests)
    jwt_issuer: str = ""              # expected iss; "" disables the iss check
    jwt_audience: str = "authenticated"   # Supabase user-token aud
    supabase_url: str = ""            # https://<ref>.supabase.co
    supabase_jwks_url: str = ""       # if set -> verify RS256/ES256 via JWKS instead of HS256
    # --- Phase 11: hardening ---
    cors_allowed_origins: str = "http://localhost:5173"  # comma-separated origins
    # Comma-separated user UUIDs permitted to mutate instruments (create/seed/
    # patch) in prod. Empty => no admins (fail-closed) in prod; dev/test bypass.
    admin_user_ids: str = ""
    sentry_dsn: str = ""
    # --- Phase 11: alerts ---
    telegram_bot_token: str = ""
    telegram_rate_limit_per_min: int = 20
    # --- DB schema isolation (Supabase multi-project). "public" => unchanged local/CI behavior ---
    db_schema: str = "public"

    # --- Phase 12: free-tier survival knobs (required-with-explicit-default) ---
    max_universe_size: int = Field(default=25, ge=1)       # hard crypto universe cap
    max_backtest_span_days: int = Field(default=366, ge=1)  # max backtest window span
    candle_retention_days: int = Field(default=60, ge=1)   # 1m-candle retention window
    llm_daily_quota: int = Field(default=500, ge=1)        # global daily LLM call budget

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def effective_jwks_url(self) -> str:
        """JWKS endpoint to verify Supabase tokens against.

        Supabase now signs user tokens with asymmetric keys (ES256), so JWKS
        is the correct verification path. Prefer an explicit ``supabase_jwks_url``;
        otherwise derive it from ``supabase_url``. Empty only when neither is set
        (local dev / tests fall back to the HS256 ``jwt_secret``).
        """
        if self.supabase_jwks_url:
            return self.supabase_jwks_url
        if self.supabase_url:
            return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        return ""

    @model_validator(mode="after")
    def _fail_fast_in_prod(self) -> "Settings":
        """Fail-fast config guard (Phase 12 Task 1).

        Outside prod the localhost/empty defaults are intentional (local dev, CI).
        In prod, a missing critical secret must crash app construction with a
        readable, field-named error rather than binding a port on stub config.
        """
        # Accept prod aliases case-insensitively so ENV=production / PROD also
        # fail-close; dev/test/CI and any other value stay permissive.
        if self.env.strip().lower() not in {"prod", "production"}:
            return self

        errors: list[str] = []
        if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
            errors.append("database_url points at localhost — set the managed Postgres URL")
        if "localhost" in self.redis_url or "127.0.0.1" in self.redis_url:
            errors.append("redis_url points at localhost — set the managed Redis URL")
        if not self.jwt_secret and not self.effective_jwks_url:
            errors.append(
                "jwt_secret (or supabase_jwks_url / supabase_url) is required for auth"
            )
        if not self.jwt_issuer:
            errors.append(
                "jwt_issuer is required in prod so the token issuer (iss) is validated"
            )
        origins = self.cors_origins_list
        if not origins or any(
            ("localhost" in o or "127.0.0.1" in o) for o in origins
        ):
            errors.append(
                "cors_allowed_origins still points at localhost/default — set the "
                "deployed frontend origin(s)"
            )
        key_field = _PROVIDER_KEY_FIELD.get(self.LLM_PROVIDER.lower())
        if key_field is None:
            errors.append(f"LLM_PROVIDER {self.LLM_PROVIDER!r} is not a known provider")
        elif not getattr(self, key_field):
            errors.append(f"{key_field} is required for LLM_PROVIDER={self.LLM_PROVIDER}")
        # telegram_bot_token is intentionally NOT boot-critical: alert delivery is
        # an optional feature. Without it the alert worker simply doesn't push to
        # Telegram; the rest of the app runs. Requiring it here would take the
        # whole deploy down for a non-essential channel.

        if errors:
            raise ValueError("invalid prod configuration: " + "; ".join(errors))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
