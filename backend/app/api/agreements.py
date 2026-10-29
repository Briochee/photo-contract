"""Controlled master-agreement records based on the supplied legal source."""

import hashlib
from datetime import UTC, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.config import LEGAL_SOURCE, TEMPLATE_VERSION
from backend.app.database import get_session
from backend.app.models import Booking, Client, MasterAgreement, PhotographerProfile
from backend.app.schemas import AgreementAcceptInput, AgreementInput
from backend.app.services.domain import client_values, profile_values, snapshot
from backend.app.services.references import allocate_reference

router = APIRouter(prefix="/api/agreements", tags=["agreements"])


def agreement_text() -> str:
    """Read the authoritative agreement section, excluding the booking sample and checklist."""
    try:
        source = LEGAL_SOURCE.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(503, "The local legal reference file is unavailable") from exc
    if "\n---\n" not in source:
        raise HTTPException(500, "The legal reference is missing its agreement boundary")
    text = source.split("\n---\n", maxsplit=1)[0].rstrip() + "\n"
    required_sections = [f"## {number}." for number in range(1, 17)]
    if any(section not in text for section in required_sections):
        raise HTTPException(500, "The legal reference is missing a required agreement section")
    return text


@router.get("")
def list_agreements(session: Session = Depends(get_session)):
    rows = session.scalars(
        select(MasterAgreement).order_by(MasterAgreement.effective_date.desc())
    ).all()
    return [_agreement_values(row) for row in rows]


@router.post("", status_code=201)
def create_agreement(payload: AgreementInput, session: Session = Depends(get_session)):
    client = session.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(404, "Client not found")
    if payload.accepted and (
        payload.accepted_date is None or not payload.acceptance_reference.strip()
    ):
        raise HTTPException(422, "Record the written acceptance date and its reference")
    if (
        payload.accepted
        and payload.accepted_date
        and payload.accepted_date < payload.effective_date
    ):
        raise HTTPException(422, "Acceptance date cannot precede the agreement effective date")
    legal = agreement_text()
    digest = hashlib.sha256(legal.encode("utf-8")).hexdigest()
    profile = session.scalar(select(PhotographerProfile).order_by(PhotographerProfile.id).limit(1))
    if profile is None:
        raise HTTPException(422, "Complete the photographer profile before creating an agreement")
    try:
        session.rollback()
        with session.begin():
            agreement = MasterAgreement(
                agreement_ref=allocate_reference(session, "agreement", payload.effective_date.year),
                client_id=client.id,
                photographer_profile_id=profile.id,
                effective_date=payload.effective_date,
                status="accepted" if payload.accepted else "draft",
                template_version=TEMPLATE_VERSION,
                legal_text_hash=digest,
                legal_text_snapshot=legal,
                source_snapshot_json=snapshot(
                    {
                        "client": client_values(client),
                        "photographer": profile_values(profile),
                        "effective_date": payload.effective_date.isoformat(),
                    }
                )[0],
                accepted_at=(
                    datetime.combine(payload.accepted_date, time.min, tzinfo=UTC)
                    if payload.accepted_date
                    else None
                ),
                acceptance_reference=payload.acceptance_reference if payload.accepted else "",
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


@router.post("/{agreement_id}/accept")
def accept_agreement(
    agreement_id: int,
    payload: AgreementAcceptInput,
    session: Session = Depends(get_session),
):
    agreement = session.get(MasterAgreement, agreement_id)
    if agreement is None:
        raise HTTPException(404, "Agreement not found")
    if agreement.status != "draft":
        raise HTTPException(409, "Only draft agreements can be marked accepted")
    if payload.accepted_date < agreement.effective_date:
        raise HTTPException(422, "Acceptance date cannot precede the agreement effective date")
    agreement.status = "accepted"
    agreement.accepted_at = datetime.combine(payload.accepted_date, time.min, tzinfo=UTC)
    agreement.acceptance_reference = payload.acceptance_reference.strip()
    session.commit()
    return _agreement_values(agreement)


def _agreement_values(agreement: MasterAgreement) -> dict[str, object]:
    return {
        "id": agreement.id,
        "agreement_ref": agreement.agreement_ref,
        "client_id": agreement.client_id,
        "client_name": agreement.client.legal_name,
        "photographer_profile_id": agreement.photographer_profile_id,
        "effective_date": agreement.effective_date.isoformat(),
        "status": agreement.status,
        "template_version": agreement.template_version,
        "legal_text_hash": agreement.legal_text_hash,
        "accepted_at": agreement.accepted_at.isoformat() if agreement.accepted_at else None,
        "acceptance_reference": agreement.acceptance_reference,
    }
