import pytest
from fastapi.testclient import TestClient

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend" / "backend"))  # enables: import app.*
sys.path.insert(0, str(REPO / "backend"))             # enables: import backend.*

from backend.backend.main import app  # use inner app

@pytest.fixture(scope="session")
def client():
    return TestClient(app)
