"""Optional Sentry error reporting: a complete no-op unless SENTRY_DSN is set."""

from app.core.config import get_settings


def init_sentry() -> None:
    """Initialize Sentry only when a DSN is configured.

    The default (empty DSN) path returns immediately without importing
    sentry_sdk, so CI/local/tests never initialize Sentry or touch the network.
    """
    settings = get_settings()
    if not settings.sentry_dsn:
        return

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        environment=settings.env,
        traces_sample_rate=0.0,
    )
