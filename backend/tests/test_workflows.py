"""Contract tests for linked client, booking, invoice, and payment records."""

from datetime import date, timedelta
from io import BytesIO

from pypdf import PdfReader, PdfWriter


def test_dynamic_same_origin_write_and_cross_site_write_protection(client) -> None:
    dynamic_origin = client.post(
        "/api/clients",
        headers={"host": "testserver:43127", "origin": "http://testserver:43127"},
        json={"legal_name": "Desktop Client"},
    )
    assert dynamic_origin.status_code == 201

    cross_site = client.post(
        "/api/clients",
        headers={"origin": "https://untrusted.example"},
        json={"legal_name": "Blocked Client"},
    )
    assert cross_site.status_code == 403


def _profile(client) -> None:
    response = client.patch(
        "/api/settings",
        json={
            "legal_name": "Studio Photographer",
            "business_name": "Northlight Studio",
            "mailing_address": "12 Main Street",
            "email": "photo@example.test",
            "phone": "555-0100",
            "payment_instructions": "Pay by bank transfer.",
            "default_payment_terms_days": 15,
            "currency": "USD",
            "default_photography_rate": "800.00",
            "default_overtime_rate": "150.00",
            "default_delivery_method": "Online gallery",
            "default_delivery_deadline": "Within ten business days after the event",
        },
    )
    assert response.status_code == 200


def _booking_payload(client_id: int) -> dict:
    return {
        "client_id": client_id,
        "agreement_id": None,
        "event_name": "Annual meeting",
        "event_type": "Corporate event",
        "event_date": "2026-11-20",
        "venue": "Grand Hall",
        "venue_address": "9 Broadway",
        "coverage_start": "09:00",
        "coverage_end": "15:00",
        "coverage_hours": "6",
        "scope": "Keynote and attendee portraits.",
        "delivery_method": "Online gallery",
        "delivery_deadline": "Within ten business days after the event",
        "special_deliverables": "",
        "guaranteed_image_count": None,
        "overtime_rate": "150.00",
        "payment_terms_days": 15,
        "exceptions": "",
        "line_items": [
            {
                "description": "Photography package",
                "quantity": "1",
                "unit": "package",
                "unit_rate": "800.00",
                "category": "photography",
            }
        ],
        "additional_expenses": [],
    }


def test_booking_invoice_payments_and_immutability(client) -> None:
    _profile(client)
    client_response = client.post(
        "/api/clients",
        json={
            "legal_name": "Example Corporation",
            "display_name": "Example",
            "mailing_address": "100 Park Avenue",
            "primary_contact_name": "Jordan Lee",
            "primary_contact_title": "Events Director",
            "contact_email": "jordan@example.test",
            "contact_phone": "555-0123",
            "notes": "",
        },
    )
    assert client_response.status_code == 201
    client_id = client_response.json()["id"]

    agreement_response = client.post(
        "/api/agreements",
        json={"client_id": client_id},
    )
    assert agreement_response.status_code == 201
    agreement = agreement_response.json()
    agreement_pdf = client.post(
        "/api/documents/preview",
        json={"document_type": "agreement", "entity_id": agreement["id"]},
    )
    assert agreement_pdf.status_code == 200, agreement_pdf.text
    assert agreement_pdf.content.startswith(b"%PDF-")
    agreement_reader = PdfReader(BytesIO(agreement_pdf.content))
    agreement_fields = agreement_reader.get_fields() or {}
    assert set(agreement_fields) == {
        "agreement.photographer.signature",
        "agreement.photographer.typed_signature",
        "agreement.photographer.date",
        "agreement.photographer.signer_name_title",
        "agreement.client.authorized_representative",
        "agreement.client.signature",
        "agreement.client.typed_signature",
        "agreement.client.date",
    }
    assert agreement_fields["agreement.client.signature"]["/FT"] == "/Sig"
    assert agreement_fields["agreement.client.typed_signature"]["/FT"] == "/Tx"
    assert "16. Signatures" in agreement_reader.pages[-1].extract_text()
    assert all("16. Signatures" not in page.extract_text() for page in agreement_reader.pages[:-1])
    agreement_widgets = {
        annotation.get_object()["/T"]: annotation.get_object()["/Rect"]
        for annotation in agreement_reader.pages[-1].get("/Annots", [])
        if annotation.get_object().get("/Subtype") == "/Widget"
    }
    photographer_signature = agreement_widgets["agreement.photographer.signature"]
    client_signature = agreement_widgets["agreement.client.signature"]
    assert photographer_signature[0] < client_signature[0]
    assert photographer_signature[1] == client_signature[1]
    signature_pair_center = (float(photographer_signature[0]) + float(client_signature[2])) / 2
    assert abs(signature_pair_center - float(agreement_reader.pages[-1].mediabox.width) / 2) < 2
    filled_writer = PdfWriter()
    filled_writer.clone_document_from_reader(agreement_reader)
    filled_writer.update_page_form_field_values(
        None,
        {
            "agreement.photographer.date": "2026-10-29",
            "agreement.client.authorized_representative": "Jordan Lee, Events Director",
            "agreement.client.typed_signature": "Jordan Lee",
        },
        auto_regenerate=False,
    )
    filled_pdf = BytesIO()
    filled_writer.write(filled_pdf)
    filled_fields = PdfReader(filled_pdf).get_fields() or {}
    assert filled_fields["agreement.photographer.date"]["/V"] == "2026-10-29"
    assert (
        filled_fields["agreement.client.authorized_representative"]["/V"]
        == "Jordan Lee, Events Director"
    )
    assert filled_fields["agreement.client.typed_signature"]["/V"] == "Jordan Lee"

    booking_payload = _booking_payload(client_id)
    booking_payload["agreement_id"] = agreement["id"]
    booking_response = client.post("/api/bookings", json=booking_payload)
    assert booking_response.status_code == 201
    booking = booking_response.json()
    assert booking["booking_ref"].startswith("BK-2026-")
    assert booking["subtotal_cents"] == 80000

    accepted = client.post(
        f"/api/bookings/{booking['id']}/accept",
        json={"accepted_date": "2026-10-28", "acceptance_reference": "Signed booking PDF, page 2"},
    )
    assert accepted.status_code == 200
    booking_pdf = client.post(
        "/api/documents/preview",
        json={"document_type": "booking_confirmation", "entity_id": booking["id"]},
    )
    assert booking_pdf.status_code == 200, booking_pdf.text
    assert booking_pdf.content.startswith(b"%PDF-")
    booking_reader = PdfReader(BytesIO(booking_pdf.content))
    booking_fields = booking_reader.get_fields() or {}
    assert set(booking_fields) == {
        "booking.photographer.signature",
        "booking.photographer.typed_signature",
        "booking.photographer.date",
        "booking.photographer.signer_name_title",
        "booking.client.authorized_representative",
        "booking.client.signature",
        "booking.client.typed_signature",
        "booking.client.date",
    }
    assert booking_fields["booking.client.signature"]["/FT"] == "/Sig"
    assert booking_fields["booking.client.typed_signature"]["/FT"] == "/Tx"
    assert "Acceptance" in booking_reader.pages[-1].extract_text()
    booking_widgets = {
        annotation.get_object()["/T"]: annotation.get_object()["/Rect"]
        for annotation in booking_reader.pages[-1].get("/Annots", [])
        if annotation.get_object().get("/Subtype") == "/Widget"
    }
    assert (
        booking_widgets["booking.photographer.signature"][1]
        == booking_widgets["booking.client.signature"][1]
    )

    expense = client.post(
        f"/api/bookings/{booking['id']}/expenses",
        json={
            "description": "Parking",
            "quantity": "1",
            "unit": "day",
            "unit_rate": "30.00",
            "category": "expense",
            "authorization_status": "approved",
            "authorization_date": "2026-10-27",
            "authorization_reference": "Client email, 2026-10-27",
            "notes": "",
        },
    )
    assert expense.status_code == 201

    forbidden_edit = client.patch(
        f"/api/bookings/{booking['id']}", json=_booking_payload(client_id)
    )
    assert forbidden_edit.status_code == 409

    booking_detail = client.get(f"/api/bookings/{booking['id']}").json()
    assert booking_detail["subtotal_cents"] == 80000
    assert booking_detail["approved_expenses_total_cents"] == 3000
    assert booking_detail["total_chargeable_cents"] == 83000
    invoice_lines = [
        {
            "source_booking_line_item_id": booking_detail["line_items"][0]["id"],
            "source_expense_id": None,
            "description": "Photography package",
            "quantity": "1",
            "unit": "package",
            "unit_rate": "800.00",
        },
        {
            "source_booking_line_item_id": None,
            "source_expense_id": expense.json()["id"],
            "description": "Parking",
            "quantity": "1",
            "unit": "day",
            "unit_rate": "30.00",
        },
    ]
    invoice_date = date(2026, 10, 28)
    invoice_payload = {
        "booking_id": booking["id"],
        "invoice_date": invoice_date.isoformat(),
        "due_date": (invoice_date + timedelta(days=15)).isoformat(),
        "tax_mode": "none",
        "tax_rate": "0",
        "manual_tax": "0",
        "notes": "",
        "line_items": invoice_lines,
    }
    invoice_response = client.post("/api/invoices", json=invoice_payload)
    assert invoice_response.status_code == 201, invoice_response.text
    invoice = invoice_response.json()
    assert invoice["subtotal_cents"] == 83000
    assert invoice["total_cents"] == booking["subtotal_cents"] + expense.json()["amount_cents"]

    issued = client.post(f"/api/invoices/{invoice['id']}/issue")
    assert issued.status_code == 200
    assert issued.json()["status"] == "issued"
    invoice_pdf = client.post(
        "/api/documents/preview",
        json={"document_type": "invoice", "entity_id": invoice["id"]},
    )
    assert invoice_pdf.status_code == 200
    assert invoice_pdf.content.startswith(b"%PDF-")
    assert PdfReader(BytesIO(invoice_pdf.content)).get_fields() is None
    locked_edit = client.patch(f"/api/invoices/{invoice['id']}", json=invoice_payload)
    assert locked_edit.status_code == 409

    payment = client.post(
        f"/api/invoices/{invoice['id']}/payments",
        json={
            "paid_at": "2026-11-01",
            "amount": "50.00",
            "method": "ACH",
            "reference": "P-1",
            "notes": "",
        },
    )
    assert payment.status_code == 201
    assert payment.json()["balance_due_cents"] == 78000
    overpayment = client.post(
        f"/api/invoices/{invoice['id']}/payments",
        json={
            "paid_at": "2026-11-02",
            "amount": "781.00",
            "method": "ACH",
            "reference": "P-2",
            "notes": "",
        },
    )
    assert overpayment.status_code == 422


def test_draft_booking_can_have_invoice_created_and_issued_without_acceptance(client) -> None:
    _profile(client)
    client_id = client.post("/api/clients", json={"legal_name": "Example Client"}).json()["id"]
    booking = client.post("/api/bookings", json=_booking_payload(client_id)).json()
    assert booking["status"] == "draft"

    invoice_date = date(2026, 10, 29)
    invoice_response = client.post(
        "/api/invoices",
        json={
            "booking_id": booking["id"],
            "invoice_date": invoice_date.isoformat(),
            "due_date": (invoice_date + timedelta(days=15)).isoformat(),
            "tax_mode": "none",
            "tax_rate": "0",
            "manual_tax": "0",
            "notes": "",
            "line_items": [
                {
                    "source_booking_line_item_id": booking["line_items"][0]["id"],
                    "source_expense_id": None,
                    "description": "Photography package",
                    "quantity": "1",
                    "unit": "package",
                    "unit_rate": "800.00",
                }
            ],
        },
    )

    assert invoice_response.status_code == 201, invoice_response.text
    invoice = invoice_response.json()
    assert invoice["record_status"] == "draft"
    assert invoice["total_cents"] == booking["subtotal_cents"]

    issued = client.post(f"/api/invoices/{invoice['id']}/issue")

    assert issued.status_code == 200, issued.text
    assert issued.json()["record_status"] == "issued"


def test_proposed_expense_is_not_invoice_eligible(client) -> None:
    _profile(client)
    client_id = client.post("/api/clients", json={"legal_name": "Example LLC"}).json()["id"]
    booking = client.post("/api/bookings", json=_booking_payload(client_id)).json()
    client.post(
        f"/api/bookings/{booking['id']}/accept",
        json={"accepted_date": "2026-10-28", "acceptance_reference": "Signed agreement"},
    )
    expense = client.post(
        f"/api/bookings/{booking['id']}/expenses",
        json={
            "description": "Equipment rental",
            "quantity": "1",
            "unit": "day",
            "unit_rate": "80.00",
            "authorization_status": "proposed",
            "authorization_date": None,
            "authorization_reference": "",
            "notes": "Awaiting approval",
        },
    ).json()
    detail = client.get(f"/api/bookings/{booking['id']}").json()
    lines = [
        {
            "source_booking_line_item_id": None,
            "source_expense_id": expense["id"],
            "description": "Equipment rental",
            "quantity": "1",
            "unit": "day",
            "unit_rate": "80.00",
        }
    ]
    response = client.post(
        "/api/invoices",
        json={
            "booking_id": booking["id"],
            "invoice_date": "2026-10-28",
            "due_date": "2026-11-12",
            "tax_mode": "none",
            "tax_rate": "0",
            "manual_tax": "0",
            "notes": "",
            "line_items": lines
            + [
                {
                    "source_booking_line_item_id": detail["line_items"][0]["id"],
                    "source_expense_id": None,
                    "description": "Corporate event photography package "
                    "(up to six hours; editing and delivery included)",
                    "quantity": "1",
                    "unit": "package",
                    "unit_rate": "800.00",
                }
            ],
        },
    )
    assert response.status_code == 422
