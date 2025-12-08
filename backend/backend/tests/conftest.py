
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db, get_conn

@pytest.fixture(scope="session", autouse=True)
def init_db():
    # If your app has a startup/init_db function, call it here
    pass

@pytest.fixture
def client():
    return TestClient(app)

def create_and_login(client, email="test@example.com", password="testpass"):
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}
