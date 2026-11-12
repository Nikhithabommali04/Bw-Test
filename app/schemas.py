from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import TaskStatus

TITLE_MAX_LENGTH = 200
DESCRIPTION_MAX_LENGTH = 5000


def _clean_title(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("title must not be blank")
    return value


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    status: TaskStatus = TaskStatus.todo

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str) -> str:
        return _clean_title(value)


class TaskUpdate(BaseModel):
    """Partial update: only the fields present in the request body are changed."""

    title: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    status: TaskStatus | None = None

    @field_validator("title")
    @classmethod
    def _title_not_null_or_blank(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("title cannot be null")
        return _clean_title(value)

    @field_validator("status")
    @classmethod
    def _status_not_null(cls, value: TaskStatus | None) -> TaskStatus:
        if value is None:
            raise ValueError("status cannot be null")
        return value


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def _as_utc(cls, value: datetime) -> datetime:
        # SQLite returns naive datetimes; the server always writes UTC, so treat naive values as UTC.
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
