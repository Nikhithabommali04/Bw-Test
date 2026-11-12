import os

DEFAULT_DATABASE_URL = "sqlite:///./tasks.db"


def get_database_url() -> str:
    """Return DATABASE_URL from the environment, or the SQLite default when unset or empty."""
    return os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL
