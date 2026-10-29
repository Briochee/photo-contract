"""Apply local migrations and run FastAPI as an Electron-managed child process."""

import argparse
import hashlib
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = (
    Path(sys._MEIPASS)
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parents[1]
)
sys.path.insert(0, str(ROOT))


def import_existing_data(source_dir: Path, destination_dir: Path) -> int:
    """Copy prior local records once, snapshotting SQLite without copying live WAL files."""
    source_dir = source_dir.expanduser().resolve()
    destination_dir = destination_dir.expanduser().resolve()
    source_database = source_dir / "studio.sqlite3"
    destination_database = destination_dir / "studio.sqlite3"
    if (
        source_dir == destination_dir
        or not source_database.is_file()
        or destination_database.exists()
    ):
        return 0

    stage_dir = Path(tempfile.mkdtemp(prefix=".prior-data-", dir=destination_dir))
    published: list[Path] = []
    imported_count = 0
    try:
        for source_path in source_dir.rglob("*"):
            relative_path = source_path.relative_to(source_dir)
            if (
                source_path.is_symlink()
                or not source_path.is_file()
                or source_path.name == ".DS_Store"
                or "logs" in relative_path.parts
                or source_path.name.endswith(("-wal", "-shm"))
            ):
                continue

            staged_path = stage_dir / relative_path
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            if source_path.suffix == ".sqlite3":
                _backup_sqlite_file(source_path, staged_path)
            else:
                shutil.copy2(source_path, staged_path)

        staged_database = stage_dir / "studio.sqlite3"
        if not staged_database.is_file():
            return 0

        staged_files = sorted(
            (path for path in stage_dir.rglob("*") if path.is_file()),
            key=lambda path: path.relative_to(stage_dir).as_posix() == "studio.sqlite3",
        )
        for staged_path in staged_files:
            destination_path = destination_dir / staged_path.relative_to(stage_dir)
            if destination_path.exists() and not _same_file_contents(
                staged_path, destination_path
            ):
                raise FileExistsError(
                    "The new data folder contains a different file at an import path."
                )

        for staged_path in staged_files:
            destination_path = destination_dir / staged_path.relative_to(stage_dir)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            if destination_path.exists():
                continue
            os.replace(staged_path, destination_path)
            published.append(destination_path)
            imported_count += 1
    except Exception as exc:
        for destination_path in reversed(published):
            destination_path.unlink(missing_ok=True)
        from backend.app.logging_config import activity

        activity.error("previous_local_data_import_failed error=%s", type(exc).__name__)
        raise RuntimeError(
            "Could not import the previous local data. Its original files were left intact."
        ) from exc
    finally:
        shutil.rmtree(stage_dir, ignore_errors=True)

    if imported_count:
        from backend.app.logging_config import activity

        activity.info("previous_local_data_imported files=%d", imported_count)
    return imported_count


def _backup_sqlite_file(source_path: Path, destination_path: Path) -> None:
    """Create a consistent SQLite snapshot that includes committed WAL content."""
    source_connection = sqlite3.connect(
        f"{source_path.as_uri()}?mode=ro", uri=True, timeout=30
    )
    destination_connection = sqlite3.connect(destination_path)
    try:
        source_connection.backup(destination_connection)
        integrity = destination_connection.execute("PRAGMA integrity_check").fetchone()
        if integrity != ("ok",):
            raise sqlite3.DatabaseError(
                "The existing SQLite database failed integrity check."
            )
    finally:
        destination_connection.close()
        source_connection.close()


def _same_file_contents(first: Path, second: Path) -> bool:
    """Compare files without exposing their contents in logs or diagnostics."""
    if not second.is_file() or first.stat().st_size != second.stat().st_size:
        return False

    def digest(path: Path) -> str:
        hasher = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    return digest(first) == digest(second)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    from alembic import command
    from alembic.config import Config

    from backend.app.config import DATA_DIR, DEFAULT_OUTPUT_DIR

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    legacy_data_dir = os.environ.get("PHOTO_STUDIO_LEGACY_DATA_DIR", "").strip()
    if legacy_data_dir:
        import_existing_data(Path(legacy_data_dir), DATA_DIR)
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    migration_config = Config(str(ROOT / "backend" / "alembic.ini"))
    command.upgrade(migration_config, "head")

    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=args.host,
        port=args.port,
        log_level="info",
        access_log=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
