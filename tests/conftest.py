from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def database_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Give each test its own SQLite file. Set before the app is imported, so ./tasks.db is never used."""
    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    return url


@pytest.fixture()
def db_engine(database_url: str) -> Iterator:
    # Build the schema with the real migrations, as the README requires (the app never calls create_all).
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    command.upgrade(config, "head")

    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    yield engine
    engine.dispose()


@pytest.fixture()
def client(db_engine) -> Iterator[TestClient]:
    # Imported here, not at module level, so DATABASE_URL is already set when app.db builds its engine.
    from app.db import get_db
    from app.main import app

    TestingSessionLocal = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)

    def override_get_db() -> Iterator:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
