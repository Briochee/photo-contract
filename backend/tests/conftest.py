"""Isolated SQLite API fixtures for local workflow tests."""

import pytest
from backend.app.database import get_session
from backend.app.main import app
from backend.app.models import Base
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(engine, "connect", lambda dbapi, _record: dbapi.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    def override_session():
        session = sessions()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()
