import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTES_DB_PATH", str(tmp_path / "version.db"))
    with TestClient(app) as c:
        yield c


def test_version_returns_1_0_0(client):
    res = client.get("/version")
    assert res.status_code == 200
    assert res.json() == {"version": "1.0.0"}
