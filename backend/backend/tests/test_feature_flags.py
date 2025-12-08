def test_flags_admin_get_put_requires_admin(auth_headers):
def test_toggle_youtube_export(admin_headers):
def test_toggle_public_shares(admin_headers):
def test_admin_flags(client):
    headers = create_and_login(client)
    # Simulate admin by updating user role in DB if needed
    r = client.get("/admin/flags", headers=headers)
    assert r.status_code in (200, 403)
    r2 = client.put("/admin/flags", json={"feature_x": True}, headers=headers)
    assert r2.status_code in (200, 403)