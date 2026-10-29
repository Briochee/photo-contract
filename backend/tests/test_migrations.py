"""Protect the squashed schema baseline and its pre-squash SQLite upgrade path."""

import re
import sqlite3
from datetime import date

from alembic.config import Config
from alembic.script import ScriptDirectory
from backend.app.migrations import CURRENT_REVISION, upgrade_database
from backend.app.models import (
    Booking,
    Client,
    GeneratedDocument,
    MasterAgreement,
    PhotographerProfile,
)
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session


def _database_url(path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_single_baseline_creates_latest_schema(tmp_path) -> None:
    """Create a new database from the one checked-in current schema revision."""
    database_path = tmp_path / "studio.sqlite3"
    database_url = _database_url(database_path)

    upgrade_database(database_url, backup_directory=tmp_path / "backups")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert inspector.get_table_names()
        profile_columns = {
            column["name"]: column for column in inspector.get_columns("photographer_profiles")
        }
        assert profile_columns["business_name"]["nullable"]
        assert profile_columns["default_photography_rate_cents"]["nullable"]
        agreement_columns = {
            column["name"]: column for column in inspector.get_columns("master_agreements")
        }
        assert agreement_columns["effective_date"]["nullable"]
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
                "0002_booking_lifecycle"
            )
    finally:
        engine.dispose()

    script = ScriptDirectory.from_config(Config("backend/alembic.ini"))
    revisions = list(script.walk_revisions())
    assert script.get_heads() == ["0002_booking_lifecycle"]
    assert {revision.revision for revision in revisions} == {
        CURRENT_REVISION,
        "0002_booking_lifecycle",
    }


def test_legacy_0003_database_migrates_without_losing_records(tmp_path) -> None:
    """Reconcile an older schema and align saved booking documents with their lifecycle."""
    database_path = tmp_path / "studio.sqlite3"
    database_url = _database_url(database_path)
    upgrade_database(database_url)

    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            client = Client(legal_name="Example Client")
            photographer = PhotographerProfile(legal_name="Example Photographer")
            session.add_all([client, photographer])
            session.flush()
            agreement = MasterAgreement(
                agreement_ref="AGR-2026-001",
                client_id=client.id,
                photographer_profile_id=photographer.id,
                effective_date=date(2026, 10, 29),
                status="draft",
                template_version="1.0.0",
                legal_text_hash="a" * 64,
                legal_text_snapshot="Agreement text",
                source_snapshot_json="{}",
            )
            session.add(agreement)
            session.flush()
            pending_booking = Booking(
                booking_ref="BK-2026-001",
                client_id=client.id,
                event_name="Portrait session",
                event_date=date(2026, 11, 20),
                status="draft",
            )
            accepted_booking = Booking(
                booking_ref="BK-2026-002",
                client_id=client.id,
                event_name="Wedding",
                event_date=date(2026, 11, 21),
                status="accepted",
            )
            session.add_all([pending_booking, accepted_booking])
            session.flush()
            session.add(
                GeneratedDocument(
                    document_type="agreement",
                    client_id=client.id,
                    reference=agreement.agreement_ref,
                    version=1,
                    status="draft",
                    file_path="agreement.pdf",
                    content_hash="b" * 64,
                    template_version="1.0.0",
                    source_snapshot_json="{}",
                )
            )
            session.add(
                GeneratedDocument(
                    document_type="booking_confirmation",
                    client_id=client.id,
                    booking_id=pending_booking.id,
                    reference=pending_booking.booking_ref,
                    version=1,
                    status="draft",
                    file_path="booking-confirmation.pdf",
                    content_hash="c" * 64,
                    template_version="1.0.0",
                    source_snapshot_json="{}",
                )
            )
            agreement_id = agreement.id
            pending_booking_id = pending_booking.id
            accepted_booking_id = accepted_booking.id
            session.commit()
    finally:
        engine.dispose()

    _make_effective_date_required(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE alembic_version SET version_num = ?",
            ("0003_agreement_lifecycle",),
        )

    backup_directory = tmp_path / "backups"
    upgrade_database(database_url, backup_directory=backup_directory)

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            agreement = connection.execute(
                text("SELECT effective_date, status FROM master_agreements WHERE id = :id"),
                {"id": agreement_id},
            ).one()
            document_status = connection.scalar(
                text("SELECT status FROM generated_documents WHERE reference = 'AGR-2026-001'")
            )
            booking_states = connection.execute(
                text("SELECT id, status FROM bookings ORDER BY id")
            ).all()
            booking_document_status = connection.scalar(
                text("SELECT status FROM generated_documents WHERE reference = 'BK-2026-001'")
            )
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
        assert agreement.effective_date is None
        assert agreement.status == "pending"
        assert document_status == "pending"
        assert booking_states == [
            (pending_booking_id, "pending"),
            (accepted_booking_id, "finalized"),
        ]
        assert booking_document_status == "pending"
        assert revision == "0002_booking_lifecycle"
    finally:
        engine.dispose()

    backups = list(backup_directory.glob("studio.pre-migration.*.sqlite3"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("SELECT COUNT(*) FROM master_agreements").fetchone() == (1,)


def _make_effective_date_required(database_path) -> None:
    """Rebuild only the legacy agreement table to reproduce revision 0003 constraints."""
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys=OFF")
        schema = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'master_agreements'"
        ).fetchone()[0]
        legacy_schema = re.sub(
            r"effective_date DATE,",
            "effective_date DATE NOT NULL,",
            schema,
            count=1,
        )
        assert legacy_schema != schema
        legacy_table_schema = legacy_schema.replace(
            "CREATE TABLE master_agreements",
            "CREATE TABLE master_agreements_legacy",
            1,
        )
        connection.execute(legacy_table_schema)
        columns = [row[1] for row in connection.execute("PRAGMA table_info(master_agreements)")]
        column_list = ", ".join(f'"{column}"' for column in columns)
        connection.execute(
            f"INSERT INTO master_agreements_legacy ({column_list}) "
            f"SELECT {column_list} FROM master_agreements"
        )
        connection.execute("DROP TABLE master_agreements")
        connection.execute("ALTER TABLE master_agreements_legacy RENAME TO master_agreements")
        connection.commit()
    finally:
        connection.close()
