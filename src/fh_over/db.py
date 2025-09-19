"""Database configuration and session management."""

from pathlib import Path
from typing import Generator

from sqlmodel import SQLModel, create_engine, Session
from fh_over.config import config


def get_database_url() -> str:
    """Get database URL from config or environment."""
    if config.database_url:
        return config.database_url
    
    # Default to SQLite
    db_path = Path(config.paths.sqlite_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def create_db_engine():
    """Create database engine."""
    database_url = get_database_url()
    return create_engine(database_url, echo=False)


def create_tables():
    """Create all database tables."""
    engine = create_db_engine()
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Get database session."""
    engine = create_db_engine()
    with Session(engine) as session:
        yield session
