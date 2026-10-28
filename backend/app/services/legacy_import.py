"""Idempotent import from the former Streamlit JSON and reference-counter store."""

import hashlib
import json
import re
import shutil
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.config import DATA_DIR, DEFAULT_OUTPUT_DIR
from backend.app.logging_config import activity
from backend.app.models import (
    AdditionalExpense,
    Booking,
    BookingLineItem,
    Client,
    GeneratedDocument,
    Invoice,
    InvoiceLineItem,
    PhotographerProfile,
    ReferenceSequence,
)
from backend.app.services.domain import recalculate_invoice, snapshot
from backend.app.services.pricing import calculate_line_item, due_date, money_to_cents

BOOKING_REF = re.compile(r"^BK-(\d{4})-(\d{3,})$")
INVOICE_REF = re.compile(r"^INV-(\d{4})-(\d{3,})$")
OLD_DOCUMENTS = {
    "Master-Agreement": "agreement",
    "Booking-Confirmation": "booking_confirmation",
    "Invoice": "invoice",
}


def import_legacy(session: Session, source_dir: Path = DATA_DIR) -> dict[str, Any]:
    """Import JSON bookings, reference counters, and old PDFs without deleting source files."""
    report: dict[str, Any] = {
        "imported_bookings": 0,
        "skipped_bookings": 0,
        "imported_documents": 0,
        "issues": [],
    }
    _import_sequences(session, source_dir / "references.sqlite3")
    for path in sorted(source_dir.glob("BK-*.json")):
        savepoint = session.begin_nested()
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            reference = str(record["booking_ref"])
            match = BOOKING_REF.fullmatch(reference)
            if match is None:
                raise ValueError("invalid booking reference")
            existing = session.scalar(select(Booking.id).where(Booking.booking_ref == reference))
            if existing:
                report["skipped_bookings"] += 1
                continue
            booking = _import_record(session, record, int(match.group(1)))
            session.flush()
            report["imported_bookings"] += 1
            report["imported_documents"] += _import_old_pdfs(session, source_dir, booking, record)
            savepoint.commit()
        except (KeyError, OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            savepoint.rollback()
            report["issues"].append({"file": path.name, "reason": str(exc)})
        except Exception:
            savepoint.rollback()
            report["issues"].append(
                {"file": path.name, "reason": "database or data validation error"}
            )
    session.commit()
    activity.info(
        "legacy_import bookings=%d documents=%d issues=%d",
        report["imported_bookings"],
        report["imported_documents"],
        len(report["issues"]),
    )
    return report


def _import_sequences(session: Session, legacy_path: Path) -> None:
    if not legacy_path.is_file():
        return
    with sqlite3.connect(f"file:{legacy_path}?mode=ro", uri=True) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "sequences" not in tables:
            return
        columns = {row[1] for row in connection.execute("PRAGMA table_info(sequences)")}
        if not {"year", "seq"}.issubset(columns):
            return
        for year, last_value in connection.execute("SELECT year, seq FROM sequences"):
            for kind in ("booking", "invoice"):
                current = session.get(ReferenceSequence, (kind, int(year)))
                if current is None:
                    session.add(
                        ReferenceSequence(kind=kind, year=int(year), last_value=int(last_value))
                    )
                else:
                    current.last_value = max(current.last_value, int(last_value))
    session.flush()


def _import_record(session: Session, record: dict[str, Any], year: int) -> Booking:
    photographer = session.scalar(
        select(PhotographerProfile).order_by(PhotographerProfile.id).limit(1)
    )
    if photographer is None:
        photographer = PhotographerProfile()
        session.add(photographer)
    photographer.legal_name = str(record.get("photographer", ""))[:200]
    photographer.mailing_address = str(record.get("photographer_address", ""))
    photographer.email = str(record.get("photographer_email", ""))[:254]
    photographer.payment_instructions = str(record.get("payment_instructions", ""))
    photographer.default_payment_terms_days = _bounded_days(record.get("net_days", 15))
    photographer.default_overtime_rate_cents = money_to_cents(
        str(record.get("overtime_rate", "150"))
    )

    legal_name = str(record.get("client", "")).strip()
    if not legal_name:
        raise ValueError("client legal name is empty")
    email = str(record.get("client_email", ""))[:254]
    client = session.scalar(
        select(Client)
        .where(Client.legal_name == legal_name, Client.contact_email == email)
        .limit(1)
    )
    if client is None:
        client = Client(legal_name=legal_name, contact_email=email)
        session.add(client)
    client.mailing_address = str(record.get("client_address", ""))
    client.primary_contact_name = str(record.get("client_contact", ""))[:160]
    client.contact_phone = str(record.get("client_phone", ""))[:80]

    event_date = _required_date(record.get("event_date"), "event date")
    booking_ref = str(record["booking_ref"])
    booking = Booking(
        booking_ref=booking_ref,
        client=client,
        agreement_date_snapshot=str(record.get("agreement_date", ""))[:10],
        event_name=str(record.get("event_name", "Imported photography assignment"))[:200]
        or "Imported photography assignment",
        event_date=event_date,
        venue=str(record.get("venue", ""))[:200],
        coverage_start=str(record.get("start_time", "09:00"))[:20],
        coverage_end=str(record.get("end_time", "15:00"))[:20],
        coverage_hours=str(record.get("coverage_hours", "6"))[:24],
        scope=str(record.get("scope", "")),
        delivery_method=str(record.get("delivery_method", "Online gallery"))[:100],
        delivery_deadline=str(record.get("delivery_deadline", ""))[:120],
        special_deliverables=str(record.get("special_deliverables", "")),
        guaranteed_image_count=_optional_int(record.get("image_count")),
        overtime_rate_cents=money_to_cents(str(record.get("overtime_rate", "150"))),
        authorized_expense_notes=str(record.get("approved_expenses", "")),
        exceptions=str(record.get("exceptions", "")),
        payment_terms_days=_bounded_days(record.get("net_days", 15)),
        status="draft",
    )
    for position, source in enumerate(record.get("booking_lines", [])):
        item = calculate_line_item(
            str(source.get("description", "")),
            str(source.get("quantity", "1")),
            str(source.get("rate", "0")),
        )
        booking.line_items.append(
            BookingLineItem(
                description=item["description"],
                quantity=item["quantity"],
                unit="service",
                unit_rate_cents=item["unit_rate_cents"],
                amount_cents=item["amount_cents"],
                category="photography",
                sort_order=position,
            )
        )
    for position, source in enumerate(record.get("invoice_extras", [])):
        if not str(source.get("description", "")).strip():
            continue
        item = calculate_line_item(
            str(source["description"]),
            str(source.get("quantity", "1")),
            str(source.get("rate", "0")),
        )
        booking.additional_expenses.append(
            AdditionalExpense(
                description=item["description"],
                quantity=item["quantity"],
                unit=item["unit"],
                unit_rate_cents=item["unit_rate_cents"],
                amount_cents=item["amount_cents"],
                authorization_status="approved" if source.get("approved") else "proposed",
                authorization_reference="Legacy Streamlit written approval confirmed"
                if source.get("approved")
                else "",
                sort_order=position,
            )
        )
    session.add(booking)
    session.flush()

    invoice_ref = str(record.get("invoice_ref", ""))
    invoice_match = INVOICE_REF.fullmatch(invoice_ref)
    if invoice_match is None:
        raise ValueError("invalid invoice reference")
    invoice_date = _required_date(record.get("invoice_date"), "invoice date")
    net_days = _bounded_days(record.get("net_days", 15))
    invoice = Invoice(
        invoice_ref=invoice_ref,
        booking_id=booking.id,
        invoice_date=invoice_date,
        due_date=date.fromisoformat(due_date(invoice_date.isoformat(), net_days)),
        status="draft",
        tax_mode="manual",
        tax_rate=str(record.get("tax_amount", "0")),
        notes=str(record.get("invoice_notes", "")),
        line_items=[
            InvoiceLineItem(
                source_booking_line_item_id=line.id,
                description=line.description,
                quantity=line.quantity,
                unit=line.unit,
                unit_rate_cents=line.unit_rate_cents,
                amount_cents=line.amount_cents,
                sort_order=line.sort_order,
            )
            for line in booking.line_items
        ],
    )
    for expense in booking.additional_expenses:
        if expense.authorization_status == "approved":
            invoice.line_items.append(
                InvoiceLineItem(
                    source_expense_id=expense.id,
                    description=expense.description,
                    quantity=expense.quantity,
                    unit=expense.unit,
                    unit_rate_cents=expense.unit_rate_cents,
                    amount_cents=expense.amount_cents,
                    sort_order=len(invoice.line_items),
                )
            )
    session.add(invoice)
    session.flush()
    recalculate_invoice(invoice, manual_tax=str(record.get("tax_amount", "0")))
    _import_sequences_from_reference(session, "booking", booking_ref)
    _import_sequences_from_reference(session, "invoice", invoice_ref)
    return booking


def _import_old_pdfs(
    session: Session, source_dir: Path, booking: Booking, record: dict[str, Any]
) -> int:
    source_folder = source_dir / "exports" / booking.booking_ref
    if not source_folder.is_dir():
        return 0
    client_id = booking.client_id
    invoice = session.scalar(select(Invoice).where(Invoice.booking_id == booking.id).limit(1))
    imported = 0
    for suffix, document_type in OLD_DOCUMENTS.items():
        source_path = source_folder / f"{booking.booking_ref}_{suffix}.pdf"
        if not source_path.is_file():
            continue
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        destination = DEFAULT_OUTPUT_DIR / source_path.name
        if destination.exists():
            continue
        shutil.copy2(source_path, destination)
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        context_json, _ = snapshot(
            {"legacy_import": True, "source": source_path.name, "booking_ref": booking.booking_ref}
        )
        session.add(
            GeneratedDocument(
                document_type=document_type,
                client_id=client_id,
                booking_id=booking.id,
                invoice_id=invoice.id if document_type == "invoice" and invoice else None,
                reference=booking.booking_ref
                if document_type != "invoice"
                else str(record.get("invoice_ref", "")),
                version=1,
                status="final",
                file_path=str(destination.resolve()),
                content_hash=digest,
                template_version="legacy-import",
                source_snapshot_json=context_json,
            )
        )
        imported += 1
    return imported


def _import_sequences_from_reference(session: Session, kind: str, reference: str) -> None:
    match = (
        BOOKING_REF.fullmatch(reference) if kind == "booking" else INVOICE_REF.fullmatch(reference)
    )
    if match is None:
        return
    year, number = int(match.group(1)), int(match.group(2))
    sequence = session.get(ReferenceSequence, (kind, year))
    if sequence is None:
        session.add(ReferenceSequence(kind=kind, year=year, last_value=number))
    else:
        sequence.last_value = max(sequence.last_value, number)


def _required_date(value: Any, label: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"invalid {label}") from exc


def _bounded_days(value: Any) -> int:
    days = int(value)
    if not 0 <= days <= 365:
        raise ValueError("payment term is outside the supported 0-365 day range")
    return days


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    number = int(value)
    if number < 0:
        raise ValueError("guaranteed image count cannot be negative")
    return number
