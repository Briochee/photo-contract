"""Generate fictional sample PDFs through the production document renderer."""

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.api.agreements import agreement_text
from backend.app.config import TEMPLATE_VERSION
from backend.app.models import (
    AdditionalExpense,
    Base,
    Booking,
    BookingLineItem,
    Client,
    Invoice,
    InvoiceLineItem,
    MasterAgreement,
    PhotographerProfile,
)
from backend.app.services import documents
from backend.app.services.documents import document_context
from backend.app.services.domain import (
    booking_values,
    client_values,
    profile_values,
    recalculate_invoice,
    snapshot,
)
from backend.app.services.pricing import calculate_line_item

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "examples"


def main() -> None:
    """Build a disposable relational fixture and save real agreement, booking, and invoice PDFs."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if any(OUTPUT.iterdir()):
        raise SystemExit("examples/ must be empty before sample PDFs are generated")
    documents.DEFAULT_OUTPUT_DIR = OUTPUT

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(
        engine,
        "connect",
        lambda connection, _record: connection.execute("PRAGMA foreign_keys=ON"),
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        profile = PhotographerProfile(
            legal_name="Sample Photographer",
            business_name="Northlight Photography",
            mailing_address="12 Example Street\nBrooklyn, NY 11201",
            email="studio@example.test",
            phone="555-0100",
            payment_instructions="Sample payment instructions: ACH transfer.",
            default_payment_terms_days=15,
            default_photography_rate_cents=75_000,
            default_overtime_rate_cents=15_000,
        )
        client = Client(
            legal_name="Example Corporation",
            display_name="Example",
            mailing_address="100 Sample Avenue\nNew York, NY 10001",
            primary_contact_name="Jordan Lee",
            primary_contact_title="Events Director",
            contact_email="jordan@example.test",
            contact_phone="555-0123",
        )
        session.add_all([profile, client])
        session.flush()

        effective_date = date(2026, 10, 28)
        legal_text = agreement_text()
        agreement = MasterAgreement(
            agreement_ref="AGR-2026-001",
            client_id=client.id,
            photographer_profile_id=profile.id,
            effective_date=effective_date,
            status="accepted",
            template_version=TEMPLATE_VERSION,
            legal_text_hash=hashlib.sha256(legal_text.encode("utf-8")).hexdigest(),
            legal_text_snapshot=legal_text,
            source_snapshot_json=snapshot(
                {
                    "client": client_values(client),
                    "photographer": profile_values(profile),
                    "effective_date": effective_date.isoformat(),
                }
            )[0],
            accepted_at=datetime(2026, 10, 28, tzinfo=UTC),
            acceptance_reference="Sample signed agreement record",
        )
        session.add(agreement)
        session.flush()

        booking = Booking(
            booking_ref="BK-2026-001",
            client_id=client.id,
            agreement_id=agreement.id,
            agreement_date_snapshot=effective_date.isoformat(),
            event_name="Annual leadership conference",
            event_type="Corporate event",
            event_date=date(2026, 11, 20),
            venue="Grand Hall",
            venue_address="9 Broadway, New York, NY 10004",
            coverage_start="09:00",
            coverage_end="15:00",
            coverage_hours="6",
            scope="Keynote, speaker portraits, and candid attendee coverage.",
            delivery_method="Private online gallery",
            delivery_deadline="Within ten (10) business days after the event",
            guaranteed_image_count=120,
            overtime_rate_cents=15_000,
            payment_terms_days=15,
            status="accepted",
            accepted_at=datetime(2026, 10, 28, tzinfo=UTC),
            acceptance_reference="Sample booking confirmation acceptance record",
        )
        package = calculate_line_item(
            "Photography package · six hours", "1", "750.00", "package"
        )
        retouching = calculate_line_item(
            "Advanced portrait retouching", "4", "30.00", "image"
        )
        parking = calculate_line_item("Event parking", "1", "42.50", "day")
        booking.line_items.extend(
            BookingLineItem(
                description=item["description"],
                quantity=item["quantity"],
                unit=item["unit"],
                unit_rate_cents=item["unit_rate_cents"],
                amount_cents=item["amount_cents"],
                category="photography",
                sort_order=position,
            )
            for position, item in enumerate((package, retouching))
        )
        booking.additional_expenses.append(
            AdditionalExpense(
                description=parking["description"],
                quantity=parking["quantity"],
                unit=parking["unit"],
                unit_rate_cents=parking["unit_rate_cents"],
                amount_cents=parking["amount_cents"],
                authorization_status="approved",
                authorization_date=effective_date,
                authorization_reference="Sample written expense approval",
                sort_order=0,
            )
        )
        session.add(booking)
        session.flush()
        booking.accepted_snapshot_json = snapshot(
            {
                "booking": booking_values(booking),
                "photographer": profile_values(profile),
            }
        )[0]

        invoice = Invoice(
            invoice_ref="INV-2026-001",
            booking_id=booking.id,
            invoice_date=effective_date,
            due_date=date(2026, 11, 12),
            status="issued",
            tax_mode="none",
            tax_rate="0",
            issued_at=datetime(2026, 10, 28, tzinfo=UTC),
            notes="Sample invoice for preview purposes.",
        )
        source_items = [*booking.line_items, *booking.additional_expenses]
        invoice.line_items.extend(
            InvoiceLineItem(
                source_booking_line_item_id=(
                    item.id if isinstance(item, BookingLineItem) else None
                ),
                source_expense_id=(
                    item.id if isinstance(item, AdditionalExpense) else None
                ),
                description=item.description,
                quantity=item.quantity,
                unit=item.unit,
                unit_rate_cents=item.unit_rate_cents,
                amount_cents=item.amount_cents,
                sort_order=position,
            )
            for position, item in enumerate(source_items)
        )
        recalculate_invoice(invoice)
        session.add(invoice)
        session.flush()
        _, _, invoice_snapshot, _ = document_context(session, "invoice", invoice.id)
        invoice.issued_snapshot_json = snapshot(invoice_snapshot)[0]
        session.commit()

        generated = [
            documents.generate_document(session, "agreement", agreement.id),
            documents.generate_document(session, "booking_confirmation", booking.id),
            documents.generate_document(session, "invoice", invoice.id),
        ]
        saved_files = [
            (document.file_path, document.content_hash) for document in generated
        ]

    engine.dispose()
    for file_path, content_hash in saved_files:
        print(f"{Path(file_path)} · {content_hash}")


if __name__ == "__main__":
    main()
