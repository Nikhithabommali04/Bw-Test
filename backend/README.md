# TaskBoard Backend

FastAPI service with an in-memory task store. Data is lost when the server stops.

## Setup

```bash
cd backend
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

## Run

Run from the `backend` directory:

```bash
uvicorn main:app --host 0.0.0.0 --port 3000
```

## API

| Method | Path               | Body                                  | Response                  |
|--------|--------------------|---------------------------------------|---------------------------|
| GET    | /api/tasks         | —                                     | 200, list of tasks        |
| POST   | /api/tasks         | `{"title": str, "status"?: str}`      | 201, created task         |
| PATCH  | /api/tasks/{id}    | `{"status": str, "title"?: str}`      | 200, updated task / 404   |
| DELETE | /api/tasks/{id}    | —                                     | 204 / 404                 |

- `title`: non-empty, max 200 characters.
- `status`: one of `todo`, `in_progress`, `done` (default `todo`).
- Invalid input returns 422.

## Frontend

If `../frontend/dist` exists at startup, it is served at `/` with `index.html` as the fallback for SPA routes. `/api/*` is never served the fallback.
