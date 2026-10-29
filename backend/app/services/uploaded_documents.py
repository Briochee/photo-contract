"""Store validated user reference files in the local document library."""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.config import DATA_DIR, DEFAULT_OUTPUT_DIR
from backend.app.logging_config import activity
from backend.app.models import GeneratedDocument

MAX_DOCUMENT_UPLOAD_BYTES = 25 * 1024 * 1024
UPLOAD_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}
_FILE_SIGNATURES = {
    "application/pdf": (b"%PDF-",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}


def safe_upload_name(filename: str) -> str:
    """Return a display-only basename with path separators and control characters removed."""
    basename = filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1]
    cleaned = "".join(character for character in basename if character.isprintable()).strip()
    if not cleaned or len(cleaned) > 255:
        raise ValueError("Choose a file with a valid name under 256 characters")
    return cleaned


def validate_upload_content(filename: str, media_type: str, content: bytes) -> None:
    """Validate the allowed extension, declared media type, size, and file signature."""
    expected_type = UPLOAD_MEDIA_TYPES.get(Path(filename).suffix.casefold())
    if expected_type is None or media_type != expected_type:
        raise ValueError("Upload a PDF, JPG, or PNG file with a matching file type")
    if not content:
        raise ValueError("The selected file is empty")
    if len(content) > MAX_DOCUMENT_UPLOAD_BYTES:
        raise ValueError("The selected file must be 25 MB or smaller")
    if not any(content.startswith(signature) for signature in _FILE_SIGNATURES[expected_type]):
        raise ValueError("The file contents do not match its file type")


def store_uploaded_document(
    session: Session,
    filename: str,
    media_type: str,
    content: bytes,
) -> GeneratedDocument:
    """Atomically store one validated file and its metadata without linking a client record."""
    display_name = safe_upload_name(filename)
    validate_upload_content(display_name, media_type, content)

    root = DEFAULT_OUTPUT_DIR
    data_root = DATA_DIR.resolve()
    if root.is_symlink() or root.resolve().parent != data_root:
        raise ValueError("The configured document library is outside the local data folder")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root = root.resolve()

    identifier = uuid4().hex
    extension = Path(display_name).suffix.casefold()
    destination = root / f"uploaded-{identifier}{extension}"
    temporary_path: Path | None = None
    destination_created = False
    session.rollback()
    try:
        with tempfile.NamedTemporaryFile(
            dir=root, prefix=".upload-", suffix=".tmp", delete=False
        ) as temporary:
            if hasattr(os, "fchmod"):
                os.fchmod(temporary.fileno(), 0o600)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)

        os.link(temporary_path, destination)
        destination_created = True
        temporary_path.unlink()
        temporary_path = None

        with session.begin():
            document = GeneratedDocument(
                document_type="uploaded_file",
                client_id=None,
                reference=f"FILE-{identifier}",
                version=1,
                status="final",
                file_path=str(destination),
                content_hash=hashlib.sha256(content).hexdigest(),
                template_version="user-upload-v1",
                source_snapshot_json=json.dumps(
                    {
                        "original_filename": display_name,
                        "media_type": media_type,
                        "size_bytes": len(content),
                    },
                    separators=(",", ":"),
                ),
            )
            session.add(document)
            session.flush()
        return document
    except Exception:
        session.rollback()
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                activity.warning("uploaded_document_cleanup_failed target=temporary")
        if destination_created:
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                activity.warning("uploaded_document_cleanup_failed target=stored")
        raise
