"""Signed booking confirmation uploads finalize bookings and preserve PDF versions."""

from backend.app.services import booking_signing, documents


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
                    "description": "Portrait package",
                    "quantity": "1",
                    "unit": "package",
                    "unit_rate": "500.00",
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_uploading_signed_confirmation_finalizes_and_keeps_prior_pdf(
    client, monkeypatch, tmp_path
) -> None:
    output_directory = tmp_path / "documents"
    monkeypatch.setattr(booking_signing, "DATA_DIR", tmp_path)
    monkeypatch.setattr(booking_signing, "DEFAULT_OUTPUT_DIR", output_directory)
    monkeypatch.setattr(documents, "DEFAULT_OUTPUT_DIR", output_directory)
    monkeypatch.setattr(documents, "render_pdf", lambda _kind, _context: b"%PDF-pending")
    booking = _new_booking(client)

    invalid = client.post(
        f"/api/bookings/{booking['id']}/signed-copy",
        params={"signed_date": "2026-11-05", "filename": "invalid.pdf"},
        content=b"not a PDF",
        headers={"content-type": "application/pdf"},
    )
    assert invalid.status_code == 422
    assert client.get(f"/api/bookings/{booking['id']}").json()["status"] == "draft"

    pending_document = client.post(
        "/api/documents/generate",
        json={"document_type": "booking_confirmation", "entity_id": booking["id"]},
    )
    assert pending_document.status_code == 201, pending_document.text
    assert pending_document.json()["status"] == "pending"

    upload = client.post(
        f"/api/bookings/{booking['id']}/signed-copy",
        params={"signed_date": "2026-11-05", "filename": "signed confirmation.pdf"},
        content=b"%PDF-signed-confirmation",
        headers={"content-type": "application/pdf"},
    )
    assert upload.status_code == 200, upload.text
    finalized = upload.json()
    assert finalized["status"] == "finalized"
    assert finalized["accepted_at"].startswith("2026-11-05")
    assert finalized["acceptance_reference"].startswith("Uploaded signed PDF:")

    saved_documents = client.get("/api/documents").json()
    booking_documents = [item for item in saved_documents if item["booking_id"] == booking["id"]]
    assert sorted(item["version"] for item in booking_documents) == [1, 2]
    signed_document = next(item for item in booking_documents if item["status"] == "final")
    assert signed_document["document_type"] == "booking_confirmation"
    assert signed_document["template_version"] == "signed-pdf-upload"
    assert (output_directory / signed_document["name"]).read_bytes() == b"%PDF-signed-confirmation"
    original_document = next(
        item for item in booking_documents if item["id"] == pending_document.json()["id"]
    )
    assert (output_directory / original_document["name"]).read_bytes() == b"%PDF-pending"

    late_upload = client.post(
        f"/api/bookings/{booking['id']}/signed-copy",
        params={"signed_date": "2026-11-05", "filename": "signed confirmation.pdf"},
        content=b"%PDF-another-signed-copy",
        headers={"content-type": "application/pdf"},
    )
    assert late_upload.status_code == 200, late_upload.text
    assert late_upload.json()["status"] == "finalized"
    assert late_upload.json()["accepted_at"] == finalized["accepted_at"]
    assert late_upload.json()["acceptance_reference"] == finalized["acceptance_reference"]
    all_documents = client.get("/api/documents").json()
    booking_documents = [item for item in all_documents if item["booking_id"] == booking["id"]]
    assert sorted(item["version"] for item in booking_documents) == [1, 2, 3]
    late_document = next(item for item in booking_documents if item["version"] == 3)
    assert late_document["status"] == "final"
    assert (output_directory / late_document["name"]).read_bytes() == b"%PDF-another-signed-copy"
