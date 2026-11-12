# Task Tracker API

A small REST API for tracking tasks. Built with FastAPI, SQLAlchemy 2.x, Alembic and Pydantic v2. Python 3.10.

## Install

```bash
cd /home/ubuntu/app
python3.10 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Configure the database

The app reads `DATABASE_URL` from the environment. When it is unset, it uses `sqlite:///./tasks.db` in the current directory.

```bash
# SQLite (default)
export DATABASE_URL="sqlite:///./tasks.db"

# PostgreSQL (psycopg 3 driver; use the postgresql+psycopg:// scheme)
export DATABASE_URL="postgresql+psycopg://user:password@host:5432/dbname"
```

Migrations and the app both read `DATABASE_URL` the same way. The Postgres driver is installed, but only SQLite has been tested.

## Run migrations

```bash
.venv/bin/alembic upgrade head
```

Tables are created only by migrations. The app never calls `create_all`.

## Run the server

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 3000
```

Interactive API docs are at http://127.0.0.1:3000/docs.

## Run the tests

```bash
.venv/bin/pytest
```

## Endpoints

| Method | Path | Description | Success |
|--------|------|-------------|---------|
| POST | `/tasks` | Create a task | 201 |
| GET | `/tasks` | List tasks; optional `?status=todo\|doing\|done` filter | 200 |
| GET | `/tasks/{id}` | Get one task | 200 |
| PATCH | `/tasks/{id}` | Partially update `title`, `description`, `status` | 200 |
| DELETE | `/tasks/{id}` | Delete a task | 204 |

A missing task returns 404. An invalid body or an invalid `status` value returns 422.

A task has `id`, `title` (1-200 characters, required), `description` (optional), `status` (`todo`, `doing` or `done`; default `todo`), `created_at`, and `updated_at`. Timestamps are UTC and set by the server. `updated_at` changes on every PATCH.

## Create a migration

After changing `app/models.py`, write a new revision by hand, or generate one and review it:

```bash
.venv/bin/alembic revision --autogenerate -m "describe the change"
.venv/bin/alembic upgrade head
```
