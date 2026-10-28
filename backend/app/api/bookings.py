"""Booking lifecycle, approved expense capture, and written amendments."""

import json
from datetime import UTC, date, datetime, time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import get_session
from backend.app.models import (
    AdditionalExpense,
    Booking,
    BookingAmendment,
    Client,
    Invoice,
    MasterAgreement,
    PhotographerProfile,
)
from backend.app.schemas import (
    AmendmentInput,
    BookingAcceptInput,
    BookingInput,
    ExpenseAuthorizationInput,
    ExpenseInput,
)
from backend.app.services.domain import (
    booking_values,
    get_booking,
    item_values,
    profile_values,
    snapshot,
)
from backend.app.services.pricing import calculate_line_item, money_to_cents
from backend.app.services.references import allocate_reference

router = APIRouter(prefix="/api/bookings", tags=["bookings"])
EDITABLE_AMENDMENT_FIELDS = {
    "event_name",
    "event_type",
    "event_date",
    "venue",
    "venue_address",
    "coverage_start",
    "coverage_end",
    "coverage_hours",
    "scope",
    "delivery_method",
    "delivery_deadline",
    "special_deliverables",
    "guaranteed_image_count",
    "overtime_rate",
    "payment_terms_days",
    "exceptions",
}


@router.get("")
def list_bookings(session: Session = Depends(get_session)):
    rows = session.scalars(select(Booking).order_by(Booking.event_date.desc())).all()
    return [booking_values(get_booking(session, row.id)) for row in rows]


@router.post("", status_code=201)
def create_booking(payload: BookingInput, session: Session = Depends(get_session)):
    client = session.get(Client, payload.client_id)
    if client is None:
        raise HTTPException(404, "Client not found")
    if payload.agreement_id is not None:
        agreement = session.get(MasterAgreement, payload.agreement_id)
        if agreement is None or agreement.client_id != payload.client_id:
            raise HTTPException(422, "The selected agreement must belong to this client")
    profile = session.scalar(select(PhotographerProfile).order_by(PhotographerProfile.id).limit(1))
    year = date.today().year
    try:
        session.rollback()
        with session.begin():
            booking = Booking(
                booking_ref=allocate_reference(session, "booking", year),
                client_id=payload.client_id,
                agreement_id=payload.agreement_id,
                event_name=payload.event_name,
                event_type=payload.event_type,
                event_date=payload.event_date,
                venue=payload.venue,
                venue_address=payload.venue_address,
                coverage_start=payload.coverage_start,
                coverage_end=payload.coverage_end,
                coverage_hours=payload.coverage_hours,
                scope=payload.scope,
                delivery_method=payload.delivery_method,
                delivery_deadline=payload.delivery_deadline
                or (
                    profile.default_delivery_deadline
                    if profile
                    else "Within ten (10) business days after the event"
                ),
                special_deliverables=payload.special_deliverables,
                guaranteed_image_count=payload.guaranteed_image_count,
                overtime_rate_cents=money_to_cents(payload.overtime_rate),
                payment_terms_days=payload.payment_terms_days,
                exceptions=payload.exceptions,
                status="draft",
            )
            session.add(booking)
            session.flush()
            _set_children(booking, payload)
        return booking_values(get_booking(session, booking.id))
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.get("/{booking_id}")
def get_booking_route(booking_id: int, session: Session = Depends(get_session)):
    booking = get_booking(session, booking_id)
    if booking is None:
        raise HTTPException(404, "Booking not found")
    result = booking_values(booking)
    invoices = session.scalars(
        select(Invoice).where(Invoice.booking_id == booking_id).order_by(Invoice.version)
    ).all()
    result["invoices"] = [
        {"id": row.id, "invoice_ref": row.invoice_ref, "status": row.status, "version": row.version}
        for row in invoices
    ]
    return result


@router.patch("/{booking_id}")
def update_booking(booking_id: int, payload: BookingInput, session: Session = Depends(get_session)):
    booking = get_booking(session, booking_id)
    if booking is None:
        raise HTTPException(404, "Booking not found")
    if booking.status != "draft":
        raise HTTPException(409, "Accepted bookings require a documented amendment")
    if payload.client_id != booking.client_id:
        raise HTTPException(422, "A booking cannot be reassigned to another client")
    if payload.agreement_id is not None:
        agreement = session.get(MasterAgreement, payload.agreement_id)
        if agreement is None or agreement.client_id != booking.client_id:
            raise HTTPException(422, "The selected agreement must belong to this client")
    for key, value in payload.model_dump(exclude={"line_items", "additional_expenses"}).items():
        if key == "overtime_rate":
            booking.overtime_rate_cents = money_to_cents(value)
        elif key == "delivery_deadline" and not value:
            continue
        else:
            setattr(booking, key, value)
    try:
        _set_children(booking, payload)
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc
    return booking_values(get_booking(session, booking.id))


@router.post("/{booking_id}/accept")
def accept_booking(
    booking_id: int, payload: BookingAcceptInput, session: Session = Depends(get_session)
):
    booking = get_booking(session, booking_id)
    if booking is None:
        raise HTTPException(404, "Booking not found")
    if booking.status != "draft":
        raise HTTPException(409, "Only draft bookings can be accepted")
    if not booking.line_items:
        raise HTTPException(422, "Add at least one agreed charge before accepting the booking")
    if not payload.acceptance_reference.strip():
        raise HTTPException(422, "Record the client's written acceptance reference")
    profile = session.scalar(select(PhotographerProfile).order_by(PhotographerProfile.id).limit(1))
    booking.status = "accepted"
    booking.accepted_at = datetime.combine(payload.accepted_date, time.min, tzinfo=UTC)
    booking.acceptance_reference = payload.acceptance_reference
    session.flush()
    booking.accepted_snapshot_json, _ = snapshot(
        {"booking": booking_values(booking), "photographer": profile_values(profile)}
    )
    session.commit()
    return booking_values(get_booking(session, booking.id))


@router.post("/{booking_id}/expenses", status_code=201)
def add_expense(booking_id: int, payload: ExpenseInput, session: Session = Depends(get_session)):
    booking = get_booking(session, booking_id)
    if booking is None:
        raise HTTPException(404, "Booking not found")
    try:
        item = calculate_line_item(
            payload.description, payload.quantity, payload.unit_rate, payload.unit
        )
        if payload.authorization_status == "approved" and (
            payload.authorization_date is None or not payload.authorization_reference.strip()
        ):
            raise ValueError("Approved expenses require a written authorization date and reference")
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    expense = AdditionalExpense(
        booking_id=booking.id,
        description=item["description"],
        quantity=item["quantity"],
        unit=item["unit"],
        unit_rate_cents=item["unit_rate_cents"],
        amount_cents=item["amount_cents"],
        authorization_status=payload.authorization_status,
        authorization_date=payload.authorization_date,
        authorization_reference=payload.authorization_reference,
        notes=payload.notes,
        sort_order=len(booking.additional_expenses),
    )
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return item_values(expense)


@router.patch("/{booking_id}/expenses/{expense_id}")
def update_expense_authorization(
    booking_id: int,
    expense_id: int,
    payload: ExpenseAuthorizationInput,
    session: Session = Depends(get_session),
):
    booking = get_booking(session, booking_id)
    if booking is None:
        raise HTTPException(404, "Booking not found")
    expense = session.get(AdditionalExpense, expense_id)
    if expense is None or expense.booking_id != booking_id:
        raise HTTPException(404, "Expense not found")
    if payload.authorization_status == "approved" and (
        payload.authorization_date is None or not payload.authorization_reference.strip()
    ):
        raise HTTPException(
            422, "Approved expenses require a written authorization date and reference"
        )
    expense.authorization_status = payload.authorization_status
    expense.authorization_date = payload.authorization_date
    expense.authorization_reference = payload.authorization_reference.strip()
    expense.notes = payload.notes
    session.commit()
    session.refresh(expense)
    return item_values(expense)


@router.post("/{booking_id}/amendments", status_code=201)
def add_amendment(
    booking_id: int, payload: AmendmentInput, session: Session = Depends(get_session)
):
    booking = get_booking(session, booking_id)
    if booking is None:
        raise HTTPException(404, "Booking not found")
    if booking.status != "accepted":
        raise HTTPException(409, "Amendments are available for accepted bookings")
    invalid = set(payload.changes) - EDITABLE_AMENDMENT_FIELDS
    if invalid:
        raise HTTPException(422, f"Unsupported amendment fields: {', '.join(sorted(invalid))}")
    if payload.accepted and (
        payload.written_acceptance_date is None or not payload.acceptance_reference.strip()
    ):
        raise HTTPException(
            422, "Record the written acceptance date and its reference before applying changes"
        )
    if not payload.changes:
        raise HTTPException(422, "An amendment must contain at least one proposed change")
    string_fields = {
        "event_name",
        "event_type",
        "venue",
        "venue_address",
        "coverage_start",
        "coverage_end",
        "coverage_hours",
        "scope",
        "delivery_method",
        "delivery_deadline",
        "special_deliverables",
        "exceptions",
    }
    for key, value in payload.changes.items():
        if key in string_fields and not isinstance(value, str):
            raise HTTPException(422, f"Amendment field {key} must be text")
        if key == "event_date":
            try:
                date.fromisoformat(str(value))
            except ValueError as exc:
                raise HTTPException(422, "Amended event date must use YYYY-MM-DD") from exc
        if key == "payment_terms_days" and (
            isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 365
        ):
            raise HTTPException(422, "Payment terms must be between 0 and 365 days")
        if key == "guaranteed_image_count" and (
            value is not None
            and (isinstance(value, bool) or not isinstance(value, int) or value < 0)
        ):
            raise HTTPException(422, "Guaranteed image count must be a nonnegative integer")
        if key == "overtime_rate":
            try:
                money_to_cents(str(value))
            except (TypeError, ValueError) as exc:
                raise HTTPException(422, str(exc)) from exc
    old_snapshot = booking.accepted_snapshot_json or snapshot(booking_values(booking))[0]
    amendment = BookingAmendment(
        amendment_ref=f"{booking.booking_ref}-A{len(booking.amendments) + 1}",
        booking_id=booking.id,
        change_summary=payload.change_summary,
        changes_json=json.dumps(payload.changes, ensure_ascii=False, sort_keys=True, default=str),
        previous_snapshot_json=old_snapshot,
        status="accepted" if payload.accepted else "proposed",
        written_acceptance_date=payload.written_acceptance_date if payload.accepted else None,
        acceptance_reference=payload.acceptance_reference if payload.accepted else "",
        accepted_at=(
            datetime.combine(payload.written_acceptance_date, time.min, tzinfo=UTC)
            if payload.accepted and payload.written_acceptance_date
            else None
        ),
    )
    session.add(amendment)
    if payload.accepted:
        for key, value in payload.changes.items():
            if key == "event_date":
                value = date.fromisoformat(str(value))
            if key == "overtime_rate":
                booking.overtime_rate_cents = money_to_cents(str(value))
            else:
                setattr(booking, key, value)
        session.flush()
        profile = session.scalar(
            select(PhotographerProfile).order_by(PhotographerProfile.id).limit(1)
        )
        booking.accepted_snapshot_json, _ = snapshot(
            {"booking": booking_values(booking), "photographer": profile_values(profile)}
        )
    session.commit()
    return {
        "id": amendment.id,
        "reference": amendment.amendment_ref,
        "status": amendment.status,
        "change_summary": amendment.change_summary,
        "changes": payload.changes,
        "written_acceptance_date": payload.written_acceptance_date.isoformat()
        if payload.written_acceptance_date
        else None,
        "acceptance_reference": amendment.acceptance_reference,
    }


def _set_children(booking: Booking, payload: BookingInput) -> None:
    from backend.app.services.domain import apply_booking_lines, apply_expenses

    apply_booking_lines(booking, payload.line_items)
    apply_expenses(booking, payload.additional_expenses)
