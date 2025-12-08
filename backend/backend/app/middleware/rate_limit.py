class RateLimitMiddleware:
    def __init__(self, app, **_):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Placeholder: no rate limiting enforced in this stub.
        await self.app(scope, receive, send)
