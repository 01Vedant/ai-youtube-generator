def test_stub_usage_today(client):
    r = client.get("/usage/today")
    assert r.status_code == 200
    j = r.json()
    assert "used" in j and "limit" in j and "remaining" in j and "reset_at" in j

def test_stub_templates(client):
    r = client.get("/api/templates")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_stub_projects(client):
    r = client.get("/projects")
    assert r.status_code == 200
    assert isinstance(r.json(), list)