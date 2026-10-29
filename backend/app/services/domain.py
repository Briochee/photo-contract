"""Domain serialization, validation, and snapshots shared by API routes."""

import hashlib
import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models import (
    AdditionalExpense,
    Booking,
    BookingLineItem,
    Client,
    Invoice,
    InvoiceLineItem,
    PhotographerProfile,
)
from backend.app.services.pricing import calculate_line_item, calculate_totals, money_to_cents


def item_values(item: Any) -> dict[str, Any]:
    """Return a JSON-safe line item view with money represented as decimal strings."""
    return {
        "id": item.id,
        "description": item.description,
        "quantity": item.quantity,
        "unit": item.unit,
        "unit_rate": _cents_text(item.unit_rate_cents),
        "unit_rate_cents": item.unit_rate_cents,
        "amount": _cents_text(item.amount_cents),
        "amount_cents": item.amount_cents,
        "category": getattr(item, "category", "service"),
        "source_booking_line_item_id": getattr(item, "source_booking_line_item_id", None),
        "source_expense_id": getattr(item, "source_expense_id", None),
        "authorization_status": getattr(item, "authorization_status", None),
        "authorization_date": _date(getattr(item, "authorization_date", None)),
        "authorization_reference": getattr(item, "authorization_reference", ""),
        "notes": getattr(item, "notes", ""),
    }


def client_values(client: Client) -> dict[str, Any]:
    return {
        "id": client.id,
        "legal_name": client.legal_name,
        "display_name": client.display_name,
        "mailing_address": client.mailing_address,
        "primary_contact_name": client.primary_contact_name,
        "primary_contact_title": client.primary_contact_title,
        "contact_email": client.contact_email,
        "contact_phone": client.contact_phone,
        "notes": client.notes,
        "created_at": client.created_at.isoformat(),
        "updated_at": client.updated_at.isoformat(),
    }


def booking_values(booking: Booking) -> dict[str, Any]:
    lines = [item_values(row) for row in booking.line_items]
    expenses = [item_values(row) for row in booking.additional_expenses]
    subtotal = sum(row["amount_cents"] for row in lines)
    approved_expenses = sum(
        item["amount_cents"] for item in expenses if item["authorization_status"] == "approved"
    )
    return {
        "id": booking.id,
        "booking_ref": booking.booking_ref,
        "client_id": booking.client_id,
        "client": client_values(booking.client),
        "agreement_id": booking.agreement_id,
        "agreement_date": (
            _date(booking.agreement.effective_date)
            if booking.agreement.status == "accepted"
            else None
        )
        if booking.agreement
        else booking.agreement_date_snapshot,
        "event_name": booking.event_name,
        "event_type": booking.event_type,
        "event_date": booking.event_date.isoformat(),
        "venue": booking.venue,
        "venue_address": booking.venue_address,
        "coverage_start": booking.coverage_start,
        "coverage_end": booking.coverage_end,
        "coverage_hours": booking.coverage_hours,
        "scope": booking.scope,
        "delivery_method": booking.delivery_method,
        "delivery_deadline": booking.delivery_deadline,
        "special_deliverables": booking.special_deliverables,
        "guaranteed_image_count": booking.guaranteed_image_count,
        "overtime_rate": f"{booking.overtime_rate_cents / 100:.2f}",
        "overtime_rate_cents": booking.overtime_rate_cents,
        "payment_terms_days": booking.payment_terms_days,
        "exceptions": booking.exceptions,
        "status": booking.status,
        "accepted_at": _datetime(booking.accepted_at),
        "acceptance_reference": booking.acceptance_reference,
        "line_items": lines,
        "additional_expenses": expenses,
        "subtotal_cents": subtotal,
        "subtotal": _cents_text(subtotal),
        "approved_expenses_total_cents": approved_expenses,
        "total_chargeable_cents": subtotal + approved_expenses,
        "amendments": [
            {
                "id": amendment.id,
                "reference": amendment.amendment_ref,
                "change_summary": amendment.change_summary,
                "changes": json.loads(amendment.changes_json),
                "status": amendment.status,
                "written_acceptance_date": _date(amendment.written_acceptance_date),
                "acceptance_reference": amendment.acceptance_reference,
            }
            for amendment in booking.amendments
        ],
        "created_at": booking.created_at.isoformat(),
        "updated_at": booking.updated_at.isoformat(),
    }


def invoice_status(invoice: Invoice) -> str:
    if invoice.revisions:
        return "voided"
    if invoice.status in {"draft", "voided"}:
        return invoice.status
    paid_cents = sum(payment.amount_cents for payment in invoice.payments)
    if paid_cents >= invoice.total_cents:
        return "paid"
    if paid_cents:
        return "partially_paid"
    if invoice.due_date < date.today():
        return "overdue"
    return "issued"


def invoice_values(invoice: Invoice) -> dict[str, Any]:
    lines = [item_values(row) for row in invoice.line_items]
    paid = sum(payment.amount_cents for payment in invoice.payments)
    return {
        "id": invoice.id,
        "invoice_ref": invoice.invoice_ref,
        "booking_id": invoice.booking_id,
        "booking_ref": invoice.booking.booking_ref,
        "client": client_values(invoice.booking.client),
        "event_name": invoice.booking.event_name,
        "event_date": invoice.booking.event_date.isoformat(),
        "version": invoice.version,
        "revision_of_id": invoice.revision_of_id,
        "is_current": not bool(invoice.revisions),
        "replaced_by_id": invoice.revisions[-1].id if invoice.revisions else None,
        "invoice_date": invoice.invoice_date.isoformat(),
        "due_date": invoice.due_date.isoformat(),
        "status": invoice_status(invoice),
        "record_status": invoice.status,
        "tax_mode": invoice.tax_mode,
        "tax_rate": invoice.tax_rate,
        "line_items": lines,
        "subtotal_cents": invoice.subtotal_cents,
        "tax_cents": invoice.tax_cents,
        "total_cents": invoice.total_cents,
        "amount_paid_cents": paid,
        "balance_due_cents": max(invoice.total_cents - paid, 0),
        "notes": invoice.notes,
        "payments": [
            {
                "id": row.id,
                "paid_at": row.paid_at.isoformat(),
                "amount_cents": row.amount_cents,
                "amount": _cents_text(row.amount_cents),
                "method": row.method,
                "reference": row.reference,
                "notes": row.notes,
            }
            for row in invoice.payments
        ],
        "created_at": invoice.created_at.isoformat(),
        "issued_at": _datetime(invoice.issued_at),
    }


def apply_booking_lines(booking: Booking, inputs: list[Any]) -> None:
    booking.line_items.clear()
    for position, source in enumerate(inputs):
        item = calculate_line_item(
            source.description, source.quantity, source.unit_rate, source.unit
        )
        booking.line_items.append(
            BookingLineItem(
                description=item["description"],
                quantity=item["quantity"],
                unit=item["unit"],
                unit_rate_cents=item["unit_rate_cents"],
                amount_cents=item["amount_cents"],
                category=source.category,
                sort_order=position,
            )
        )


def apply_expenses(booking: Booking, inputs: list[Any]) -> None:
    booking.additional_expenses.clear()
    for position, source in enumerate(inputs):
        if source.authorization_status == "approved" and (
            source.authorization_date is None or not source.authorization_reference.strip()
        ):
            raise ValueError("Approved expenses require a written authorization date and reference")
        item = calculate_line_item(
            source.description, source.quantity, source.unit_rate, source.unit
        )
        booking.additional_expenses.append(
            AdditionalExpense(
                description=item["description"],
                quantity=item["quantity"],
                unit=item["unit"],
                unit_rate_cents=item["unit_rate_cents"],
                amount_cents=item["amount_cents"],
                authorization_status=source.authorization_status,
                authorization_date=source.authorization_date,
                authorization_reference=source.authorization_reference,
                notes=source.notes,
                sort_order=position,
            )
        )


def make_invoice_lines(booking: Booking) -> list[InvoiceLineItem]:
    rows = [
        InvoiceLineItem(
            source_booking_line_item_id=item.id,
            description=item.description,
            quantity=item.quantity,
            unit=item.unit,
            unit_rate_cents=item.unit_rate_cents,
            amount_cents=item.amount_cents,
            sort_order=item.sort_order,
        )
        for item in booking.line_items
    ]
    next_order = len(rows)
    for item in booking.additional_expenses:
        if item.authorization_status != "approved":
            continue
        rows.append(
            InvoiceLineItem(
                source_expense_id=item.id,
                description=item.description,
                quantity=item.quantity,
                unit=item.unit,
                unit_rate_cents=item.unit_rate_cents,
                amount_cents=item.amount_cents,
                sort_order=next_order,
            )
        )
        next_order += 1
    return rows


def select_invoice_lines(booking: Booking, inputs: list[Any]) -> list[InvoiceLineItem]:
    """Build draft invoice rows only from accepted booking charges or approved expenses."""
    if not inputs:
        return make_invoice_lines(booking)
    base_by_id = {item.id: item for item in booking.line_items}
    expenses_by_id = {item.id: item for item in booking.additional_expenses}
    selected_base: set[int] = set()
    selected_expenses: set[int] = set()
    result: list[InvoiceLineItem] = []
    for position, source in enumerate(inputs):
        if source.source_booking_line_item_id is not None:
            source_item = base_by_id.get(source.source_booking_line_item_id)
            if source_item is None or source_item.id in selected_base:
                raise ValueError("Invoice lines must uniquely reference a charge on this booking")
            selected_base.add(source_item.id)
        else:
            source_item = expenses_by_id.get(source.source_expense_id)
            if source_item is None or source_item.id in selected_expenses:
                raise ValueError("Invoice lines must uniquely reference an expense on this booking")
            if source_item.authorization_status != "approved":
                raise ValueError("Only approved additional expenses can be billed")
            selected_expenses.add(source_item.id)
        calculated = calculate_line_item(
            source.description, source.quantity, source.unit_rate, source.unit
        )
        if (
            calculated["description"] != source_item.description
            or calculated["quantity"] != source_item.quantity
            or calculated["unit"] != source_item.unit
            or calculated["unit_rate_cents"] != source_item.unit_rate_cents
            or calculated["amount_cents"] != source_item.amount_cents
        ):
            raise ValueError(
                "Invoice lines must preserve the accepted source charge description and amounts"
            )
        result.append(
            InvoiceLineItem(
                source_booking_line_item_id=(
                    source_item.id if source.source_booking_line_item_id else None
                ),
                source_expense_id=(source_item.id if source.source_expense_id else None),
                description=source_item.description,
                quantity=source_item.quantity,
                unit=source_item.unit,
                unit_rate_cents=source_item.unit_rate_cents,
                amount_cents=source_item.amount_cents,
                sort_order=position,
            )
        )
    if selected_base != set(base_by_id):
        raise ValueError("Every agreed booking line item must appear on the invoice")
    return result


def recalculate_invoice(invoice: Invoice, *, manual_tax: str = "0") -> None:
    rows = [
        {
            "amount_cents": item.amount_cents,
            "authorization_status": "approved" if item.source_expense_id else None,
        }
        for item in invoice.line_items
    ]
    tax_rate = invoice.tax_rate or "0"
    totals = calculate_totals(
        rows,
        tax_mode=invoice.tax_mode,
        tax_rate=tax_rate,
        manual_tax=manual_tax,
    )
    invoice.subtotal_cents = totals.subtotal_cents
    invoice.tax_cents = totals.tax_cents
    invoice.total_cents = totals.total_cents


def snapshot(value: Any) -> tuple[str, str]:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return raw, hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_booking(session: Session, booking_id: int) -> Booking | None:
    statement = (
        select(Booking)
        .options(
            selectinload(Booking.client),
            selectinload(Booking.agreement),
            selectinload(Booking.line_items),
            selectinload(Booking.additional_expenses),
            selectinload(Booking.amendments),
        )
        .where(Booking.id == booking_id)
    )
    return session.scalar(statement)


def get_invoice(session: Session, invoice_id: int) -> Invoice | None:
    statement = (
        select(Invoice)
        .options(
            selectinload(Invoice.booking).selectinload(Booking.client),
            selectinload(Invoice.line_items),
            selectinload(Invoice.payments),
        )
        .where(Invoice.id == invoice_id)
    )
    return session.scalar(statement)


def set_profile(session: Session, payload: Any) -> PhotographerProfile:
    profile = session.scalar(select(PhotographerProfile).order_by(PhotographerProfile.id).limit(1))
    if profile is None:
        profile = PhotographerProfile()
        session.add(profile)
    profile.legal_name = payload.legal_name
    profile.business_name = payload.business_name
    profile.mailing_address = payload.mailing_address
    profile.email = payload.email
    profile.phone = payload.phone
    profile.payment_instructions = payload.payment_instructions
    profile.default_payment_terms_days = payload.default_payment_terms_days
    profile.currency = payload.currency
    profile.default_photography_rate_cents = (
        money_to_cents(payload.default_photography_rate)
        if payload.default_photography_rate is not None
        else None
    )
    profile.default_overtime_rate_cents = (
        money_to_cents(payload.default_overtime_rate)
        if payload.default_overtime_rate is not None
        else None
    )
    profile.default_delivery_method = payload.default_delivery_method
    profile.default_delivery_deadline = payload.default_delivery_deadline
    return profile


def profile_values(profile: PhotographerProfile | None) -> dict[str, Any]:
    """Serialize a saved or empty photographer profile without applying hidden defaults."""
    return {
        "legal_name": profile.legal_name if profile else "",
        "business_name": profile.business_name if profile else None,
        "mailing_address": profile.mailing_address if profile else "",
        "email": profile.email if profile else "",
        "phone": profile.phone if profile else "",
        "payment_instructions": profile.payment_instructions if profile else "",
        "default_payment_terms_days": profile.default_payment_terms_days if profile else None,
        "currency": profile.currency if profile else "USD",
        "default_photography_rate": (
            _cents_text(profile.default_photography_rate_cents)
            if profile and profile.default_photography_rate_cents is not None
            else None
        ),
        "default_overtime_rate": (
            _cents_text(profile.default_overtime_rate_cents)
            if profile and profile.default_overtime_rate_cents is not None
            else None
        ),
        "default_delivery_method": profile.default_delivery_method if profile else None,
        "default_delivery_deadline": profile.default_delivery_deadline if profile else None,
    }


def _date(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _cents_text(cents: int) -> str:
    whole, fraction = divmod(abs(cents), 100)
    return f"{'-' if cents < 0 else ''}{whole}.{fraction:02d}"
