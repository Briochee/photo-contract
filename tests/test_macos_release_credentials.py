"""Notarized release packaging stops before building when credentials are incomplete."""

from scripts.build_macos_app import (
    NOTARIZATION_CREDENTIALS,
    release_credentials_missing,
)


def test_release_credential_gate_lists_only_missing_names() -> None:
    complete = {name: "configured" for name in NOTARIZATION_CREDENTIALS}
    assert release_credentials_missing(complete) == []
    assert release_credentials_missing({"CSC_LINK": "configured"}) == [
        "CSC_KEY_PASSWORD",
        "APPLE_API_KEY",
        "APPLE_API_KEY_ID",
        "APPLE_API_ISSUER",
    ]
