"""Consistent local backup packaging for the SQLite stores and generated documents."""

import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from backend.app.config import DATA_DIR, DATABASE_PATH


def create_backup() -> Path:
    """Build a ZIP with SQLite online backups and copied local records/documents."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix="contract-studio-backup-", dir=DATA_DIR))
    archive_path = temporary_root / "contract-studio-backup.zip"
    staging = temporary_root / "staging"
    staging.mkdir()
    try:
        for source in DATA_DIR.rglob("*"):
            if source.is_symlink() or not source.is_file() or temporary_root in source.parents:
                continue
            relative = source.relative_to(DATA_DIR)
            if source.name.endswith(("-wal", "-shm")):
                continue
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.suffix == ".sqlite3":
                _sqlite_backup(source, destination)
            else:
                shutil.copy2(source, destination)
        if DATABASE_PATH.exists() and not (staging / DATABASE_PATH.name).exists():
            _sqlite_backup(DATABASE_PATH, staging / DATABASE_PATH.name)
        manifest = {
            "application": "Contract Studio",
            "created_at": datetime.now(UTC).isoformat(),
            "database_file": DATABASE_PATH.name,
            "includes": [
                "SQLite databases",
                "settings",
                "master agreement template",
                "legacy records",
                "generated documents",
            ],
        }
        (staging / "backup_manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for source in sorted(staging.rglob("*")):
                if source.is_file():
                    archive.write(source, source.relative_to(staging).as_posix())
        return archive_path
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise


def remove_backup(path: Path) -> None:
    """Delete a temporary archive and its private staging directory after download."""
    shutil.rmtree(path.parent, ignore_errors=True)


def _sqlite_backup(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(f"{source.resolve().as_uri()}?mode=ro", uri=True, timeout=15) as source_db:
        with sqlite3.connect(destination) as destination_db:
            source_db.backup(destination_db)
            destination_db.commit()
