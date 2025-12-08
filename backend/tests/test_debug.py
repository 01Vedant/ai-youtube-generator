import os, sys, importlib
from fastapi.testclient import TestClient

def _load_app(debug_enabled: bool):
    # Set env BEFORE importing the module
    os.environ["DEBUG_API_ENABLED"] = "true" if debug_enabled else "false"
    os.environ["RATE_LIMIT_DISABLED"] = "true"  # disable RL in tests
    os.environ.setdefault("SAAS_ENABLED", "false")  # default off for tests
    # drop any half-loaded modules to avoid stale state
    for mod in ("app.routes.debug", "app.main"):
        if mod in sys.modules:
            del sys.modules[mod]
    main_mod = importlib.import_module("app.main")
    importlib.reload(main_mod)
    return main_mod.app


def test_debug_echo_get():
    app = _load_app(True)
    client = TestClient(app)
    r = client.get("/debug/echo?q=hi")
    assert r.status_code == 200
    assert r.json() == {"echo": "hi"}


def test_debug_echo_post():
    app = _load_app(True)
    client = TestClient(app)
    r = client.post("/debug/echo", json={"k": 1})
    assert r.status_code == 200
    assert r.json() == {"echo": {"k": 1}}


def test_debug_disabled_returns_404_or_405():
    app = _load_app(False)
    client = TestClient(app)
    r = client.get("/debug/echo?q=hi")
    assert r.status_code in (404, 405)


