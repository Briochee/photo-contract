"""Protect the source agreement wording and keep internal notes out of agreement PDFs."""

from backend.app.api.agreements import agreement_text
from backend.app.config import LEGAL_SOURCE


def test_agreement_source_is_preserved_and_separated_from_other_material() -> None:
    complete_source = LEGAL_SOURCE.read_text(encoding="utf-8")
    expected = complete_source.split("\n---\n", maxsplit=1)[0].rstrip() + "\n"
    actual = agreement_text()

    assert actual == expected
    assert all(f"## {section}." in actual for section in range(1, 17))
    assert "BOOKING CONFIRMATION — SEPARATE PAGE" not in actual
    assert "Internal checklist" not in actual
