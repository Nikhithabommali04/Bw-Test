from datetime import datetime, timezone
from pathlib import Path

import pytest

TASKS = "/tasks"


def _create(client, **fields) -> dict:
    response = client.post(TASKS, json={"title": "Write tests", **fields})
    assert response.status_code == 201, response.text
    return response.json()


def _parse(value: str) -> datetime:
    # Python 3.10's fromisoformat does not accept a trailing "Z".
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# --- test database isolation ---


def test_suite_uses_temporary_database(database_url: str, tmp_path: Path) -> None:
    assert database_url == f"sqlite:///{tmp_path / 'test.db'}"
    assert "tasks.db" not in database_url


# --- POST /tasks ---


def test_create_task_returns_201_with_task_fields(client) -> None:
    response = client.post(TASKS, json={"title": "Buy milk", "description": "2 litres"})

    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["title"] == "Buy milk"
    assert body["description"] == "2 litres"
    assert body["status"] == "todo"
    assert "created_at" in body
    assert "updated_at" in body


def test_create_task_defaults_status_to_todo(client) -> None:
    body = client.post(TASKS, json={"title": "No status given"}).json()

    assert body["status"] == "todo"


@pytest.mark.parametrize("status", ["todo", "doing", "done"])
def test_create_task_accepts_each_valid_status(client, status: str) -> None:
    body = _create(client, status=status)

    assert body["status"] == status


def test_create_task_description_is_optional(client) -> None:
    body = _create(client)

    assert body["description"] is None


def test_create_task_sets_equal_utc_timestamps(client) -> None:
    body = _create(client)

    created = _parse(body["created_at"])
    updated = _parse(body["updated_at"])
    assert created.tzinfo is not None
    assert created.utcoffset().total_seconds() == 0
    assert created == updated


def test_create_task_strips_surrounding_whitespace_from_title(client) -> None:
    body = _create(client, title="   padded title   ")

    assert body["title"] == "padded title"


def test_create_task_title_is_required(client) -> None:
    response = client.post(TASKS, json={"description": "no title"})

    assert response.status_code == 422


@pytest.mark.parametrize("title", [None, "", "   ", "\t\n"])
def test_create_task_rejects_null_empty_or_blank_title(client, title) -> None:
    response = client.post(TASKS, json={"title": title})

    assert response.status_code == 422


def test_create_task_accepts_title_of_exactly_200_characters(client) -> None:
    body = _create(client, title="a" * 200)

    assert len(body["title"]) == 200


def test_create_task_rejects_title_of_201_characters(client) -> None:
    response = client.post(TASKS, json={"title": "a" * 201})

    assert response.status_code == 422


def test_create_task_invalid_status_returns_422(client) -> None:
    response = client.post(TASKS, json={"title": "Bad status", "status": "archived"})

    assert response.status_code == 422


def test_create_task_rejects_null_status(client) -> None:
    response = client.post(TASKS, json={"title": "Null status", "status": None})

    assert response.status_code == 422


def test_create_task_rejected_request_stores_nothing(client) -> None:
    client.post(TASKS, json={"title": "   "})

    assert client.get(TASKS).json() == []


# --- GET /tasks ---


def test_list_tasks_empty_when_no_tasks(client) -> None:
    response = client.get(TASKS)

    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_returns_all_tasks_in_id_order(client) -> None:
    first = _create(client, title="first")
    second = _create(client, title="second", status="done")
    third = _create(client, title="third", status="doing")

    response = client.get(TASKS)

    assert response.status_code == 200
    assert [task["id"] for task in response.json()] == [first["id"], second["id"], third["id"]]


@pytest.mark.parametrize("status", ["todo", "doing", "done"])
def test_list_tasks_filters_by_status(client, status: str) -> None:
    _create(client, title="todo one", status="todo")
    _create(client, title="doing one", status="doing")
    _create(client, title="done one", status="done")

    response = client.get(TASKS, params={"status": status})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == status


def test_list_tasks_filter_with_no_matches_returns_empty_list(client) -> None:
    _create(client, status="todo")

    response = client.get(TASKS, params={"status": "done"})

    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_invalid_status_filter_returns_422(client) -> None:
    response = client.get(TASKS, params={"status": "archived"})

    assert response.status_code == 422


# --- GET /tasks/{id} ---


def test_get_task_returns_200_with_the_task(client) -> None:
    created = _create(client, title="Fetch me", description="details")

    response = client.get(f"{TASKS}/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_task_missing_id_returns_404(client) -> None:
    response = client.get(f"{TASKS}/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_get_task_non_integer_id_returns_422(client) -> None:
    response = client.get(f"{TASKS}/not-a-number")

    assert response.status_code == 422


# --- PATCH /tasks/{id} ---


def test_patch_task_changes_only_the_fields_sent(client) -> None:
    created = _create(client, title="Original", description="keep me", status="todo")

    response = client.patch(f"{TASKS}/{created['id']}", json={"title": "Renamed"})

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Renamed"
    assert body["description"] == "keep me"
    assert body["status"] == "todo"


def test_patch_task_can_change_only_status(client) -> None:
    created = _create(client, title="Status change", status="todo")

    response = client.patch(f"{TASKS}/{created['id']}", json={"status": "done"})

    assert response.status_code == 200
    assert response.json()["status"] == "done"
    assert response.json()["title"] == "Status change"


def test_patch_task_can_clear_description_with_null(client) -> None:
    created = _create(client, description="to be cleared")

    response = client.patch(f"{TASKS}/{created['id']}", json={"description": None})

    assert response.status_code == 200
    assert response.json()["description"] is None


def test_patch_task_change_is_persisted(client) -> None:
    created = _create(client, title="Before")

    client.patch(f"{TASKS}/{created['id']}", json={"title": "After", "status": "doing"})
    fetched = client.get(f"{TASKS}/{created['id']}").json()

    assert fetched["title"] == "After"
    assert fetched["status"] == "doing"


def test_patch_task_updates_updated_at_and_keeps_created_at(client) -> None:
    created = _create(client, title="Timestamps")

    response = client.patch(f"{TASKS}/{created['id']}", json={"status": "doing"})

    assert response.status_code == 200
    body = response.json()
    assert body["created_at"] == created["created_at"]
    assert _parse(body["updated_at"]) > _parse(created["updated_at"])


def test_patch_task_with_empty_body_still_bumps_updated_at(client) -> None:
    created = _create(client, title="No-op patch")

    response = client.patch(f"{TASKS}/{created['id']}", json={})

    assert response.status_code == 200
    assert response.json()["title"] == "No-op patch"
    assert _parse(response.json()["updated_at"]) > _parse(created["updated_at"])


def test_patch_task_missing_id_returns_404(client) -> None:
    response = client.patch(f"{TASKS}/999999", json={"title": "Nobody"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


@pytest.mark.parametrize(
    "payload",
    [
        {"title": None},
        {"title": ""},
        {"title": "   "},
        {"title": "a" * 201},
        {"status": None},
        {"status": "archived"},
    ],
)
def test_patch_task_invalid_body_returns_422(client, payload: dict) -> None:
    created = _create(client, title="Stable", status="todo")

    response = client.patch(f"{TASKS}/{created['id']}", json=payload)

    assert response.status_code == 422
    assert client.get(f"{TASKS}/{created['id']}").json()["title"] == "Stable"


# --- DELETE /tasks/{id} ---


def test_delete_task_returns_204_with_no_body(client) -> None:
    created = _create(client)

    response = client.delete(f"{TASKS}/{created['id']}")

    assert response.status_code == 204
    assert response.content == b""


def test_delete_task_then_get_returns_404(client) -> None:
    created = _create(client)

    client.delete(f"{TASKS}/{created['id']}")
    response = client.get(f"{TASKS}/{created['id']}")

    assert response.status_code == 404


def test_delete_task_removes_it_from_list_and_keeps_others(client) -> None:
    keep = _create(client, title="keep")
    gone = _create(client, title="gone")

    client.delete(f"{TASKS}/{gone['id']}")

    assert client.get(TASKS).json() == [keep]


def test_delete_task_twice_returns_404_the_second_time(client) -> None:
    created = _create(client)

    assert client.delete(f"{TASKS}/{created['id']}").status_code == 204
    response = client.delete(f"{TASKS}/{created['id']}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_delete_task_missing_id_returns_404(client) -> None:
    response = client.delete(f"{TASKS}/999999")

    assert response.status_code == 404
