"""Restore an application backup into a new or empty data directory."""

import argparse
import shutil
import zipfile
from pathlib import Path, PurePosixPath

MAX_UNCOMPRESSED_BYTES = 5_000_000_000


def restore(archive_path: Path, destination: Path) -> None:
    """Safely extract a verified archive without replacing a nonempty data directory."""
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Restore destination must be a new or empty directory")
    created = not destination.exists()
    destination.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.infolist()
            if sum(item.file_size for item in members) > MAX_UNCOMPRESSED_BYTES:
                raise ValueError("Backup is larger than the supported restore limit")
            names = [item.filename for item in members]
            if "studio.sqlite3" not in names or "backup_manifest.json" not in names:
                raise ValueError("Archive does not contain a supported studio backup")
            if archive.testzip() is not None:
                raise ValueError("Backup archive integrity check failed")
            root = destination.resolve()
            for member in members:
                relative = PurePosixPath(member.filename)
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or "" in relative.parts
                ):
                    raise ValueError("Backup contains an unsafe file path")
                mode = member.external_attr >> 16
                if mode and (mode & 0o170000) == 0o120000:
                    raise ValueError("Backup contains a symbolic link")
                if member.is_dir() or member.filename == "backup_manifest.json":
                    continue
                output = (root / Path(*relative.parts)).resolve()
                if root not in output.parents:
                    raise ValueError(
                        "Backup file resolves outside the restore directory"
                    )
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, output.open("xb") as target:
                    shutil.copyfileobj(source, target)
    except Exception:
        if created:
            shutil.rmtree(destination, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Path to the local backup ZIP")
    parser.add_argument(
        "destination", type=Path, help="New or empty directory for restored data"
    )
    args = parser.parse_args()
    try:
        restore(
            args.archive.expanduser().resolve(), args.destination.expanduser().resolve()
        )
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))
    print(f"Restored local studio data to {args.destination.expanduser().resolve()}")
    print(
        "Set PHOTO_STUDIO_DATA_DIR to this directory before starting the application."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
