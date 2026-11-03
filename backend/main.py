import os
import threading
from enum import Enum
from typing import Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

TITLE_MAX_LENGTH = 200
FRONTEND_DIST = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
)


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


def _reject_blank(value: Optional[str]) -> Optional[str]:
    if value is not None and not value.strip():
        raise ValueError("title must not be blank")
    return value


class Task(BaseModel):
    id: int
    title: str
    status: TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH)
    status: TaskStatus = TaskStatus.todo

    @field_validator("title")
    @classmethod
    def no_blank_title(cls, value: str) -> str:
        return _reject_blank(value)


class TaskUpdate(BaseModel):
    status: TaskStatus
    title: Optional[str] = Field(default=None, min_length=1, max_length=TITLE_MAX_LENGTH)

    @field_validator("title")
    @classmethod
    def no_blank_title(cls, value: Optional[str]) -> Optional[str]:
        return _reject_blank(value)


# In-memory store. Data is lost when the process exits.
_tasks: dict[int, Task] = {}
_next_id = 1
_lock = threading.Lock()

app = FastAPI(title="TaskBoard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/tasks", response_model=list[Task])
def list_tasks() -> list[Task]:
    with _lock:
        return list(_tasks.values())


@app.post("/api/tasks", response_model=Task, status_code=201)
def create_task(body: TaskCreate) -> Task:
    global _next_id
    with _lock:
        task = Task(id=_next_id, title=body.title, status=body.status)
        _tasks[task.id] = task
        _next_id += 1
        return task


@app.patch("/api/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, body: TaskUpdate) -> Task:
    with _lock:
        task = _tasks.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        task.status = body.status
        if body.title is not None:
            task.title = body.title
        return task


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int) -> Response:
    with _lock:
        if _tasks.pop(task_id, None) is None:
            raise HTTPException(status_code=404, detail="Task not found")
    return Response(status_code=204)


class SPAStaticFiles(StaticFiles):
    """Serve the built frontend, falling back to index.html for SPA routes.

    Unknown /api/* paths are never rewritten to index.html.
    """

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and path.split("/")[0] != "api":
                return await super().get_response("index.html", scope)
            raise


if os.path.isdir(FRONTEND_DIST):
    app.mount("/", SPAStaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
