import pytest
from fastapi.testclient import TestClient

from backend.main import BODY_MAX, TITLE_MAX, app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # The lifespan hook reads NOTES_DB_PATH at startup, so each test gets its own database.
    monkeypatch.setenv("NOTES_DB_PATH", str(tmp_path / "notes.db"))
    with TestClient(app) as c:
        yield c


def create(client, title="", body=""):
    res = client.post("/api/notes", json={"title": title, "body": body})
    assert res.status_code == 201
    return res.json()


def test_list_empty(client):
    res = client.get("/api/notes")
    assert res.status_code == 200
    assert res.json() == []


def test_list_orders_most_recently_updated_first(client):
    a = create(client, title="a")
    b = create(client, title="b")
    c = create(client, title="c")

    assert [n["id"] for n in client.get("/api/notes").json()] == [c["id"], b["id"], a["id"]]

    client.put(f"/api/notes/{a['id']}", json={"title": "a2"})

    titles = [n["title"] for n in client.get("/api/notes").json()]
    assert titles[0] == "a2"


def test_create_returns_201_with_defaults(client):
    res = client.post("/api/notes", json={})
    assert res.status_code == 201
    note = res.json()
    assert isinstance(note["id"], int)
    assert note["title"] == ""
    assert note["body"] == ""
    assert note["created_at"]
    assert note["created_at"] == note["updated_at"]


def test_create_stores_given_fields(client):
    note = create(client, title="Hello", body="World")
    assert note["title"] == "Hello"
    assert note["body"] == "World"


def test_put_partial_update_keeps_omitted_fields(client):
    note = create(client, title="t", body="b")

    res = client.put(f"/api/notes/{note['id']}", json={"title": "new"})
    assert res.status_code == 200
    updated = res.json()
    assert updated["title"] == "new"
    assert updated["body"] == "b"
    assert updated["created_at"] == note["created_at"]

    res = client.put(f"/api/notes/{note['id']}", json={"body": "x"})
    assert res.json()["title"] == "new"
    assert res.json()["body"] == "x"


def test_put_null_field_is_rejected(client):
    note = create(client, title="t", body="b")
    res = client.put(f"/api/notes/{note['id']}", json={"title": None})
    assert res.status_code == 422


def test_put_missing_note_returns_404(client):
    res = client.put("/api/notes/9999", json={"title": "x"})
    assert res.status_code == 404
    assert res.json()["detail"] == "Note not found"


def test_delete_returns_204_and_removes_note(client):
    note = create(client, title="gone")

    res = client.delete(f"/api/notes/{note['id']}")
    assert res.status_code == 204
    assert res.content == b""

    assert client.get("/api/notes").json() == []


def test_delete_missing_note_returns_404(client):
    res = client.delete("/api/notes/9999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Note not found"


def test_delete_twice_returns_404_second_time(client):
    note = create(client)
    assert client.delete(f"/api/notes/{note['id']}").status_code == 204
    assert client.delete(f"/api/notes/{note['id']}").status_code == 404


def test_list_reflects_create_update_and_delete(client):
    first = create(client, title="first")
    second = create(client, title="second")

    client.put(f"/api/notes/{first['id']}", json={"body": "edited"})
    notes = {n["id"]: n for n in client.get("/api/notes").json()}
    assert len(notes) == 2
    assert notes[first["id"]]["body"] == "edited"

    client.delete(f"/api/notes/{second['id']}")
    remaining = client.get("/api/notes").json()
    assert [n["id"] for n in remaining] == [first["id"]]


def test_title_at_max_length_is_accepted(client):
    res = client.post("/api/notes", json={"title": "x" * TITLE_MAX})
    assert res.status_code == 201


def test_title_over_max_length_returns_422(client):
    res = client.post("/api/notes", json={"title": "x" * (TITLE_MAX + 1)})
    assert res.status_code == 422


def test_body_at_max_length_is_accepted(client):
    res = client.post("/api/notes", json={"body": "x" * BODY_MAX})
    assert res.status_code == 201


def test_body_over_max_length_returns_422(client):
    res = client.post("/api/notes", json={"body": "x" * (BODY_MAX + 1)})
    assert res.status_code == 422


def test_put_over_max_length_returns_422(client):
    note = create(client)
    res = client.put(f"/api/notes/{note['id']}", json={"title": "x" * (TITLE_MAX + 1)})
    assert res.status_code == 422


def test_non_int_id_returns_422(client):
    assert client.put("/api/notes/abc", json={"title": "x"}).status_code == 422
    assert client.delete("/api/notes/abc").status_code == 422


def test_sql_injection_looking_title_is_stored_literally(client):
    payload = "'); DROP TABLE notes; --"
    note = create(client, title=payload)
    assert note["title"] == payload

    notes = client.get("/api/notes").json()
    assert [n["title"] for n in notes] == [payload]


def test_sql_injection_looking_update_is_stored_literally(client):
    note = create(client, title="safe")
    payload = "x' OR '1'='1"

    res = client.put(f"/api/notes/{note['id']}", json={"title": payload})
    assert res.status_code == 200
    assert res.json()["title"] == payload

    # The table is intact and other rows are untouched.
    other = create(client, title="other")
    titles = {n["id"]: n["title"] for n in client.get("/api/notes").json()}
    assert titles == {note["id"]: payload, other["id"]: "other"}
