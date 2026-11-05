"""Release version checks prevent stale or inconsistent macOS releases."""

import pytest

from scripts.check_release_version import (
    latest_release_version,
    validate_release_version,
)


def test_first_release_is_allowed_when_there_are_no_version_tags() -> None:
    assert validate_release_version("1.0.0", "1.0.0", "1.0.0", []) == "1.0.0"


def test_version_must_be_newer_than_the_latest_release_tag() -> None:
    assert (
        validate_release_version("1.2.0", "1.2.0", "1.2.0", ["v1.0.0", "v1.1.4"])
        == "1.2.0"
    )
    assert latest_release_version(["unrelated", "1.2.0", "v1.10.0"]) == (1, 10, 0)


@pytest.mark.parametrize("version", ["1.1.0", "1.2.0"])
def test_equal_or_older_release_versions_are_rejected(version: str) -> None:
    with pytest.raises(ValueError, match="Increment frontend/package.json"):
        validate_release_version(version, version, version, ["v1.2.0"])


def test_npm_lockfile_must_match_the_application_version() -> None:
    with pytest.raises(ValueError, match="package-lock.json must match"):
        validate_release_version("1.2.0", "1.1.0", "1.1.0", ["v1.0.0"])


def test_prerelease_or_malformed_versions_are_rejected() -> None:
    with pytest.raises(ValueError, match="stable semantic version"):
        validate_release_version("1.3.0-rc.1", "1.3.0-rc.1", "1.3.0-rc.1", [])
