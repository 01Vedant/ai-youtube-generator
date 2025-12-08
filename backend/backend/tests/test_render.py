def test_render_job(client):
    headers = create_and_login(client)
    r = client.post("/render", json={"project_id": "test", "scene": "intro"}, headers=headers)
    assert r.status_code == 200
    job_id = r.json()["job_id"]
    r = client.get(f"/render/{job_id}", headers=headers)
    assert r.status_code == 200
