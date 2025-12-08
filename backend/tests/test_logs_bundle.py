def test_logs_bundle_admin(client, admin_headers):
def test_admin_logs_bundle(client):
    headers = create_and_login(client)
    r = client.get("/admin/logs/bundle.zip", headers=headers)
    assert r.status_code in (200, 403)
    if r.status_code == 200:
        assert "zip" in r.headers["content-type"]
    resp3 = client.get(f"/logs/bundle?from=2099-01-01&to=2099-01-01", headers=admin_headers)
    assert resp3.status_code == 204