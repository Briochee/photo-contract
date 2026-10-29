"""Keep the agreement's recorded effective date tied to its last signature."""


def test_acceptance_records_last_signature_date_as_agreement_date(
    client, tmp_path, monkeypatch
) -> None:
    profile = client.patch("/api/settings", json={"legal_name": "Riley Doe"})
    assert profile.status_code == 200
    client_record = client.post("/api/clients", json={"legal_name": "Jordan Lee"})
    assert client_record.status_code == 201
    agreement = client.post(
        "/api/agreements",
        json={"client_id": client_record.json()["id"], "effective_date": "2026-10-29"},
    )
    assert agreement.status_code == 201
    assert agreement.json()["status"] == "draft"

    accepted = client.post(
        f"/api/agreements/{agreement.json()['id']}/accept",
        json={
            "accepted_date": "2026-11-02",
            "acceptance_reference": "Signed copy stored in client records",
        },
    )

    assert accepted.status_code == 200
    assert accepted.json()["effective_date"] == "2026-11-02"
    assert accepted.json()["template_version"] == "1.1.0"

    output_dir = tmp_path / "documents"
    monkeypatch.setattr("backend.app.services.documents.DEFAULT_OUTPUT_DIR", output_dir)
    monkeypatch.setattr(
        "backend.app.services.documents.render_pdf",
        lambda _document_type, _context: b"%PDF-test",
    )
    document = client.post(
        "/api/documents/generate",
        json={"document_type": "agreement", "entity_id": agreement.json()["id"]},
    )

    assert document.status_code == 201
    assert document.json()["template_version"] == "1.1.0"
