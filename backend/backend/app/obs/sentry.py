import os


def init_sentry():
    dsn = os.getenv("SENTRY_DSN", "")
    if not dsn:
        return
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=dsn, traces_sample_rate=0.1)
    except Exception:
        # No-op if SDK not installed or init fails
        pass
