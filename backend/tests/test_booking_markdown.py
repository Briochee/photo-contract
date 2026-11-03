"""Booking confirmation Markdown rendering and escaping behavior."""

from backend.app.api import documents as documents_api
from backend.app.services.documents import _JINJA


def test_booking_confirmation_renders_common_markdown_safely(client, monkeypatch) -> None:
    client_response = client.post(
        "/api/clients",
        json={
            "legal_name": "Markdown Client",
            "primary_contact_name": "Jordan Lee",
            "contact_email": "jordan@example.test",
        },
    )
    assert client_response.status_code == 201

    booking_response = client.post(
        "/api/bookings",
        json={
            "client_id": client_response.json()["id"],
            "event_name": "Portrait session",
            "event_type": "Portrait",
            "event_date": "2026-11-20",
            "coverage_hours": "2",
            "scope": (
                "Create **natural portraits** with *soft light*.\n\n"
                "- Capture individual portraits\n- Include a small group portrait\n\n"
                "<script>alert('unsafe')</script>\n\n"
                "![remote image](https://external.invalid/image.png)"
            ),
            "special_deliverables": (
                "**Final selection**\n\n| Set | Count |\n|---|---:|\n| Edited portraits | 3 |"
            ),
            "exceptions": "Section 6: **Use is limited** to the agreed campaign.",
            "line_items": [
                {
                    "description": "**Portrait** package",
                    "quantity": "1",
                    "unit": "package",
                    "unit_rate": "500.00",
                }
            ],
            "additional_expenses": [
                {
                    "description": "Parking",
                    "quantity": "1",
                    "unit": "day",
                    "unit_rate": "25.00",
                    "authorization_status": "approved",
                    "authorization_date": "2026-10-28",
                    "authorization_reference": "Client email",
                    "notes": (
                        "Keep the *receipt* with the invoice. "
                        "![receipt](https://external.invalid/receipt.png)"
                    ),
                },
                {
                    "description": "Unapproved equipment rental",
                    "quantity": "1",
                    "unit": "day",
                    "unit_rate": "100.00",
                    "authorization_status": "proposed",
                    "notes": "This **proposed note** must stay off the confirmation.",
                },
            ],
        },
    )
    assert booking_response.status_code == 201, booking_response.text

    captured: dict[str, str] = {}

    def render_preview(_document_type: str, context: dict) -> bytes:
        captured["html"] = _JINJA.get_template("booking.html").render(**context)
        return b"%PDF-test"

    monkeypatch.setattr(documents_api, "render_pdf", render_preview)
    preview = client.post(
        "/api/documents/preview",
        json={
            "document_type": "booking_confirmation",
            "entity_id": booking_response.json()["id"],
        },
    )
    assert preview.status_code == 200, preview.text
    assert preview.content == b"%PDF-test"

    rendered = captured["html"]
    assert "<strong>natural portraits</strong>" in rendered
    assert "<em>soft light</em>" in rendered
    assert "<ul>" in rendered
    assert "<strong>Final selection</strong>" in rendered
    assert "<th>Set</th>" in rendered
    assert "<strong>Portrait</strong> package" in rendered
    assert "<strong>Use is limited</strong>" in rendered
    assert "<em>receipt</em>" in rendered
    assert "&lt;script&gt;" in rendered
    assert "<script>" not in rendered
    assert "external.invalid" not in rendered
    assert "<img" not in rendered
    assert "proposed note" not in rendered
