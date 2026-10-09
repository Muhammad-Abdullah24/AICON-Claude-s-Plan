import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app


@pytest.fixture(scope="session")
def client():
    with TestClient(create_app()) as c:  # `with` runs the startup that loads artifacts
        yield c


@pytest.fixture(scope="session")
def meta(client):
    return client.get("/api/meta").json()
