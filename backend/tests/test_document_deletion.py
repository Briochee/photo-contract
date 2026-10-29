"""Verify document-library deletion removes both metadata and local PDF files."""


def test_delete_document_removes_pdf_and_library_record(client, tmp_path, monkeypatch) -> None:
    output_dir = tmp_path / "documents"
    output_dir.mkdir()
    monkeypatch.setattr("backend.app.api.documents.DEFAULT_OUTPUT_DIR", output_dir)
    monkeypatch.setattr("backend.app.services.documents.DEFAULT_OUTPUT_DIR", output_dir)
    monkeypatch.setattr(
        "backend.app.services.documents.render_pdf",
        lambda _document_type, _context: b"%PDF-test",
    )

    profile = client.patch(
        "/api/settings",
        json={"legal_name": "Riley Doe", "mailing_address": "10 Studio Lane"},
    )
    assert profile.status_code == 200
    client_record = client.post("/api/clients", json={"legal_name": "Jordan Lee"})
    assert client_record.status_code == 201
    agreement = client.post(
        "/api/agreements",
        json={"client_id": client_record.json()["id"], "effective_date": "2026-10-29"},
    )
    assert agreement.status_code == 201
    generated = client.post(
        "/api/documents/generate",
        json={"document_type": "agreement", "entity_id": agreement.json()["id"]},
    )
    assert generated.status_code == 201
    pdf_path = output_dir / generated.json()["name"]
    assert pdf_path.is_file()

    deleted = client.delete(f"/api/documents/{generated.json()['id']}")

    assert deleted.status_code == 204
    assert not pdf_path.exists()
    assert client.get(f"/api/documents/{generated.json()['id']}").status_code == 404
    assert client.get("/api/documents").json() == []
