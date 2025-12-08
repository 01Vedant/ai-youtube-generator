import asyncio
from fastapi import Request
from fastapi.testclient import TestClient
from app.main import app

# Basic tests for share views analytics and HTML/oEmbed/robots/sitemap

client = TestClient(app)


def test_share_view_records_and_html_json_modes(monkeypatch):
    # Create a share first via helper; assume existing endpoint to create
    # For test simplicity, insert a share directly
    from app.db import get_conn
    conn = get_conn()
    try:
        conn.execute("INSERT INTO shares (share_id, job_id, user_id, created_at, revoked) VALUES (?,?,?,?,0)", ("testshare1", "job123", "user1", "2024-01-01T00:00:00Z"))
        conn.execute("INSERT OR REPLACE INTO jobs_index (id, user_id, title, created_at) VALUES (?,?,?,?)", ("job123", "user1", "Test Job", "2024-01-01T00:00:00Z"))
        conn.commit()
    finally:
        conn.close()

    # Normal UA returns JSON and records a view
    r = client.get("/s/testshare1", headers={"User-Agent": "Mozilla/5.0"})
    assert r.status_code == 200
    data = r.json()
    assert data["job_id"] == "job123"

    # Crawler UA returns HTML
    r2 = client.get("/s/testshare1", headers={"User-Agent": "Twitterbot"})
    assert r2.status_code == 200
    assert "<meta property=\"og:title\"" in r2.text


def test_oembed_endpoint():
    # Ensure share exists
    from app.db import get_conn
    conn = get_conn()
    try:
        conn.execute("INSERT INTO shares (share_id, job_id, user_id, created_at, revoked) VALUES (?,?,?,?,0)", ("testshare2", "jobxyz", "user1", "2024-01-01T00:00:00Z"))
        conn.execute("INSERT OR REPLACE INTO jobs_index (id, user_id, title, created_at) VALUES (?,?,?,?)", ("jobxyz", "user1", "Job X", "2024-01-01T00:00:00Z"))
        conn.commit()
    finally:
        conn.close()

    base = "http://testserver"
    r = client.get("/oembed", params={"url": f"{base}/s/testshare2"})
    assert r.status_code == 200
    j = r.json()
    assert j["type"] == "video"
    assert "iframe" in j["html"]


def test_robots_and_sitemap():
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert "Allow: /s/" in r.text
    assert "Disallow: /api/" in r.text

    # create a share for sitemap
    from app.db import get_conn
    conn = get_conn()
    try:
        conn.execute("INSERT INTO shares (share_id, job_id, user_id, created_at, revoked) VALUES (?,?,?,?,0)", ("testshare3", "jobabc", "user1", "2024-01-01T00:00:00Z"))
        conn.commit()
    finally:
        conn.close()

    r2 = client.get("/sitemap.xml")
    assert r2.status_code == 200
    assert "/s/testshare3" in r2.text


def test_admin_analytics_summary_and_daily(monkeypatch):
    # monkeypatch admin auth to bypass
    from app.auth.security import get_current_user
    def fake_user():
        return {"id": "admin", "roles": ["admin"]}
    app.dependency_overrides[get_current_user] = fake_user

    # seed some views
    from app.db import get_conn
    conn = get_conn()
    try:
        conn.execute("INSERT OR IGNORE INTO shares (share_id, job_id, user_id, created_at, revoked) VALUES (?,?,?,?,0)", ("testshare4", "jobv", "user1", "2024-01-01T00:00:00Z"))
        conn.execute("CREATE TABLE IF NOT EXISTS share_views (id TEXT PRIMARY KEY, share_id TEXT, ts TEXT, ip_hash TEXT, ua TEXT, referer TEXT)")
        conn.execute("INSERT INTO share_views (id, share_id, ts, ip_hash, ua, referer) VALUES (?,?,?,?,?,?)", ("v1","testshare4","2024-01-01","ip1","ua","ref"))
        conn.execute("INSERT INTO share_views (id, share_id, ts, ip_hash, ua, referer) VALUES (?,?,?,?,?,?)", ("v2","testshare4","2024-01-02","ip2","ua","ref"))
        conn.commit()
    finally:
        conn.close()

    r = client.get("/admin/shares/testshare4/analytics/summary")
    assert r.status_code == 200
    j = r.json()
    assert "views_7d" in j and "unique_ips_7d" in j

    r2 = client.get("/admin/shares/testshare4/analytics/daily", params={"days": 30})
    assert r2.status_code == 200
    j2 = r2.json()
    assert "days" in j2 and "views" in j2 and "unique_ips" in j2

    r3 = client.get("/admin/shares/testshare4/analytics/export.csv")
    assert r3.status_code == 200
    assert "ts,ip_hash,ua,referer" in r3.text
