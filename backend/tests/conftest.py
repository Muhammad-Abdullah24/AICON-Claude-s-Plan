import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app


@pytest.fixture(autouse=True)
def _news_offline(monkeypatch):
    """Tests never hit the network (docs/PIVOT.md rule 6): the news feed falls back to its committed snapshot."""
    from backend.app.news import fetch

    def offline(_url):
        raise OSError("no network in tests")

    monkeypatch.setattr(fetch, "_default_opener", offline)


@pytest.fixture(scope="session")
def client():
    with TestClient(create_app()) as c:  # `with` runs the startup that loads artifacts
        yield c


@pytest.fixture(scope="session")
def meta(client):
    return client.get("/api/meta").json()
