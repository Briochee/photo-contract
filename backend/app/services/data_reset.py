"""Controlled removal of local business records and generated files."""

import os
import shutil
import uuid
from pathlib import Path

from sqlalchemy import delete, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.app.config import DATA_DIR, DEFAULT_OUTPUT_DIR
from backend.app.logging_config import clear_log_history
from backend.app.models import (
    AdditionalExpense,
    AppSetting,
    Booking,
    BookingAmendment,
    BookingLineItem,
    Client,
    GeneratedDocument,
    Invoice,
    InvoiceLineItem,
    MasterAgreement,
    Payment,
    PhotographerProfile,
)

_RECORD_MODELS = (
    GeneratedDocument,
    Payment,
    InvoiceLineItem,
    Invoice,
    BookingAmendment,
    AdditionalExpense,
    BookingLineItem,
    Booking,
    MasterAgreement,
    Client,
    PhotographerProfile,
    AppSetting,
)


class DataResetError(RuntimeError):
    """Raised when a reset cannot safely complete or restore staged local files."""


def clear_application_data(session: Session) -> dict[str, bool]:
    """Clear business records, generated documents, legacy inputs, and log history.

    The configured database remains initialized, while reference sequences are retained so
    identifiers from deleted records are never reused. Files are first moved into a private
    quarantine directory, allowing restoration if the database transaction fails.
    """
    data_root = DATA_DIR.resolve()
    home = Path.home().resolve()
    if data_root == Path(data_root.anchor) or home == data_root or home.is_relative_to(data_root):
        raise DataResetError("The configured data directory is too broad for a safe reset")

    document_root = DEFAULT_OUTPUT_DIR
    try:
        if document_root.is_symlink() or document_root.resolve().parent != data_root:
            raise DataResetError("The configured document library is outside the local data folder")
    except OSError as exc:
        raise DataResetError("The configured document library could not be inspected") from exc
    if document_root.name != "documents":
        raise DataResetError("The configured document library path is not recognized")

    files_cleared = _remove_previous_quarantines(data_root)
    quarantine = data_root / f".contract-studio-clear-{uuid.uuid4().hex}"
    staged: list[tuple[Path, Path]] = []
    document_root_created = False
    try:
        quarantine.mkdir()
        _stage_path(document_root, quarantine / "documents", staged)
        document_root.mkdir(parents=True, exist_ok=True)
        document_root_created = True

        legacy_root = quarantine / "legacy"
        legacy_paths = [
            *data_root.glob("references.sqlite3*"),
            *data_root.glob("BK-*.json"),
            *data_root.glob("BK-*.pdf"),
            *data_root.glob(".prior-data-*"),
            *data_root.glob("contract-studio-backup-*"),
        ]
        for legacy_path in legacy_paths:
            if legacy_path == quarantine or quarantine in legacy_path.parents:
                continue
            _stage_path(legacy_path, legacy_root / legacy_path.name, staged)

        session.execute(text("PRAGMA secure_delete=ON"))
        session.execute(text("PRAGMA defer_foreign_keys=ON"))
        for model in _RECORD_MODELS:
            session.execute(delete(model))
        session.commit()
    except Exception as exc:
        session.rollback()
        try:
            _restore_staged_files(staged, document_root, remove_document_root=document_root_created)
            _remove_path(quarantine)
        except OSError as restore_error:
            raise DataResetError(
                "The reset failed and staged files could not all be restored"
            ) from restore_error
        if isinstance(exc, DataResetError):
            raise
        raise DataResetError("The application data could not be cleared") from exc

    try:
        _remove_path(quarantine)
    except OSError:
        files_cleared = False

    database_compacted = _compact_database(session.get_bind())
    logs_cleared = clear_log_history()
    return {
        "local_files_cleared": files_cleared,
        "database_compacted": database_compacted,
        "logs_cleared": logs_cleared,
        "reference_sequences_retained": True,
    }


def _stage_path(source: Path, destination: Path, staged: list[tuple[Path, Path]]) -> None:
    """Move an application-owned path to quarantine and record its restoration target."""
    if not source.exists() and not source.is_symlink():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(source, destination)
    staged.append((source, destination))


def _restore_staged_files(
    staged: list[tuple[Path, Path]], document_root: Path, *, remove_document_root: bool
) -> None:
    """Restore quarantined files in reverse order after a failed database transaction."""
    if remove_document_root and document_root.exists():
        _remove_path(document_root)
    for original, staged_path in reversed(staged):
        if staged_path.exists() or staged_path.is_symlink():
            original.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged_path, original)


def _remove_previous_quarantines(data_root: Path) -> bool:
    """Remove reset staging folders left behind by interrupted filesystem cleanup."""
    complete = True
    for path in data_root.glob(".contract-studio-clear-*"):
        try:
            _remove_path(path)
        except OSError:
            complete = False
    return complete


def _remove_path(path: Path) -> None:
    """Remove a file, directory, or symlink without following symlink targets."""
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def _compact_database(engine: Engine) -> bool:
    """Checkpoint and vacuum SQLite so deleted record pages are not left in the live store."""
    database_path = engine.url.database
    if engine.dialect.name != "sqlite" or not database_path or database_path == ":memory:":
        return True
    if not Path(database_path).is_file():
        return True
    try:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            checkpoint = connection.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)").one()
            if checkpoint[0]:
                return False
            connection.exec_driver_sql("VACUUM")
            checkpoint = connection.exec_driver_sql("PRAGMA wal_checkpoint(TRUNCATE)").one()
            return checkpoint[0] == 0
    except Exception:
        return False
