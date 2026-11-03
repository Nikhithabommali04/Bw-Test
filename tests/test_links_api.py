import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Each test gets its own database; the real data/notes.db is never touched.
    monkeypatch.setenv("NOTES_DB_PATH", str(tmp_path / "links.db"))
    with TestClient(app) as c:
        yield c


def create(client, url="https://example.com", title="", tag=""):
    res = client.post("/api/links", json={"url": url, "title": title, "tag": tag})
    assert res.status_code == 201
    return res.json()


def test_list_empty(client):
    res = client.get("/api/links")
    assert res.status_code == 200
    assert res.json() == []


def test_create_returns_201_with_defaults(client):
    res = client.post("/api/links", json={"url": "http://example.com/a"})
    assert res.status_code == 201
    body = res.json()
    assert set(body) == {"id", "url", "title", "tag", "created_at"}
    assert body["url"] == "http://example.com/a"
    assert body["title"] == ""
    assert body["tag"] == ""
    assert isinstance(body["id"], int)


def test_list_orders_by_tag_then_id(client):
    b = create(client, url="https://b.example", tag="work")
    a = create(client, url="https://a.example", tag="home")
    c = create(client, url="https://c.example", tag="home")

    ids = [link["id"] for link in client.get("/api/links").json()]
    assert ids == [a["id"], c["id"], b["id"]]


def test_filter_by_exact_tag(client):
    home = create(client, tag="home")
    create(client, tag="work")
    create(client, tag="homework")

    res = client.get("/api/links", params={"tag": "home"})
    assert res.status_code == 200
    assert [link["id"] for link in res.json()] == [home["id"]]


def test_filter_with_unknown_tag_returns_empty(client):
    create(client, tag="home")
    assert client.get("/api/links", params={"tag": "nope"}).json() == []


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "ftp://example.com/file",
        "file:///etc/passwd",
        "example.com",
        "http://",
        "",
    ],
)
def test_create_rejects_non_http_urls(client, url):
    res = client.post("/api/links", json={"url": url})
    assert res.status_code == 422
    assert client.get("/api/links").json() == []


def test_create_requires_url(client):
    assert client.post("/api/links", json={"title": "x"}).status_code == 422


def test_create_rejects_overlong_fields(client):
    assert client.post("/api/links", json={"url": "https://e.x/" + "a" * 2000}).status_code == 422
    assert client.post("/api/links", json={"url": "https://e.x", "title": "t" * 201}).status_code == 422
    assert client.post("/api/links", json={"url": "https://e.x", "tag": "t" * 51}).status_code == 422


def test_delete_returns_204_and_removes_link(client):
    link = create(client)
    res = client.delete(f"/api/links/{link['id']}")
    assert res.status_code == 204
    assert res.content == b""
    assert client.get("/api/links").json() == []


def test_delete_missing_returns_404(client):
    res = client.delete("/api/links/9999")
    assert res.status_code == 404
    assert res.json() == {"detail": "Link not found"}


def test_links_and_notes_are_independent(client):
    create(client)
    assert client.get("/api/notes").json() == []
    client.post("/api/notes", json={"title": "n"})
    assert len(client.get("/api/links").json()) == 1
