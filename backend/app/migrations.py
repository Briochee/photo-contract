"""Run the consolidated Alembic baseline while preserving known local databases."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, make_url, text

from backend.app.config import DATABASE_URL, PROJECT_ROOT
from backend.app.logging_config import activity

CURRENT_REVISION = "0001_current_schema"
LEGACY_REVISIONS = frozenset(
    {
        "0001_initial",
        "0002_optional_profile_defaults",
        "0003_agreement_lifecycle",
        "0004_agreement_effective_date_nullable",
    }
)


def upgrade_database(
    database_url: str | None = None,
    config_path: Path | None = None,
    backup_directory: Path | None = None,
) -> None:
    """Upgrade SQLite to the single current baseline, snapshotting known older schemas.

    Existing databases stamped by the former migration chain are backed up, then
    unstamped so the consolidated migration can reconcile their schema and data.
    Unknown revisions are rejected without changing the database.
    """
    url = database_url or DATABASE_URL
    parsed_url = make_url(url)
    if parsed_url.get_backend_name() != "sqlite":
        raise ValueError("Contract Studio migrations require a SQLite database.")

    alembic_config_path = config_path or PROJECT_ROOT / "backend" / "alembic.ini"
    available_revisions = {
        script.revision
        for script in ScriptDirectory.from_config(Config(str(alembic_config_path))).walk_revisions()
    }
    database_path = _database_path(parsed_url)
    revisions, tables = _database_state(url, database_path)
    if revisions and revisions.issubset(available_revisions):
        _run_alembic(url, alembic_config_path)
        return

    if revisions and not revisions.issubset(LEGACY_REVISIONS):
        unknown = ", ".join(sorted(revisions - LEGACY_REVISIONS))
        raise RuntimeError(
            "The local database has an unrecognized migration revision "
            f"({unknown or ', '.join(sorted(revisions))}); no migration changes were made."
        )

    if database_path is not None and database_path.is_file() and (revisions or tables):
        backup_root = backup_directory or database_path.parent / "backups"
        backup_path = _backup_database(database_path, backup_root)
        activity.info(
            "database_migration_backup_created file=%s",
            backup_path.name,
        )

    if revisions:
        _clear_revision_table(url)
        activity.info("legacy_database_revision_rebased revision_count=%d", len(revisions))

    _run_alembic(url, alembic_config_path)


def _database_path(url) -> Path | None:
    """Return the local SQLite file path, excluding in-memory databases."""
    database = url.database
    if not database or database == ":memory:":
        return None
    return Path(database).expanduser().resolve()


def _database_state(url: str, database_path: Path | None) -> tuple[set[str], set[str]]:
    """Read Alembic revisions and table names without exposing persisted records."""
    if database_path is not None and not database_path.is_file():
        return set(), set()

    engine = create_engine(url, connect_args={"timeout": 15})
    try:
        with engine.connect() as connection:
            tables = set(inspect(connection).get_table_names())
            if "alembic_version" not in tables:
                return set(), tables
            rows = connection.execute(text("SELECT version_num FROM alembic_version"))
            return {row[0] for row in rows}, tables - {"alembic_version"}
    finally:
        engine.dispose()


def _backup_database(database_path: Path, backup_directory: Path) -> Path:
    """Create and integrity-check a consistent SQLite backup before schema changes."""
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = backup_directory / f"studio.pre-migration.{timestamp}.sqlite3"
    try:
        backup_directory.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(f"{database_path.as_uri()}?mode=ro", uri=True, timeout=30) as source:
            with sqlite3.connect(backup_path) as destination:
                source.backup(destination)
                result = destination.execute("PRAGMA integrity_check").fetchone()
                if result != ("ok",):
                    raise sqlite3.DatabaseError("SQLite integrity check failed for backup.")
    except (OSError, sqlite3.Error) as error:
        try:
            backup_path.unlink(missing_ok=True)
        except OSError:
            activity.warning("failed_partial_migration_backup_cleanup")
        activity.error("database_migration_backup_failed error=%s", type(error).__name__)
        raise RuntimeError(
            "A safe database backup could not be created, so migration was stopped."
        ) from error
    return backup_path


def _clear_revision_table(url: str) -> None:
    """Remove only a recognized historical Alembic marker before baseline upgrade."""
    engine = create_engine(url, connect_args={"timeout": 15})
    try:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM alembic_version"))
    finally:
        engine.dispose()


def _run_alembic(url: str, config_path: Path | None) -> None:
    """Apply all revisions in the configured migration directory."""
    migration_config = Config(str(config_path or PROJECT_ROOT / "backend" / "alembic.ini"))
    migration_config.attributes["database_url"] = url
    try:
        command.upgrade(migration_config, "head")
    except Exception as error:
        activity.error("database_migration_failed error=%s", type(error).__name__)
        raise
