"""Protect the source agreement wording and keep internal notes out of agreement PDFs."""

from backend.app.api.agreements import agreement_text
from backend.app.config import LEGAL_SOURCE
from backend.app.services.documents import _JINJA, _substitute_header_lines


def test_agreement_source_is_preserved_and_separated_from_other_material() -> None:
    complete_source = LEGAL_SOURCE.read_text(encoding="utf-8")
    expected = complete_source.split("\n---\n", maxsplit=1)[0].rstrip() + "\n"
    actual = agreement_text()

    assert actual == expected
    assert all(f"## {section}." in actual for section in range(1, 17))
    assert "BOOKING CONFIRMATION — SEPARATE PAGE" not in actual
    assert "Internal checklist" not in actual


def test_agreement_header_aliases_populate_party_fields() -> None:
    source = "\n".join(
        [
            "**Effective Date:** [Date]",
            "**Photographer:** [Legal Name/Company Name]",
            "**Address:** [Address]",
            "**Email:** [Email]",
            "**Client:** [Legal Entity Name]",
            "**Address:** [Address]",
            "**Authorized Representative:** [Name/Title]",
            "**Email:** [Email]",
        ]
    )
    source_snapshot = {
        "effective_date": "2026-10-29",
        "photographer": {
            "legal_name": "Riley Doe",
            "business_name": "Northlight Photo",
            "mailing_address": "10 Studio Lane",
            "email": "riley@example.test",
        },
        "client": {
            "legal_name": "Jordan Lee",
            "mailing_address": "20 Client Road",
            "primary_contact_name": "Jordan Lee",
            "primary_contact_title": "Client",
            "contact_email": "jordan@example.test",
        },
    }

    populated = _substitute_header_lines(source, source_snapshot)

    assert "2026-10-29" in populated
    assert "Riley Doe / Northlight Photo" in populated
    assert "10 Studio Lane" in populated
    assert "riley@example.test" in populated
    assert "Jordan Lee" in populated
    assert "20 Client Road" in populated
    assert "Jordan Lee / Client" in populated
    assert "jordan@example.test" in populated
    assert "[Date]" not in populated
    assert "[Address]" not in populated
    assert "[Email]" not in populated
    assert "[Legal Name/Company Name]" not in populated
    assert "[Name/Title]" not in populated


def test_master_agreement_preview_uses_saved_client_and_photographer_fields(
    client, monkeypatch
) -> None:
    rendered_context: dict[str, object] = {}
    rendered_html: dict[str, str] = {}

    def render_without_browser(document_type: str, context: dict[str, object]) -> bytes:
        assert document_type == "agreement"
        rendered_context.update(context)
        rendered_html["html"] = _JINJA.get_template("agreement.html").render(**context)
        return b"%PDF preview"

    monkeypatch.setattr("backend.app.api.documents.render_pdf", render_without_browser)
    profile = client.patch(
        "/api/settings",
        json={
            "legal_name": "Riley Doe",
            "business_name": "Northlight Photo",
            "mailing_address": "10 Studio Lane",
            "email": "riley@example.test",
        },
    )
    assert profile.status_code == 200
    client_record = client.post(
        "/api/clients",
        json={
            "legal_name": "Jordan Lee",
            "mailing_address": "20 Client Road",
            "primary_contact_name": "Jordan Lee",
            "primary_contact_title": "Client",
            "contact_email": "jordan@example.test",
        },
    )
    assert client_record.status_code == 201
    agreement = client.post(
        "/api/agreements",
        json={"client_id": client_record.json()["id"], "effective_date": "2026-10-29"},
    )
    assert agreement.status_code == 201

    preview = client.post(
        "/api/documents/preview",
        json={"document_type": "agreement", "entity_id": agreement.json()["id"]},
    )

    assert preview.status_code == 200
    assert preview.headers["content-type"] == "application/pdf"
    legal_html = str(rendered_context["legal_html"])
    assert "Riley Doe / Northlight Photo" in legal_html
    assert "10 Studio Lane" in legal_html
    assert "riley@example.test" in legal_html
    assert "Jordan Lee" in legal_html
    assert "20 Client Road" in legal_html
    assert "Jordan Lee / Client" in legal_html
    assert "jordan@example.test" in legal_html
    assert "[Date]" not in legal_html
    assert "[Address]" not in legal_html
    assert "[Email]" not in legal_html
    assert "[object Object]" not in rendered_html["html"]


def test_booking_confirmation_preview_renders_reference_and_event_fields(
    client, monkeypatch
) -> None:
    rendered_html: dict[str, str] = {}

    def render_without_browser(document_type: str, context: dict[str, object]) -> bytes:
        assert document_type == "booking_confirmation"
        rendered_html["html"] = _JINJA.get_template("booking.html").render(**context)
        return b"%PDF preview"

    monkeypatch.setattr("backend.app.api.documents.render_pdf", render_without_browser)
    profile = client.patch(
        "/api/settings",
        json={"legal_name": "Riley Doe", "email": "riley@example.test"},
    )
    assert profile.status_code == 200
    client_record = client.post("/api/clients", json={"legal_name": "Jordan Lee"})
    assert client_record.status_code == 201
    booking = client.post(
        "/api/bookings",
        json={
            "client_id": client_record.json()["id"],
            "agreement_id": None,
            "event_name": "Wedding portraits",
            "event_type": "Wedding",
            "event_date": "2026-11-20",
            "venue": "Riverside Garden",
            "venue_address": "10 River Road",
            "coverage_start": "09:00",
            "coverage_end": "15:00",
            "coverage_hours": "6",
            "scope": "Ceremony and portraits",
            "delivery_method": "Online gallery",
            "delivery_deadline": "Within ten business days after the event",
            "special_deliverables": "",
            "guaranteed_image_count": None,
            "overtime_rate": "150.00",
            "payment_terms_days": 15,
            "exceptions": "",
            "line_items": [
                {
                    "description": "Wedding photography",
                    "quantity": "1",
                    "unit": "package",
                    "unit_rate": "1200.00",
                    "category": "photography",
                }
            ],
            "additional_expenses": [],
        },
    )
    assert booking.status_code == 201

    preview = client.post(
        "/api/documents/preview",
        json={"document_type": "booking_confirmation", "entity_id": booking.json()["id"]},
    )

    assert preview.status_code == 200
    assert preview.headers["content-type"] == "application/pdf"
    assert "BK-2026-001" in rendered_html["html"]
    assert "Wedding portraits" in rendered_html["html"]
    assert "Riverside Garden" in rendered_html["html"]
    assert "[object Object]" not in rendered_html["html"]
