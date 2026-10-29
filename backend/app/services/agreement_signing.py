"""Finalize agreements from an uploaded signed PDF while preserving document versions."""

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, date, datetime, time
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.config import DATA_DIR, DEFAULT_OUTPUT_DIR
from backend.app.logging_config import activity
from backend.app.models import GeneratedDocument, MasterAgreement
from backend.app.services.domain import snapshot

MAX_SIGNED_AGREEMENT_BYTES = 25 * 1024 * 1024
_SAFE_AGREEMENT_REFERENCE = re.compile(r"^AGR-\d{4}-\d{3,}$")


def store_signed_agreement(
    session: Session,
    agreement_id: int,
    signed_date: date,
    upload_filename: str,
    content: bytes,
) -> tuple[MasterAgreement, GeneratedDocument]:
    """Finalize a pending agreement and atomically save its signed PDF in the document library.

    The PDF is stored under a generated filename, never a user-supplied path. The returned
    document is a new immutable library version; an existing draft PDF is left untouched.
    """
    if not upload_filename.casefold().endswith(".pdf") or not content.startswith(b"%PDF-"):
        raise ValueError("Upload a valid signed PDF file")
    if not content or len(content) > MAX_SIGNED_AGREEMENT_BYTES:
        raise ValueError("The signed PDF must be smaller than 25 MB")

    session.rollback()
    temporary_path: Path | None = None
    destination: Path | None = None
    destination_created = False
    try:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        agreement = session.get(MasterAgreement, agreement_id)
        if agreement is None:
            raise LookupError("Agreement not found")
        if agreement.status == "finalized":
            raise ValueError("This contract has already been finalized")
        if agreement.status not in {"draft", "pending"}:
            raise ValueError("This contract cannot be finalized from its current status")
        if not _SAFE_AGREEMENT_REFERENCE.fullmatch(agreement.agreement_ref):
            raise ValueError("The contract reference cannot be used as a safe filename")

        root = DEFAULT_OUTPUT_DIR
        data_root = DATA_DIR.resolve()
        if root.is_symlink() or root.resolve().parent != data_root:
            raise ValueError("The configured document library is outside the local data folder")
        root.mkdir(parents=True, exist_ok=True)
        root = root.resolve()

        previous_version = (
            session.scalar(
                select(func.max(GeneratedDocument.version)).where(
                    GeneratedDocument.document_type == "agreement",
                    GeneratedDocument.reference == agreement.agreement_ref,
                )
            )
            or 0
        )
        version = previous_version + 1
        filename = f"{agreement.agreement_ref}_Signed-Copy_v{version}.pdf"
        destination = root / filename
        if destination.parent != root:
            raise ValueError("The signed PDF path is outside the document library")

        with tempfile.NamedTemporaryFile(dir=root, suffix=".tmp", delete=False) as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.link(temporary_path, destination)
        destination_created = True
        temporary_path.unlink()

        agreement.status = "finalized"
        agreement.effective_date = signed_date
        agreement.accepted_at = datetime.combine(signed_date, time.min, tzinfo=UTC)
        agreement.acceptance_reference = f"Uploaded signed PDF: {filename}"[:200]
        source = json.loads(agreement.source_snapshot_json)
        source["effective_date"] = signed_date.isoformat()
        source["acceptance_reference"] = agreement.acceptance_reference
        agreement.source_snapshot_json, _ = snapshot(source)

        document = GeneratedDocument(
            document_type="agreement",
            client_id=agreement.client_id,
            reference=agreement.agreement_ref,
            version=version,
            status="final",
            file_path=str(destination),
            content_hash=hashlib.sha256(content).hexdigest(),
            template_version="signed-pdf-upload",
            source_snapshot_json=agreement.source_snapshot_json,
        )
        session.add(document)
        session.commit()
    except Exception:
        session.rollback()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        if destination_created and destination is not None:
            destination.unlink(missing_ok=True)
        raise

    session.refresh(agreement)
    session.refresh(document)
    activity.info(
        "agreement_finalized reference=%s method=uploaded_pdf version=%d",
        agreement.agreement_ref,
        document.version,
    )
    return agreement, document
