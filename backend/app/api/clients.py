"""Client records and their associated activity."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import get_session
from backend.app.models import Booking, Client, Invoice
from backend.app.schemas import ClientInput
from backend.app.services.domain import booking_values, client_values, invoice_values

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("")
def list_clients(
    q: str = Query(default="", max_length=200), session: Session = Depends(get_session)
):
    statement = select(Client).order_by(Client.legal_name)
    if q.strip():
        statement = statement.where(Client.legal_name.ilike(f"%{q.strip()}%"))
    return [client_values(row) for row in session.scalars(statement).all()]


@router.post("", status_code=201)
def create_client(payload: ClientInput, session: Session = Depends(get_session)):
    client = Client(**payload.model_dump())
    session.add(client)
    session.commit()
    session.refresh(client)
    return client_values(client)


@router.get("/{client_id}")
def get_client(client_id: int, session: Session = Depends(get_session)):
    client = session.get(Client, client_id)
    if client is None:
        raise HTTPException(404, "Client not found")
    bookings = session.scalars(
        select(Booking).where(Booking.client_id == client_id).order_by(Booking.event_date.desc())
    ).all()
    invoices = session.scalars(
        select(Invoice)
        .join(Booking)
        .where(Booking.client_id == client_id)
        .order_by(Invoice.invoice_date.desc())
    ).all()
    return {
        **client_values(client),
        "bookings": [booking_values(row) for row in bookings],
        "invoices": [invoice_values(row) for row in invoices],
        "agreements": [
            {
                "id": row.id,
                "agreement_ref": row.agreement_ref,
                "effective_date": row.effective_date.isoformat(),
                "status": row.status,
                "template_version": row.template_version,
            }
            for row in client.agreements
        ],
    }


@router.patch("/{client_id}")
def update_client(client_id: int, payload: ClientInput, session: Session = Depends(get_session)):
    client = session.get(Client, client_id)
    if client is None:
        raise HTTPException(404, "Client not found")
    for key, value in payload.model_dump().items():
        setattr(client, key, value)
    session.commit()
    session.refresh(client)
    return client_values(client)
