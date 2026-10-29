"""Settings API regressions for empty and incomplete photographer profiles."""


def test_settings_load_without_existing_profile_returns_optional_defaults(client) -> None:
    response = client.get("/api/settings")

    assert response.status_code == 200
    profile = response.json()["profile"]
    assert profile["business_name"] is None
    assert profile["default_payment_terms_days"] is None
    assert profile["default_photography_rate"] is None
    assert profile["default_overtime_rate"] is None
    assert profile["default_delivery_method"] is None
    assert profile["default_delivery_deadline"] is None


def test_profile_saves_without_optional_company_or_defaults(client) -> None:
    response = client.patch(
        "/api/settings",
        json={
            "legal_name": "Riley Photographer",
            "business_name": "",
        },
    )

    assert response.status_code == 200
    profile = response.json()["profile"]
    assert profile["legal_name"] == "Riley Photographer"
    assert profile["business_name"] is None
    assert profile["default_payment_terms_days"] is None
    assert profile["default_photography_rate"] is None
    assert profile["default_overtime_rate"] is None
    assert profile["default_delivery_method"] is None
    assert profile["default_delivery_deadline"] is None

    persisted = client.get("/api/settings")
    assert persisted.status_code == 200
    assert persisted.json()["profile"] == profile
