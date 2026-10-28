"""SQLAlchemy engine and per-request session dependency."""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from backend.app.config import DATA_DIR, DATABASE_PATH, DATABASE_URL

DATA_DIR.mkdir(parents=True, exist_ok=True)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15},
    pool_pre_ping=True,
)


@event.listens_for(Engine, "connect")
def enable_sqlite_integrity(dbapi_connection: object, _connection_record: object) -> None:
    """Enable SQLite foreign keys and a bounded lock wait on every connection."""
    if DATABASE_PATH.suffix != ".sqlite3":
        return
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.execute("PRAGMA journal_mode=WAL")
    finally:
        cursor.close()


SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False, autoflush=False)


def get_session() -> Generator[Session, None, None]:
    """Yield one SQLAlchemy session for the request and always close it."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
