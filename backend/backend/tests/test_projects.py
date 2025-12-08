def auth(email: str) -> dict:
def test_projects_crud_and_visibility_and_protection():
def test_projects_crud(client):
    headers = create_and_login(client)
    r = client.post("/projects", json={"title": "Test Project"}, headers=headers)
    assert r.status_code == 200
    pid = r.json()["id"]
    r = client.get("/projects", headers=headers)
    assert r.status_code == 200
    assert any(p["id"] == pid for p in r.json())
    r = client.get(f"/projects/{pid}", headers=headers)
    assert r.status_code == 200
    lst = r.json()
    assert isinstance(lst, list) and len(lst) >= 1

    # link a job to project
    job_id = 'job-123'
    r = client.post(f'/projects/{pid}/assign', json={'job_id': job_id}, headers=headers_a)
    assert r.status_code == 200

    # project detail shows job and count increments
    r = client.get(f'/projects/{pid}', headers=headers_a)
    assert r.status_code == 200
    detail = r.json()
    assert detail['total'] == 1
    assert any(e['id'] == job_id for e in detail['entries'])

    # user B cannot see projects of A
    headers_b = auth('b@example.com')
    r = client.get('/projects', headers=headers_b)
    assert r.status_code == 200
    assert all(p['id'] != pid for p in r.json())

    # delete protection -> 409
    r = client.delete(f'/projects/{pid}', headers=headers_a)
    assert r.status_code == 409

    # unassign then delete succeeds
    r = client.post(f'/projects/{pid}/unassign', json={'job_id': job_id}, headers=headers_a)
    assert r.status_code == 200
    r = client.delete(f'/projects/{pid}', headers=headers_a)
    assert r.status_code == 200
    assert r.json()['ok'] is True
