import os, sys, pathlib
import importlib
from fastapi import HTTPException

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "app"
for p in (ROOT, APP):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

from app.db import init_db, get_conn
from app.routes.templates_marketplace import (
    list_marketplace_templates,
    get_marketplace_template,
)


def seed():
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO templates (id, title, description, category, thumb, plan_json, inputs_schema, visibility, user_id, downloads, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,strftime('%Y-%m-%dT%H:%M:%SZ','now'))
            """,
            ("tpl_flag_a", "Flag A", None, None, None, "{}", None, "shared", "uX", 0),
        )
        conn.commit()
    finally:
        conn.close()


def test_flag_off_returns_404(monkeypatch):
    init_db()
    seed()
    monkeypatch.setenv("FEATURE_TEMPLATES_MARKETPLACE", "0")
    import app.settings as settings
    importlib.reload(settings)
    import app.routes.templates_marketplace as mp
    importlib.reload(mp)
    try:
        list_marketplace_templates()
        assert False, "Expected 404"
    except HTTPException as e:
        assert e.status_code == 404
    try:
        get_marketplace_template("tpl_flag_a")
        assert False, "Expected 404"
    except HTTPException as e:
        assert e.status_code == 404


def test_flag_on_returns_data(monkeypatch):
    init_db()
    seed()
    monkeypatch.setenv("FEATURE_TEMPLATES_MARKETPLACE", "1")
    import app.settings as settings
    importlib.reload(settings)
    import app.routes.templates_marketplace as mp
    importlib.reload(mp)
    data = list_marketplace_templates()
    assert any(it["id"] == "tpl_flag_a" for it in data["items"])