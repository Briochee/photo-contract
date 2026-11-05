"""Client detail response tests for agreement finalization evidence."""

from backend.app.services import agreement_signing


def test_uploaded_signed_copy_is_returned_in_client_detail(client, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(agreement_signing, "DATA_DIR", tmp_path)
    monkeypatch.setattr(agreement_signing, "DEFAULT_OUTPUT_DIR", tmp_path / "documents")

    profile = client.patch("/api/settings", json={"legal_name": "Studio Photographer"})
    assert profile.status_code == 200
    client_record = client.post("/api/clients", json={"legal_name": "Example Client"})
    assert client_record.status_code == 201
    client_id = client_record.json()["id"]
    agreement = client.post("/api/agreements", json={"client_id": client_id})
    assert agreement.status_code == 201
    agreement_id = agreement.json()["id"]

    upload = client.post(
        f"/api/agreements/{agreement_id}/signed-copy",
        params={"signed_date": "2026-11-05", "filename": "signed agreement.pdf"},
        content=b"%PDF-test",
        headers={"content-type": "application/pdf"},
    )
    assert upload.status_code == 200, upload.text
    assert upload.json()["acceptance_reference"].startswith("Uploaded signed PDF:")

    detail = client.get(f"/api/clients/{client_id}")
    assert detail.status_code == 200
    assert detail.json()["agreements"][0]["acceptance_reference"].startswith("Uploaded signed PDF:")

    finalized = upload.json()
    late_upload = client.post(
        f"/api/agreements/{agreement_id}/signed-copy",
        params={"signed_date": "2026-11-05", "filename": "signed agreement v2.pdf"},
        content=b"%PDF-late-signed-copy",
        headers={"content-type": "application/pdf"},
    )
    assert late_upload.status_code == 200, late_upload.text
    assert late_upload.json()["status"] == "finalized"
    assert late_upload.json()["effective_date"] == finalized["effective_date"]
    assert late_upload.json()["accepted_at"] == finalized["accepted_at"]
    assert late_upload.json()["acceptance_reference"] == finalized["acceptance_reference"]
    documents = client.get("/api/documents").json()
    agreement_documents = [
        item for item in documents if item["reference"] == agreement.json()["agreement_ref"]
    ]
    assert sorted(item["version"] for item in agreement_documents) == [1, 2]
    assert all(item["status"] == "final" for item in agreement_documents)
