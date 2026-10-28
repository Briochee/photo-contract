from decimal import Decimal

import pytest
from backend.app.services.pricing import calculate_line_item, calculate_totals, due_date


def test_line_item_supports_fractional_quantity_without_float_math() -> None:
    item = calculate_line_item("Retouching", "1.25", "80.00", "hour")

    assert item["quantity"] == "1.25"
    assert item["unit_rate_cents"] == 8000
    assert item["amount_cents"] == 10000


def test_totals_round_half_up_and_apply_rate_tax() -> None:
    items = [calculate_line_item("Coverage", "1", "12.345")]

    totals = calculate_totals(items, tax_mode="rate", tax_rate="8.25")

    assert totals.subtotal_cents == 1235
    assert totals.tax_cents == 102
    assert totals.total_cents == 1337


def test_manual_tax_and_no_tax_modes() -> None:
    items = [calculate_line_item("Coverage", "1", "100.00")]

    manual = calculate_totals(items, tax_mode="manual", manual_tax="7.50")
    untaxed = calculate_totals(items, tax_mode="none")

    assert manual.tax_cents == 750
    assert untaxed.tax_cents == 0


@pytest.mark.parametrize(
    ("quantity", "unit_rate"),
    [("0", "10.00"), ("1", "-0.01"), ("NaN", "10.00"), ("1.0001", "10.00")],
)
def test_line_item_rejects_invalid_quantity_or_rate(quantity: str, unit_rate: str) -> None:
    with pytest.raises(ValueError):
        calculate_line_item("Fee", quantity, unit_rate)


def test_line_item_rejects_binary_float_values() -> None:
    with pytest.raises(TypeError):
        calculate_line_item("Fee", "1", 0.1)  # type: ignore[arg-type]


def test_due_date_uses_calendar_days() -> None:
    assert due_date("2026-10-28", 15) == "2026-11-12"


def test_unapproved_expenses_cannot_be_added_to_totals() -> None:
    item = calculate_line_item("Travel", "1", "30.00")
    item["authorization_status"] = "proposed"

    with pytest.raises(ValueError, match="approved"):
        calculate_totals([item], tax_mode="none")


def test_results_are_integer_minor_units() -> None:
    item = calculate_line_item("Coverage", "1", "1.005")
    totals = calculate_totals([item])

    assert item["amount_cents"] == 101
    assert isinstance(totals.total_cents, int)
    assert Decimal(totals.total_cents) == 101
