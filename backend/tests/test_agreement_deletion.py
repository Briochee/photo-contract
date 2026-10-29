"""Agreement deletion tests for unreferenced and booking-linked records."""


def _create_client_and_agreement(client) -> tuple[int, int]:
    profile = client.patch("/api/settings", json={"legal_name": "Photographer"})
    assert profile.status_code == 200
    client_response = client.post("/api/clients", json={"legal_name": "Example Client"})
    assert client_response.status_code == 201
    client_id = client_response.json()["id"]
    agreement_response = client.post(
        "/api/agreements",
        json={"client_id": client_id, "effective_date": "2026-10-29"},
    )
    assert agreement_response.status_code == 201
    return client_id, agreement_response.json()["id"]


def test_client_can_delete_unreferenced_master_agreement(client) -> None:
    _, agreement_id = _create_client_and_agreement(client)

    deleted = client.delete(f"/api/agreements/{agreement_id}")

    assert deleted.status_code == 204
    assert client.get(f"/api/agreements/{agreement_id}").status_code == 404


def test_master_agreement_cannot_be_deleted_while_a_booking_uses_it(client) -> None:
    client_id, agreement_id = _create_client_and_agreement(client)
    booking = client.post(
        "/api/bookings",
        json={
            "client_id": client_id,
            "agreement_id": agreement_id,
            "event_name": "Portrait session",
            "event_type": "Portrait",
            "event_date": "2026-12-01",
            "coverage_start": "09:00",
            "coverage_end": "10:00",
            "coverage_hours": "1",
            "line_items": [
                {"description": "Photography session", "quantity": "1", "unit_rate": "100"}
            ],
        },
    )
    assert booking.status_code == 201

    deleted = client.delete(f"/api/agreements/{agreement_id}")

    assert deleted.status_code == 409
    assert "linked to a booking" in deleted.json()["detail"]
    assert client.get(f"/api/agreements/{agreement_id}").status_code == 200
