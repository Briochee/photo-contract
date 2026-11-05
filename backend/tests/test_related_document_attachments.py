"""Related file uploads remain attached without changing finalized business records."""

from datetime import date, timedelta

from backend.app.services import uploaded_documents


def test_related_files_attach_to_final_agreement_booking_and_invoice(
    client, monkeypatch, tmp_path
) -> None:
    output_directory = tmp_path / "documents"
    monkeypatch.setattr(uploaded_documents, "DATA_DIR", tmp_path)
    monkeypatch.setattr(uploaded_documents, "DEFAULT_OUTPUT_DIR", output_directory)
    monkeypatch.setattr("backend.app.api.documents.DEFAULT_OUTPUT_DIR", output_directory)

    profile = client.patch("/api/settings", json={"legal_name": "Studio Photographer"})
    assert profile.status_code == 200
    client_record = client.post("/api/clients", json={"legal_name": "Example Client"})
    assert client_record.status_code == 201
    client_id = client_record.json()["id"]

    agreement_response = client.post("/api/agreements", json={"client_id": client_id})
    assert agreement_response.status_code == 201, agreement_response.text
    agreement_id = agreement_response.json()["id"]
    agreement_final = client.post(
        f"/api/agreements/{agreement_id}/finalize",
        json={"signed_date": "2026-11-05", "evidence_reference": "Confirmed by email"},
    )
    assert agreement_final.status_code == 200, agreement_final.text

    booking_response = client.post(
        "/api/bookings",
        json={
            "client_id": client_id,
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
    assert booking_response.status_code == 201, booking_response.text
    booking = booking_response.json()
    booking_final = client.post(
        f"/api/bookings/{booking['id']}/accept",
        json={
            "accepted_date": "2026-11-05",
            "acceptance_reference": "Confirmation email",
        },
    )
    assert booking_final.status_code == 200, booking_final.text

    invoice_date = date(2026, 11, 5)
    line = booking["line_items"][0]
    invoice_response = client.post(
        "/api/invoices",
        json={
            "booking_id": booking["id"],
            "invoice_date": invoice_date.isoformat(),
            "due_date": (invoice_date + timedelta(days=15)).isoformat(),
            "tax_mode": "none",
            "line_items": [
                {
                    "source_booking_line_item_id": line["id"],
                    "description": line["description"],
                    "quantity": line["quantity"],
                    "unit": line["unit"],
                    "unit_rate": line["unit_rate"],
                }
            ],
        },
    )
    assert invoice_response.status_code == 201, invoice_response.text
    invoice = invoice_response.json()
    issued = client.post(f"/api/invoices/{invoice['id']}/issue")
    assert issued.status_code == 200, issued.text

    attachments = [
        ("agreement", agreement_id, b"%PDF-signed-contract", "signed-contract.pdf"),
        ("booking", booking["id"], b"%PDF-signed-confirmation", "confirmation.pdf"),
        ("invoice", invoice["id"], b"%PDF-invoice-copy", "invoice-copy.pdf"),
    ]
    uploaded = []
    for entity_type, entity_id, content, filename in attachments:
        response = client.post(
            "/api/documents/attach",
            params={"entity_type": entity_type, "entity_id": entity_id, "filename": filename},
            content=content,
            headers={"content-type": "application/pdf"},
        )
        assert response.status_code == 201, response.text
        uploaded.append(response.json())

    expected_references = [
        agreement_response.json()["agreement_ref"],
        booking["booking_ref"],
        invoice["invoice_ref"],
    ]
    for item, (entity_type, entity_id, content, _filename), reference in zip(
        uploaded, attachments, expected_references, strict=True
    ):
        assert item["document_type"] == "uploaded_file"
        assert item["related_entity_type"] == entity_type
        assert item["related_entity_id"] == entity_id
        assert item["related_reference"] == reference
        downloaded = client.get(f"/api/documents/{item['id']}/download")
        assert downloaded.status_code == 200
        assert downloaded.content == content

    assert client.get(f"/api/agreements/{agreement_id}").json()["status"] == "finalized"
    assert client.get(f"/api/bookings/{booking['id']}").json()["status"] == "finalized"
    final_invoice = client.get(f"/api/invoices/{invoice['id']}").json()
    assert final_invoice["record_status"] == "issued"
    assert final_invoice["total_cents"] == issued.json()["total_cents"]

    draft_booking_response = client.post(
        "/api/bookings",
        json={
            "client_id": client_id,
            "event_name": "Unaccepted session",
            "event_type": "Portrait",
            "event_date": "2026-12-01",
            "line_items": [
                {
                    "description": "Portrait package",
                    "quantity": "1",
                    "unit": "package",
                    "unit_rate": "250.00",
                }
            ],
        },
    )
    assert draft_booking_response.status_code == 201, draft_booking_response.text
    draft_booking = draft_booking_response.json()
    draft_attachment = client.post(
        "/api/documents/attach",
        params={
            "entity_type": "booking",
            "entity_id": draft_booking["id"],
            "filename": "draft-reference.pdf",
        },
        content=b"%PDF-draft-reference",
        headers={"content-type": "application/pdf"},
    )
    assert draft_attachment.status_code == 201, draft_attachment.text

    deleted = client.delete(f"/api/bookings/{draft_booking['id']}")

    assert deleted.status_code == 204
    detached = client.get(f"/api/documents/{draft_attachment.json()['id']}").json()
    assert detached["related_entity_type"] is None
    assert detached["related_entity_id"] is None
    assert detached["related_reference"] is None
    assert (
        client.get(f"/api/documents/{detached['id']}/download").content == b"%PDF-draft-reference"
    )

    removable_agreement = client.post("/api/agreements", json={"client_id": client_id})
    assert removable_agreement.status_code == 201
    removable_agreement_id = removable_agreement.json()["id"]
    agreement_attachment = client.post(
        "/api/documents/attach",
        params={
            "entity_type": "agreement",
            "entity_id": removable_agreement_id,
            "filename": "agreement-reference.pdf",
        },
        content=b"%PDF-agreement-reference",
        headers={"content-type": "application/pdf"},
    )
    assert agreement_attachment.status_code == 201
    deleted_agreement = client.delete(f"/api/agreements/{removable_agreement_id}")
    assert deleted_agreement.status_code == 204
    detached_agreement_file = client.get(
        f"/api/documents/{agreement_attachment.json()['id']}"
    ).json()
    assert detached_agreement_file["related_entity_type"] is None
    assert detached_agreement_file["related_entity_id"] is None
    assert (
        client.get(f"/api/documents/{detached_agreement_file['id']}/download").content
        == b"%PDF-agreement-reference"
    )
