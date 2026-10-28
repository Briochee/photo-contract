"""Draft invoices, issuance snapshots, revisions, and recorded payments."""

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.database import get_session
from backend.app.models import Booking, Invoice, Payment
from backend.app.schemas import InvoiceInput, PaymentInput
from backend.app.services.documents import document_context
from backend.app.services.domain import (
    get_invoice,
    invoice_values,
    recalculate_invoice,
    select_invoice_lines,
    snapshot,
)
from backend.app.services.pricing import due_date, money_to_cents
from backend.app.services.references import allocate_reference

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.get("")
def list_invoices(session: Session = Depends(get_session)):
    rows = session.scalars(
        select(Invoice)
        .options(selectinload(Invoice.booking).selectinload(Booking.client))
        .order_by(Invoice.invoice_date.desc())
    ).all()
    return [invoice_values(get_invoice(session, row.id)) for row in rows]


@router.post("", status_code=201)
def create_invoice(payload: InvoiceInput, session: Session = Depends(get_session)):
    booking = session.scalar(
        select(Booking)
        .options(
            selectinload(Booking.client),
            selectinload(Booking.line_items),
            selectinload(Booking.additional_expenses),
        )
        .where(Booking.id == payload.booking_id)
    )
    if booking is None:
        raise HTTPException(404, "Booking not found")
    if booking.status != "accepted":
        raise HTTPException(409, "Accept the booking before creating an invoice")
    if payload.due_date < payload.invoice_date:
        raise HTTPException(422, "The due date cannot be before the invoice date")
    expected_due = date.fromisoformat(
        due_date(payload.invoice_date.isoformat(), booking.payment_terms_days)
    )
    if payload.due_date != expected_due:
        raise HTTPException(
            422, f"Due date must follow the accepted payment terms ({expected_due.isoformat()})"
        )
    try:
        session.rollback()
        with session.begin():
            invoice = Invoice(
                invoice_ref=allocate_reference(session, "invoice", payload.invoice_date.year),
                booking_id=booking.id,
                invoice_date=payload.invoice_date,
                due_date=payload.due_date,
                status="draft",
                tax_mode=payload.tax_mode,
                tax_rate=payload.manual_tax if payload.tax_mode == "manual" else payload.tax_rate,
                notes=payload.notes,
                line_items=select_invoice_lines(booking, payload.line_items),
            )
            session.add(invoice)
            session.flush()
            recalculate_invoice(invoice, manual_tax=payload.manual_tax)
        return invoice_values(get_invoice(session, invoice.id))
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.get("/{invoice_id}")
def get_invoice_route(invoice_id: int, session: Session = Depends(get_session)):
    invoice = get_invoice(session, invoice_id)
    if invoice is None:
        raise HTTPException(404, "Invoice not found")
    return invoice_values(invoice)


@router.patch("/{invoice_id}")
def update_invoice(invoice_id: int, payload: InvoiceInput, session: Session = Depends(get_session)):
    invoice = get_invoice(session, invoice_id)
    if invoice is None:
        raise HTTPException(404, "Invoice not found")
    if invoice.status != "draft":
        raise HTTPException(409, "Issued invoices are immutable; create a documented revision")
    if payload.booking_id != invoice.booking_id:
        raise HTTPException(422, "An invoice cannot be reassigned to another booking")
    booking = invoice.booking
    if payload.due_date < payload.invoice_date:
        raise HTTPException(422, "The due date cannot be before the invoice date")
    expected_due = date.fromisoformat(
        due_date(payload.invoice_date.isoformat(), booking.payment_terms_days)
    )
    if payload.due_date != expected_due:
        raise HTTPException(
            422, f"Due date must follow the accepted payment terms ({expected_due.isoformat()})"
        )
    try:
        invoice.invoice_date = payload.invoice_date
        invoice.due_date = payload.due_date
        invoice.tax_mode = payload.tax_mode
        invoice.tax_rate = payload.manual_tax if payload.tax_mode == "manual" else payload.tax_rate
        invoice.notes = payload.notes
        invoice.line_items.clear()
        invoice.line_items.extend(select_invoice_lines(booking, payload.line_items))
        recalculate_invoice(invoice, manual_tax=payload.manual_tax)
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc
    return invoice_values(get_invoice(session, invoice.id))


@router.post("/{invoice_id}/issue")
def issue_invoice(invoice_id: int, session: Session = Depends(get_session)):
    invoice = get_invoice(session, invoice_id)
    if invoice is None:
        raise HTTPException(404, "Invoice not found")
    if invoice.status != "draft":
        raise HTTPException(409, "Only draft invoices can be issued")
    invoice.status = "issued"
    invoice.issued_at = datetime.now(UTC)
    session.flush()
    _, _, document_snapshot, _ = document_context(session, "invoice", invoice.id)
    invoice.issued_snapshot_json, _ = snapshot(document_snapshot)
    session.commit()
    return invoice_values(get_invoice(session, invoice.id))


@router.post("/{invoice_id}/payments", status_code=201)
def add_payment(invoice_id: int, payload: PaymentInput, session: Session = Depends(get_session)):
    invoice = get_invoice(session, invoice_id)
    if invoice is None:
        raise HTTPException(404, "Invoice not found")
    if invoice.status != "issued":
        raise HTTPException(409, "Payments can be recorded only against an issued invoice")
    if invoice.revisions:
        raise HTTPException(
            409, "This invoice has been replaced; record payment against the current revision"
        )
    try:
        cents = money_to_cents(payload.amount)
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    if cents <= 0:
        raise HTTPException(422, "Payment amount must be greater than zero")
    paid = sum(payment.amount_cents for payment in invoice.payments)
    if paid + cents > invoice.total_cents:
        raise HTTPException(422, "Payment would exceed the invoice balance")
    payment = Payment(
        invoice_id=invoice.id,
        paid_at=payload.paid_at,
        amount_cents=cents,
        method=payload.method,
        reference=payload.reference,
        notes=payload.notes,
    )
    invoice.payments.append(payment)
    session.commit()
    return invoice_values(get_invoice(session, invoice.id))


@router.post("/{invoice_id}/revisions", status_code=201)
def revise_invoice(invoice_id: int, session: Session = Depends(get_session)):
    previous = get_invoice(session, invoice_id)
    if previous is None:
        raise HTTPException(404, "Invoice not found")
    if previous.status != "issued" or previous.revisions:
        raise HTTPException(409, "Only an issued invoice can be replaced")
    if previous.payments:
        raise HTTPException(
            409, "An invoice with recorded payments cannot be replaced automatically"
        )
    try:
        session.rollback()
        with session.begin():
            revision = Invoice(
                invoice_ref=allocate_reference(session, "invoice", date.today().year),
                booking_id=previous.booking_id,
                revision_of_id=previous.id,
                version=previous.version + 1,
                invoice_date=date.today(),
                due_date=date.fromisoformat(
                    due_date(date.today().isoformat(), previous.booking.payment_terms_days)
                ),
                status="draft",
                tax_mode=previous.tax_mode,
                tax_rate=previous.tax_rate,
                notes=previous.notes,
                line_items=[
                    type(item)(
                        description=item.description,
                        quantity=item.quantity,
                        unit=item.unit,
                        unit_rate_cents=item.unit_rate_cents,
                        amount_cents=item.amount_cents,
                        sort_order=item.sort_order,
                        source_booking_line_item_id=item.source_booking_line_item_id,
                        source_expense_id=item.source_expense_id,
                    )
                    for item in previous.line_items
                ],
            )
            session.add(revision)
            session.flush()
            recalculate_invoice(
                revision, manual_tax=previous.tax_rate if previous.tax_mode == "manual" else "0"
            )
        return invoice_values(get_invoice(session, revision.id))
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc
