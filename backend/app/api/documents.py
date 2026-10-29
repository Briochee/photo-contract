"""Document preview, versioned generation, metadata, and safe PDF downloads."""

import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.config import DEFAULT_OUTPUT_DIR
from backend.app.database import get_session
from backend.app.logging_config import activity
from backend.app.models import GeneratedDocument
from backend.app.schemas import DocumentRequest
from backend.app.services.documents import document_context, generate_document, render_pdf

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
    root = DEFAULT_OUTPUT_DIR.resolve()
    path = Path(document.file_path).resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(404, "The generated file is missing from the local document library")
    return FileResponse(
        path, media_type="application/pdf", filename=path.name, content_disposition_type="inline"
    )


@router.get("/{document_id}/download")
def download_document(document_id: int, session: Session = Depends(get_session)):
    document = session.get(GeneratedDocument, document_id)
    if document is None:
        raise HTTPException(404, "Document not found")
    root = DEFAULT_OUTPUT_DIR.resolve()
    path = Path(document.file_path).resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(404, "The generated file is missing from the local document library")
    return FileResponse(path, media_type="application/pdf", filename=path.name)


def _document_values(document: GeneratedDocument) -> dict[str, object]:
    return {
        "id": document.id,
        "document_type": document.document_type,
        "name": Path(document.file_path).name,
        "client_id": document.client_id,
        "client_name": document.client.legal_name,
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
    }
