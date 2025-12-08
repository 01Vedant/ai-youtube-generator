def test_onboarding_state_and_event(client):
    r = client.get("/onboarding/state")
    assert r.status_code == 200
    r2 = client.post("/onboarding/event", json={"event": "welcome_seen"})
    assert r2.status_code == 200