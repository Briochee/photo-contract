"""Exercise local agreement-template updates and immutable agreement snapshots."""


def test_custom_template_is_snapshotted_reset_and_rendered_without_images(
    client, tmp_path, monkeypatch
) -> None:
    template_path = tmp_path / "master_agreement_template.md"
    monkeypatch.setattr(
        "backend.app.services.agreement_templates.ACTIVE_AGREEMENT_TEMPLATE", template_path
    )

    initial = client.get("/api/settings/agreement-template")
    assert initial.status_code == 200
    assert initial.json()["source"] == "bundled"

    profile = client.patch("/api/settings", json={"legal_name": "Riley Doe"})
    assert profile.status_code == 200
    client_record = client.post("/api/clients", json={"legal_name": "Jordan Lee"})
    assert client_record.status_code == 201

    custom_markdown = (
        "# Custom agreement\n\n"
        "Client: {{client_legal_name}}\n\n"
        "![remote seal](https://example.invalid/seal.png)\n\n"
        "## Signatures\n"
    )
    saved = client.put(
        "/api/settings/agreement-template", json={"content": custom_markdown}
    )
    assert saved.status_code == 200
    assert saved.json()["source"] == "custom"
    assert saved.json()["content"] == custom_markdown.rstrip("\n")

    agreement = client.post(
        "/api/agreements", json={"client_id": client_record.json()["id"]}
    )
    assert agreement.status_code == 201
    assert agreement.json()["template_version"] == saved.json()["template_version"]

    replacement = client.put(
        "/api/settings/agreement-template",
        json={"content": "# Replacement agreement\n\n## Signatures\n"},
    )
    assert replacement.status_code == 200

    rendered: dict[str, object] = {}

    def render_without_browser(_document_type: str, context: dict[str, object]) -> bytes:
        rendered.update(context)
        return b"%PDF preview"

    monkeypatch.setattr("backend.app.api.documents.render_pdf", render_without_browser)
    preview = client.post(
        "/api/documents/preview",
        json={"document_type": "agreement", "entity_id": agreement.json()["id"]},
    )
    assert preview.status_code == 200
    legal_html = str(rendered["legal_html"])
    assert "Jordan Lee" in legal_html
    assert "Replacement agreement" not in legal_html
    assert "example.invalid" not in legal_html
    assert "<img" not in legal_html

    reset = client.delete("/api/settings/agreement-template")
    assert reset.status_code == 200
    assert reset.json()["source"] == "bundled"
    assert template_path.exists() is False


def test_empty_custom_template_is_rejected_without_replacing_active_template(
    client, tmp_path, monkeypatch
) -> None:
    template_path = tmp_path / "master_agreement_template.md"
    monkeypatch.setattr(
        "backend.app.services.agreement_templates.ACTIVE_AGREEMENT_TEMPLATE", template_path
    )

    saved = client.put(
        "/api/settings/agreement-template", json={"content": "# Usable agreement"}
    )
    assert saved.status_code == 200

    rejected = client.put("/api/settings/agreement-template", json={"content": "   "})
    assert rejected.status_code == 422
    current = client.get("/api/settings/agreement-template")
    assert current.status_code == 200
    assert current.json()["content"] == saved.json()["content"]
