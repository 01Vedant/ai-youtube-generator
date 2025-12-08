import os, sys, pathlib, importlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / 'app'
for p in (ROOT, APP):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

def _app_with_env(env_val: str):
    os.environ['APP_ENV'] = env_val
    import app.main as main
    importlib.reload(main)
    return main.app


def test_headers_present_in_prod():
    app = _app_with_env('prod')
    # Call a simple handler directly to get a Response-like object
    # Use status handler from app.routes.status for simplicity
    from app.routes.status import status_page
    resp = status_page()
    # Simulate middleware headers by constructing a Response through middleware path not possible here.
    # Instead, assert SecurityHeadersMiddleware logic by instantiating and calling dispatch on a dummy request.
    from starlette.requests import Request
    from starlette.responses import Response
    from app.middleware.security_headers import SecurityHeadersMiddleware
    async def _dummy_app(scope, receive, send):
        r = Response()
        await r(scope, receive, send)
    shm = SecurityHeadersMiddleware(_dummy_app)
    scope = {'type': 'http', 'method': 'GET', 'path': '/version', 'headers': []}
    req = Request(scope)
    async def _receive():
        return {'type': 'http.request'}
    async def _send(message):
        pass
    # Execute middleware dispatch
    import asyncio
    async def _call_next(_request):
        return Response("OK")
    resp2 = asyncio.run(shm.dispatch(req, _call_next))
    h = resp2.headers
    assert h.get('Strict-Transport-Security')
    assert h.get('X-Content-Type-Options') == 'nosniff'
    assert h.get('X-Frame-Options') == 'DENY'
    assert h.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
    assert h.get('Permissions-Policy')
    assert h.get('Content-Security-Policy')


def test_headers_absent_in_dev():
    app = _app_with_env('dev')
    from starlette.requests import Request
    from starlette.responses import Response
    from app.middleware.security_headers import SecurityHeadersMiddleware
    async def _dummy_app(scope, receive, send):
        r = Response()
        await r(scope, receive, send)
    shm = SecurityHeadersMiddleware(_dummy_app)
    scope = {'type': 'http', 'method': 'GET', 'path': '/version', 'headers': []}
    req = Request(scope)
    import asyncio
    async def _call_next(_request):
        return Response("OK")
    resp2 = asyncio.run(shm.dispatch(req, _call_next))
    h = resp2.headers
    # In dev, we do not set HSTS or CSP
    assert h.get('Strict-Transport-Security') is None
    assert h.get('Content-Security-Policy') is None
