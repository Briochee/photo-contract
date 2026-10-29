"""Action-oriented dashboard summaries derived from local business records."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import get_session
from backend.app.models import Booking, Client, GeneratedDocument, Invoice
from backend.app.services.domain import invoice_status

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(session: Session = Depends(get_session)):
    today = date.today()
    bookings = session.scalars(select(Booking).order_by(Booking.event_date)).all()
    invoices = session.scalars(select(Invoice)).all()
    outstanding = sum(
        max(invoice.total_cents - sum(payment.amount_cents for payment in invoice.payments), 0)
        for invoice in invoices
        if invoice.status == "issued" and not invoice.revisions
    )
    recent_clients = session.scalars(
        select(Client).order_by(Client.created_at.desc()).limit(5)
    ).all()
    recent_documents = session.scalars(
        select(GeneratedDocument).order_by(GeneratedDocument.created_at.desc()).limit(6)
    ).all()
    upcoming = [
        {
            "id": booking.id,
            "booking_ref": booking.booking_ref,
            "event_name": booking.event_name,
            "event_date": booking.event_date.isoformat(),
            "client_name": booking.client.display_name or booking.client.legal_name,
            "status": booking.status,
        }
        for booking in bookings
        if booking.event_date >= today and booking.status != "cancelled"
    ][:6]
    return {
        "active_bookings": sum(
            booking.status in {"draft", "pending", "finalized"} for booking in bookings
        ),
        "upcoming_assignments": upcoming,
        "draft_invoices": sum(invoice.status == "draft" for invoice in invoices),
        "outstanding_invoices": sum(
            invoice_status(invoice) in {"issued", "partially_paid", "overdue"}
            for invoice in invoices
        ),
        "outstanding_balance_cents": outstanding,
        "recent_clients": [
            {"id": client.id, "legal_name": client.legal_name, "display_name": client.display_name}
            for client in recent_clients
        ],
        "recent_documents": [
            {
                "id": item.id,
                "document_type": item.document_type,
                "reference": item.reference,
                "version": item.version,
                "created_at": item.created_at.isoformat(),
                "status": item.status,
            }
            for item in recent_documents
        ],
    }
