from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Task, TaskStatus, utcnow
from app.schemas import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])

# SQLite INTEGER primary keys are signed 64-bit; larger ids cannot exist and would overflow.
TaskId = Annotated[int, Path(ge=1, le=2**63 - 1)]


def _get_task_or_404(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> Task:
    now = utcnow()
    task = Task(
        title=payload.title,
        description=payload.description,
        status=payload.status.value,
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("", response_model=list[TaskRead])
def list_tasks(
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> list[Task]:
    stmt = select(Task).order_by(Task.id)
    if status_filter is not None:
        stmt = stmt.where(Task.status == status_filter.value)
    return list(db.scalars(stmt).all())


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: TaskId, db: Session = Depends(get_db)) -> Task:
    return _get_task_or_404(db, task_id)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(task_id: TaskId, payload: TaskUpdate, db: Session = Depends(get_db)) -> Task:
    task = _get_task_or_404(db, task_id)
    changes = payload.model_dump(mode="json", exclude_unset=True)
    for field, value in changes.items():
        setattr(task, field, value)
    # Every PATCH counts as an update, even one that changes nothing.
    task.updated_at = utcnow()
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: TaskId, db: Session = Depends(get_db)) -> Response:
    task = _get_task_or_404(db, task_id)
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
