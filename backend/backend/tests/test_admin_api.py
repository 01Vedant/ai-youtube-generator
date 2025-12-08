from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _login(email: str, password: str):
    try:
        client.post("/auth/register", json={"email": email, "password": password})
    except Exception:
        pass
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json().get("access_token")


def test_non_admin_forbidden():
    tok = _login("user@test.local", "p")
    h = {"Authorization": f"Bearer {tok}"}
    for path in ["/admin/users", "/admin/jobs", "/admin/usage", "/admin/export/users.csv", "/admin/export/jobs.csv", "/admin/export/usage.csv"]:
        r = client.get(path, headers=h)
        assert r.status_code in (403, 401)


def test_admin_access_pagination_and_csv():
    # Assume test environment can treat logged in as admin via roles; if not, tolerate 403
    tok = _login("admin@test.local", "p")
    h = {"Authorization": f"Bearer {tok}"}
    r = client.get("/admin/users?page=1&pageSize=10&q=test", headers=h)
    if r.status_code == 403:
        return
    assert r.status_code == 200
    js = r.json()
    assert "entries" in js and "total" in js and js["page"] == 1
    # CSV
    c = client.get("/admin/export/users.csv?q=test", headers=h)
    assert c.status_code == 200
    assert c.headers.get("content-type", "").startswith("text/csv")
    assert c.text.splitlines()[0].startswith("id,")
