"""Protect booking-confirmation status transitions and pre-acceptance invoices."""

from datetime import date, timedelta


def _new_booking(client) -> dict:
    profile = client.patch("/api/settings", json={"legal_name": "Studio Photographer"})
    assert profile.status_code == 200
    client_record = client.post("/api/clients", json={"legal_name": "Example Client"})
    assert client_record.status_code == 201
    response = client.post(
        "/api/bookings",
        json={
            "client_id": client_record.json()["id"],
            "event_name": "Portrait session",
            "event_type": "Portrait",
            "event_date": "2026-11-20",
            "line_items": [
                {
                    "description": "Portrait session",
                    "quantity": "1",
                    "unit": "session",
                    "unit_rate": "250.00",
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_booking_confirmation_moves_pending_and_invoice_is_available_before_acceptance(
    client, tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr("backend.app.services.documents.DEFAULT_OUTPUT_DIR", tmp_path / "documents")
    monkeypatch.setattr(
        "backend.app.services.documents.render_pdf",
        lambda _document_type, _context: b"%PDF-test",
    )
    booking = _new_booking(client)
    assert booking["status"] == "draft"

    confirmation = client.post(
        "/api/documents/generate",
        json={"document_type": "booking_confirmation", "entity_id": booking["id"]},
    )

    assert confirmation.status_code == 201, confirmation.text
    assert confirmation.json()["status"] == "pending"
    pending = client.get(f"/api/bookings/{booking['id']}").json()
    assert pending["status"] == "pending"

    invoice_date = date(2026, 10, 29)
    line = pending["line_items"][0]
    invoice = client.post(
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
                    "source_booking_line_item_id": line["id"],
                    "source_expense_id": None,
                    "description": line["description"],
                    "quantity": line["quantity"],
                    "unit": line["unit"],
                    "unit_rate": line["unit_rate"],
                }
            ],
        },
    )
    assert invoice.status_code == 201, invoice.text
    assert invoice.json()["record_status"] == "draft"

    finalized = client.post(
        f"/api/bookings/{booking['id']}/accept",
        json={
            "accepted_date": "2026-10-29",
            "acceptance_reference": "Signed booking confirmation",
        },
    )

    assert finalized.status_code == 200, finalized.text
    assert finalized.json()["status"] == "finalized"


def test_unaccepted_pending_booking_can_be_deleted_without_deleting_saved_pdf(
    client, tmp_path, monkeypatch
) -> None:
    output_directory = tmp_path / "documents"
    monkeypatch.setattr("backend.app.services.documents.DEFAULT_OUTPUT_DIR", output_directory)
    monkeypatch.setattr(
        "backend.app.services.documents.render_pdf",
        lambda _document_type, _context: b"%PDF-test",
    )
    booking = _new_booking(client)
    document = client.post(
        "/api/documents/generate",
        json={"document_type": "booking_confirmation", "entity_id": booking["id"]},
    )
    assert document.status_code == 201

    deleted = client.delete(f"/api/bookings/{booking['id']}")

    assert deleted.status_code == 204
    saved_document = client.get(f"/api/documents/{document.json()['id']}").json()
    assert saved_document["booking_id"] is None
    assert (output_directory / document.json()["name"]).is_file()
