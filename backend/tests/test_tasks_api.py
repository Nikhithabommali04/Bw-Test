import pytest
from fastapi.testclient import TestClient

import main
from main import app


@pytest.fixture(autouse=True)
def reset_store():
    # The store is module-level and in-memory; reset it so tests are independent.
    with main._lock:
        main._tasks.clear()
        main._next_id = 1
    yield
    with main._lock:
        main._tasks.clear()
        main._next_id = 1


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def create(client, title="Write tests", status=None):
    payload = {"title": title}
    if status is not None:
        payload["status"] = status
    resp = client.post("/api/tasks", json=payload)
    assert resp.status_code == 201
    return resp.json()


# --- create ---

def test_create_task_defaults_to_todo(client):
    resp = client.post("/api/tasks", json={"title": "Buy milk"})
    assert resp.status_code == 201
    assert resp.json() == {"id": 1, "title": "Buy milk", "status": "todo"}


def test_create_task_with_explicit_status(client):
    resp = client.post("/api/tasks", json={"title": "Ship it", "status": "done"})
    assert resp.status_code == 201
    assert resp.json()["status"] == "done"


def test_create_assigns_incrementing_ids(client):
    first = create(client, "one")
    second = create(client, "two")
    assert second["id"] == first["id"] + 1


def test_create_rejects_blank_title(client):
    resp = client.post("/api/tasks", json={"title": "   "})
    assert resp.status_code == 422


def test_create_rejects_empty_title(client):
    resp = client.post("/api/tasks", json={"title": ""})
    assert resp.status_code == 422


def test_create_rejects_missing_title(client):
    resp = client.post("/api/tasks", json={})
    assert resp.status_code == 422


def test_create_rejects_invalid_status(client):
    resp = client.post("/api/tasks", json={"title": "x", "status": "archived"})
    assert resp.status_code == 422


def test_create_rejects_title_over_max_length(client):
    resp = client.post("/api/tasks", json={"title": "a" * 201})
    assert resp.status_code == 422


# --- list ---

def test_list_empty(client):
    resp = client.get("/api/tasks")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_returns_created_tasks(client):
    a = create(client, "a")
    b = create(client, "b", status="in_progress")
    resp = client.get("/api/tasks")
    assert resp.status_code == 200
    assert resp.json() == [a, b]


# --- status update (PATCH) ---

def test_patch_updates_status(client):
    task = create(client)
    resp = client.patch(f"/api/tasks/{task['id']}", json={"status": "in_progress"})
    assert resp.status_code == 200
    assert resp.json() == {"id": task["id"], "title": task["title"], "status": "in_progress"}
    # Persisted in the store, not just echoed back.
    listed = client.get("/api/tasks").json()
    assert listed[0]["status"] == "in_progress"


def test_patch_can_update_title(client):
    task = create(client, "old")
    resp = client.patch(
        f"/api/tasks/{task['id']}", json={"status": "todo", "title": "new"}
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "new"


def test_patch_requires_status(client):
    task = create(client)
    resp = client.patch(f"/api/tasks/{task['id']}", json={"title": "only title"})
    assert resp.status_code == 422


def test_patch_rejects_invalid_status(client):
    task = create(client)
    resp = client.patch(f"/api/tasks/{task['id']}", json={"status": "bogus"})
    assert resp.status_code == 422
    # Store unchanged after rejected update.
    assert client.get("/api/tasks").json()[0]["status"] == "todo"


def test_patch_rejects_blank_title(client):
    task = create(client)
    resp = client.patch(
        f"/api/tasks/{task['id']}", json={"status": "todo", "title": "   "}
    )
    assert resp.status_code == 422


def test_patch_unknown_id_returns_404(client):
    resp = client.patch("/api/tasks/999", json={"status": "done"})
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Task not found"}


# --- delete ---

def test_delete_removes_task(client):
    task = create(client)
    resp = client.delete(f"/api/tasks/{task['id']}")
    assert resp.status_code == 204
    assert resp.content == b""
    assert client.get("/api/tasks").json() == []


def test_delete_unknown_id_returns_404(client):
    resp = client.delete("/api/tasks/999")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Task not found"}


def test_delete_twice_returns_404_second_time(client):
    task = create(client)
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 204
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 404


def test_deleted_id_is_not_reused(client):
    first = create(client, "first")
    client.delete(f"/api/tasks/{first['id']}")
    second = create(client, "second")
    assert second["id"] != first["id"]
