"""Document preview, versioned generation, local uploads, and safe downloads."""

import json
import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.config import DEFAULT_OUTPUT_DIR
from backend.app.database import get_session
from backend.app.logging_config import activity
from backend.app.models import GeneratedDocument
from backend.app.schemas import DocumentRequest
from backend.app.services.documents import document_context, generate_document, render_pdf
from backend.app.services.uploaded_documents import (
    MAX_DOCUMENT_UPLOAD_BYTES,
    UPLOAD_MEDIA_TYPES,
    safe_upload_name,
    store_uploaded_document,
    validate_upload_content,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
def list_documents(session: Session = Depends(get_session)):
    rows = session.scalars(
        select(GeneratedDocument).order_by(GeneratedDocument.created_at.desc())
    ).all()
    return [_document_values(row) for row in rows]


@router.post("/preview")
def preview_document(payload: DocumentRequest, session: Session = Depends(get_session)):
    try:
        _, _, context, _ = document_context(session, payload.document_type, payload.entity_id)
        content = render_pdf(payload.document_type, context)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (RuntimeError, OSError) as exc:
        raise HTTPException(503, str(exc)) from exc
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'inline; filename="document-preview.pdf"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/generate", status_code=201)
def generate_document_route(payload: DocumentRequest, session: Session = Depends(get_session)):
    try:
        document = generate_document(session, payload.document_type, payload.entity_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, RuntimeError, OSError) as exc:
        session.rollback()
        raise HTTPException(503, str(exc)) from exc
    return _document_values(document)


@router.post("/upload", status_code=201)
async def upload_document_route(
    request: Request,
    filename: str = Query(min_length=1, max_length=255),
    session: Session = Depends(get_session),
):
    """Store one small PDF or image as a private library file without linking a business record."""
    try:
        display_name = safe_upload_name(filename)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    media_type = UPLOAD_MEDIA_TYPES.get(Path(display_name).suffix.casefold())
    if media_type is None:
        raise HTTPException(415, "Upload a PDF, JPG, or PNG file")
    declared_type = request.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    if declared_type and declared_type not in {media_type, "application/octet-stream"}:
        raise HTTPException(415, "The selected file type does not match its extension")

    try:
        content_length = int(request.headers.get("content-length", "0"))
    except ValueError as exc:
        raise HTTPException(400, "The upload size is invalid") from exc
    if content_length < 0:
        raise HTTPException(400, "The upload size is invalid")
    if content_length > MAX_DOCUMENT_UPLOAD_BYTES:
        raise HTTPException(413, "The selected file must be 25 MB or smaller")

    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > MAX_DOCUMENT_UPLOAD_BYTES:
            raise HTTPException(413, "The selected file must be 25 MB or smaller")
        content.extend(chunk)
    if not content:
        raise HTTPException(400, "The selected file is empty")
    try:
        validate_upload_content(display_name, media_type, bytes(content))
    except ValueError as exc:
        raise HTTPException(415, str(exc)) from exc

    try:
        document = store_uploaded_document(session, display_name, media_type, bytes(content))
    except (OSError, SQLAlchemyError, ValueError) as exc:
        session.rollback()
        activity.error("document_upload_failed error=%s", type(exc).__name__)
        raise HTTPException(
            503, "The file could not be saved to the local document library"
        ) from exc
    activity.info("document_uploaded id=%d", document.id)
    return _document_values(document)


@router.get("/{document_id}")
def get_document(document_id: int, session: Session = Depends(get_session)):
    document = session.get(GeneratedDocument, document_id)
    if document is None:
        raise HTTPException(404, "Document not found")
    return _document_values(document)


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, session: Session = Depends(get_session)) -> Response:
    """Remove one library record and its PDF while keeping the database and file consistent."""
    document = session.get(GeneratedDocument, document_id)
    if document is None:
        raise HTTPException(404, "Document not found")
    document_type = document.document_type

    root = DEFAULT_OUTPUT_DIR.resolve()
    path = Path(document.file_path).resolve()
    if path.parent != root:
        raise HTTPException(409, "The document file is outside the configured library")

    tombstone = root / f".delete-{uuid4().hex}.tmp"
    moved_file = False
    try:
        if path.exists():
            if not path.is_file():
                raise HTTPException(409, "The document file is not a regular file")
            os.replace(path, tombstone)
            moved_file = True
        session.delete(document)
        session.commit()
    except HTTPException:
        raise
    except Exception as exc:
        session.rollback()
        if moved_file:
            try:
                os.replace(tombstone, path)
            except OSError:
                activity.error("document_delete_restore_failed id=%d", document_id)
        raise HTTPException(503, "The document could not be deleted") from exc

    if moved_file:
        try:
            tombstone.unlink(missing_ok=True)
        except OSError:
            activity.warning("document_delete_cleanup_failed id=%d", document_id)
    activity.info("document_deleted id=%d type=%s", document_id, document_type)
    return Response(status_code=204)


@router.get("/{document_id}/preview")
def preview_saved_document(document_id: int, session: Session = Depends(get_session)):
    document = session.get(GeneratedDocument, document_id)
    if document is None:
        raise HTTPException(404, "Document not found")
    path = _safe_document_path(document)
    return FileResponse(
        path,
        media_type=_document_media_type(document),
        filename=_document_filename(document),
        content_disposition_type="inline",
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )


@router.get("/{document_id}/download")
def download_document(document_id: int, session: Session = Depends(get_session)):
    document = session.get(GeneratedDocument, document_id)
    if document is None:
        raise HTTPException(404, "Document not found")
    path = _safe_document_path(document)
    return FileResponse(
        path,
        media_type=_document_media_type(document),
        filename=_document_filename(document),
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )


def _document_values(document: GeneratedDocument) -> dict[str, object]:
    metadata = _upload_metadata(document)
    return {
        "id": document.id,
        "document_type": document.document_type,
        "name": metadata.get("original_filename", Path(document.file_path).name),
        "client_id": document.client_id,
        "client_name": document.client.legal_name if document.client else None,
        "booking_id": document.booking_id,
        "booking_reference": document.booking.booking_ref if document.booking else None,
        "invoice_id": document.invoice_id,
        "invoice_reference": document.invoice.invoice_ref if document.invoice else None,
        "reference": document.reference,
        "version": document.version,
        "status": document.status,
        "created_at": document.created_at.isoformat(),
        "content_hash": document.content_hash,
        "template_version": document.template_version,
        "media_type": metadata.get("media_type"),
        "size_bytes": metadata.get("size_bytes"),
    }


def _upload_metadata(document: GeneratedDocument) -> dict[str, object]:
    """Read user-upload metadata while tolerating malformed snapshots in old local records."""
    if document.document_type != "uploaded_file":
        return {}
    try:
        metadata = json.loads(document.source_snapshot_json)
    except (TypeError, ValueError):
        return {}
    return metadata if isinstance(metadata, dict) else {}


def _document_filename(document: GeneratedDocument) -> str:
    """Use the sanitized original name for uploads and the generated basename for PDFs."""
    name = _upload_metadata(document).get("original_filename")
    if isinstance(name, str):
        try:
            return safe_upload_name(name)
        except ValueError:
            pass
    return Path(document.file_path).name


def _document_media_type(document: GeneratedDocument) -> str:
    """Return only a known safe browser media type for uploaded files."""
    if document.document_type != "uploaded_file":
        return "application/pdf"
    media_type = _upload_metadata(document).get("media_type")
    if media_type not in set(UPLOAD_MEDIA_TYPES.values()):
        raise HTTPException(415, "The stored file type cannot be previewed or downloaded")
    return str(media_type)


def _safe_document_path(document: GeneratedDocument) -> Path:
    """Resolve a library path and reject missing files or paths outside the configured directory."""
    root = DEFAULT_OUTPUT_DIR.resolve()
    path = Path(document.file_path).resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(404, "The document file is missing from the local library")
    return path
