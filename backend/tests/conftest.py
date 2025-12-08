import pytest
from fastapi.testclient import TestClient
from backend.backend.main import app  # use inner app


@pytest.fixture(scope="session")
def client():
    return TestClient(app)
