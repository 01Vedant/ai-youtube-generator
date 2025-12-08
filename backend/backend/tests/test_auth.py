def test_register_login_me_refresh_roundtrip():
def test_auth_flow(client):
    email = "user@example.com"
    password = "testpass"
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 200
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    token = r.json()["access_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    new_access = r.json()['access_token']
    r = client.get('/auth/me', headers={'Authorization': f'Bearer {new_access}'})
    assert r.status_code == 200


def test_login_wrong_password():
    email = 'user2@example.com'
    client.post('/auth/register', json={'email': email, 'password': 'correct'})
    r = client.post('/auth/login', json={'email': email, 'password': 'wrong'})
    assert r.status_code == 401
