"""Controlled master-agreement records based on the supplied legal source."""

import json
from datetime import UTC, date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.database import get_session
from backend.app.logging_config import activity
from backend.app.models import Booking, Client, MasterAgreement, PhotographerProfile
from backend.app.schemas import AgreementFinalizeInput, AgreementInput
from backend.app.services.agreement_signing import (
    MAX_SIGNED_AGREEMENT_BYTES,
    store_signed_agreement,
)
from backend.app.services.agreement_templates import get_agreement_template
from backend.app.services.domain import client_values, profile_values, snapshot
from backend.app.services.references import allocate_reference

router = APIRouter(prefix="/api/agreements", tags=["agreements"])


def agreement_text() -> str:
    """Return the active agreement text, preserving the custom or bundled source as written."""
    try:
        return get_agreement_template()["content"]
    except OSError as exc:
        raise HTTPException(503, "The local agreement template is unavailable") from exc
    except ValueError as exc:
        raise HTTPException(500, str(exc)) from exc


@router.get("")
def list_agreements(session: Session = Depends(get_session)):
    rows = session.scalars(
        select(MasterAgreement).order_by(MasterAgreement.created_at.desc())
    ).all()
    return [_agreement_values(row) for row in rows]


@router.post("", status_code=201)
def create_agreement(payload: AgreementInput, session: Session = Depends(get_session)):
    client = session.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(404, "Client not found")
    try:
        template = get_agreement_template()
    except OSError as exc:
        raise HTTPException(503, "The local agreement template is unavailable") from exc
    except ValueError as exc:
        raise HTTPException(500, str(exc)) from exc
    legal = template["content"]
    digest = template["content_hash"]
    profile = session.scalar(select(PhotographerProfile).order_by(PhotographerProfile.id).limit(1))
    if profile is None:
        raise HTTPException(422, "Complete the photographer profile before creating an agreement")
    try:
        session.rollback()
        with session.begin():
            agreement = MasterAgreement(
                agreement_ref=allocate_reference(session, "agreement", date.today().year),
                client_id=client.id,
                photographer_profile_id=profile.id,
                effective_date=None,
                status="draft",
                template_version=template["template_version"],
                legal_text_hash=digest,
                legal_text_snapshot=legal,
                source_snapshot_json=snapshot(
                    {
                        "client": client_values(client),
                        "photographer": profile_values(profile),
                    }
                )[0],
            )
            session.add(agreement)
            session.flush()
        return _agreement_values(agreement)
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.get("/{agreement_id}")
def get_agreement(agreement_id: int, session: Session = Depends(get_session)):
    agreement = session.get(MasterAgreement, agreement_id)
    if agreement is None:
        raise HTTPException(404, "Agreement not found")
    return _agreement_values(agreement)


@router.delete("/{agreement_id}", status_code=204)
def delete_agreement(agreement_id: int, session: Session = Depends(get_session)) -> Response:
    """Delete an agreement record only when no booking depends on its terms."""
    agreement = session.get(MasterAgreement, agreement_id)
    if agreement is None:
        raise HTTPException(404, "Agreement not found")
    booking_id = session.scalar(
        select(Booking.id).where(Booking.agreement_id == agreement_id).limit(1)
    )
    if booking_id is not None:
        raise HTTPException(409, "This agreement is linked to a booking and cannot be deleted")
    try:
        session.delete(agreement)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            409, "This agreement is linked to another record and cannot be deleted"
        ) from exc
    return Response(status_code=204)


@router.post("/{agreement_id}/finalize")
def finalize_agreement(
    agreement_id: int,
    payload: AgreementFinalizeInput,
    session: Session = Depends(get_session),
):
    agreement = session.get(MasterAgreement, agreement_id)
    if agreement is None:
        raise HTTPException(404, "Agreement not found")
    if agreement.status == "finalized":
        raise HTTPException(409, "This contract has already been finalized")
    if agreement.status not in {"draft", "pending"}:
        raise HTTPException(409, "This contract cannot be finalized from its current status")
    agreement.status = "finalized"
    agreement.effective_date = payload.signed_date
    agreement.accepted_at = datetime.combine(payload.signed_date, time.min, tzinfo=UTC)
    agreement.acceptance_reference = payload.evidence_reference.strip()
    source = json.loads(agreement.source_snapshot_json)
    source["effective_date"] = payload.signed_date.isoformat()
    source["acceptance_reference"] = agreement.acceptance_reference
    agreement.source_snapshot_json, _ = snapshot(source)
    session.commit()
    return _agreement_values(agreement)


@router.post("/{agreement_id}/signed-copy")
async def upload_signed_copy(
    agreement_id: int,
    request: Request,
    signed_date: date,
    filename: str = Query(min_length=1, max_length=255),
    session: Session = Depends(get_session),
):
    """Upload a PDF body, save it as a new library version, and finalize the agreement."""
    agreement = session.get(MasterAgreement, agreement_id)
    if agreement is None:
        raise HTTPException(404, "Agreement not found")
    if agreement.status == "finalized":
        raise HTTPException(409, "This contract has already been finalized")
    if agreement.status not in {"draft", "pending"}:
        raise HTTPException(409, "This contract cannot be finalized from its current status")

    content_type = request.headers.get("content-type", "").split(";", maxsplit=1)[0].strip()
    if content_type.casefold() != "application/pdf":
        raise HTTPException(415, "Upload the signed contract as a PDF")
    try:
        content_length = int(request.headers.get("content-length", "0"))
    except ValueError as exc:
        raise HTTPException(400, "The PDF upload size is invalid") from exc
    if content_length > MAX_SIGNED_AGREEMENT_BYTES:
        raise HTTPException(413, "The signed PDF must be smaller than 25 MB")

    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > MAX_SIGNED_AGREEMENT_BYTES:
            raise HTTPException(413, "The signed PDF must be smaller than 25 MB")
        content.extend(chunk)
    try:
        agreement, _document = store_signed_agreement(
            session, agreement_id, signed_date, filename, bytes(content)
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (OSError, SQLAlchemyError) as exc:
        activity.error(
            "agreement_signed_upload_failed id=%d error=%s", agreement_id, type(exc).__name__
        )
        raise HTTPException(
            503, "The signed PDF could not be saved to the local document library"
        ) from exc
    return _agreement_values(agreement)


def _agreement_values(agreement: MasterAgreement) -> dict[str, object]:
    return {
        "id": agreement.id,
        "agreement_ref": agreement.agreement_ref,
        "client_id": agreement.client_id,
        "client_name": agreement.client.legal_name,
        "photographer_profile_id": agreement.photographer_profile_id,
        "effective_date": agreement.effective_date.isoformat()
        if agreement.effective_date
        else None,
        "status": "finalized" if agreement.status == "accepted" else agreement.status,
        "template_version": agreement.template_version,
        "legal_text_hash": agreement.legal_text_hash,
        "accepted_at": agreement.accepted_at.isoformat() if agreement.accepted_at else None,
        "acceptance_reference": agreement.acceptance_reference,
    }
