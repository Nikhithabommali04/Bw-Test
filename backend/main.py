import os
import sqlite3
from contextlib import asynccontextmanager, closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Iterator

from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator, model_validator

DEFAULT_DB_PATH = "/home/ubuntu/app/data/notes.db"
FRONTEND_DIST = Path("/home/ubuntu/app/frontend/dist")

TITLE_MAX = 200
BODY_MAX = 100000
URL_MAX = 2000
TAG_MAX = 50

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    tag TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""

NOTE_COLUMNS = "id, title, body, created_at, updated_at"
LINK_COLUMNS = "id, url, title, tag, created_at"


class NoteCreate(BaseModel):
    title: str = Field("", max_length=TITLE_MAX)
    body: str = Field("", max_length=BODY_MAX)


class NoteUpdate(BaseModel):
    title: str | None = Field(None, max_length=TITLE_MAX)
    body: str | None = Field(None, max_length=BODY_MAX)

    @model_validator(mode="after")
    def reject_explicit_null(self):
        # Omitted fields are left unchanged; explicit null is not a valid value.
        for name in ("title", "body"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} must be a string, not null")
        return self


class NoteOut(BaseModel):
    id: int
    title: str
    body: str
    created_at: str
    updated_at: str


class LinkCreate(BaseModel):
    url: str = Field(..., max_length=URL_MAX)
    title: str = Field("", max_length=TITLE_MAX)
    tag: str = Field("", max_length=TAG_MAX)

    @field_validator("url")
    @classmethod
    def require_http_url(cls, value: str) -> str:
        # Only web links are stored; anything else (javascript:, file:, ...) is rejected.
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("url must be an http or https URL")
        return value


class LinkOut(BaseModel):
    id: int
    url: str
    title: str
    tag: str
    created_at: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = Path(os.environ.get("NOTES_DB_PATH", DEFAULT_DB_PATH))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(_connect(str(db_path))) as conn, conn:
        conn.executescript(SCHEMA)
    app.state.db_path = str(db_path)
    yield


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    conn = _connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()


DB = Annotated[sqlite3.Connection, Depends(get_db)]


def _get_note(db: sqlite3.Connection, note_id: int) -> dict:
    row = db.execute(
        f"SELECT {NOTE_COLUMNS} FROM notes WHERE id = ?", (note_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return dict(row)


def _get_link(db: sqlite3.Connection, link_id: int) -> dict:
    row = db.execute(
        f"SELECT {LINK_COLUMNS} FROM links WHERE id = ?", (link_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Link not found")
    return dict(row)


app = FastAPI(title="NoteNest", lifespan=lifespan)


@app.get("/api/notes", response_model=list[NoteOut])
def list_notes(db: DB):
    rows = db.execute(
        f"SELECT {NOTE_COLUMNS} FROM notes ORDER BY updated_at DESC, id DESC"
    ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/notes", response_model=NoteOut, status_code=201)
def create_note(payload: NoteCreate, db: DB):
    now = _now()
    with db:
        cur = db.execute(
            "INSERT INTO notes (title, body, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (payload.title, payload.body, now, now),
        )
    return _get_note(db, cur.lastrowid)


@app.put("/api/notes/{note_id}", response_model=NoteOut)
def update_note(note_id: int, payload: NoteUpdate, db: DB):
    current = _get_note(db, note_id)
    title = payload.title if "title" in payload.model_fields_set else current["title"]
    body = payload.body if "body" in payload.model_fields_set else current["body"]
    with db:
        db.execute(
            "UPDATE notes SET title = ?, body = ?, updated_at = ? WHERE id = ?",
            (title, body, _now(), note_id),
        )
    return _get_note(db, note_id)


@app.delete("/api/notes/{note_id}", status_code=204)
def delete_note(note_id: int, db: DB) -> Response:
    with db:
        cur = db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return Response(status_code=204)


@app.get("/api/links", response_model=list[LinkOut])
def list_links(db: DB, tag: str | None = None):
    # Omitted tag returns every link; a given tag matches exactly.
    if tag is None:
        rows = db.execute(
            f"SELECT {LINK_COLUMNS} FROM links ORDER BY tag, id"
        ).fetchall()
    else:
        rows = db.execute(
            f"SELECT {LINK_COLUMNS} FROM links WHERE tag = ? ORDER BY tag, id", (tag,)
        ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/links", response_model=LinkOut, status_code=201)
def create_link(payload: LinkCreate, db: DB):
    with db:
        cur = db.execute(
            "INSERT INTO links (url, title, tag, created_at) VALUES (?, ?, ?, ?)",
            (payload.url, payload.title, payload.tag, _now()),
        )
    return _get_link(db, cur.lastrowid)


@app.delete("/api/links/{link_id}", status_code=204)
def delete_link(link_id: int, db: DB) -> Response:
    with db:
        cur = db.execute("DELETE FROM links WHERE id = ?", (link_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Link not found")
    return Response(status_code=204)


# Static frontend. Decided once at startup: if a built dist exists, serve it;
# otherwise GET / returns a small JSON message. Routes above are registered
# first, so /api paths never reach the SPA fallback below.
_index_file = FRONTEND_DIST / "index.html"
if FRONTEND_DIST.is_dir() and _index_file.is_file():
    _dist_root = FRONTEND_DIST.resolve()

    @app.get("/", include_in_schema=False)
    def spa_root():
        return FileResponse(_index_file)

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = (_dist_root / full_path).resolve()
        if candidate.is_file() and candidate.is_relative_to(_dist_root):
            return FileResponse(candidate)
        return FileResponse(_index_file)

else:

    @app.get("/", include_in_schema=False)
    def root():
        return {"message": "NoteNest API is running. Frontend build not found."}
