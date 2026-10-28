"""Exact monetary calculations for bookings and invoices."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
QUANTITY_STEP = Decimal("0.001")


@dataclass(frozen=True)
class InvoiceTotals:
    subtotal_cents: int
    tax_cents: int
    total_cents: int


def calculate_line_item(
    description: str,
    quantity: str,
    unit_rate: str,
    unit: str = "service",
) -> dict[str, object]:
    label = str(description).strip()
    if not label:
        raise ValueError("Line item description is required")
    if len(label) > 300:
        raise ValueError("Line item description must be 300 characters or fewer")

    parsed_quantity = _parse_decimal(quantity, "quantity")
    if parsed_quantity <= 0:
        raise ValueError("Line item quantity must be positive")
    normalized_quantity = parsed_quantity.quantize(QUANTITY_STEP, rounding=ROUND_HALF_UP)
    if normalized_quantity != parsed_quantity:
        raise ValueError("Line item quantity supports at most three decimal places")

    parsed_rate = _parse_decimal(unit_rate, "unit rate")
    if parsed_rate < 0:
        raise ValueError("Line item rate cannot be negative")
    rate_cents = int(parsed_rate.quantize(CENT, rounding=ROUND_HALF_UP) * 100)
    amount_cents = int(
        (normalized_quantity * Decimal(rate_cents) / 100).quantize(CENT, rounding=ROUND_HALF_UP)
        * 100
    )

    normalized_unit = str(unit).strip() or "service"
    if len(normalized_unit) > 40:
        raise ValueError("Line item unit must be 40 characters or fewer")

    return {
        "description": label,
        "quantity": _decimal_text(normalized_quantity),
        "unit": normalized_unit,
        "unit_rate_cents": rate_cents,
        "amount_cents": amount_cents,
    }


def calculate_totals(
    items: Iterable[dict[str, object]],
    *,
    tax_mode: str = "none",
    tax_rate: str = "0",
    manual_tax: str = "0",
) -> InvoiceTotals:
    normalized_items = list(items)
    subtotal = 0
    for item in normalized_items:
        authorization = item.get("authorization_status")
        if authorization is not None and authorization != "approved":
            raise ValueError("Only approved additional expenses can be billed")
        amount = item.get("amount_cents")
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise ValueError("Line item amount must be a nonnegative integer number of cents")
        subtotal += amount

    if tax_mode == "none":
        tax_cents = 0
    elif tax_mode == "rate":
        rate = _parse_decimal(tax_rate, "tax rate")
        if rate < 0 or rate > 100:
            raise ValueError("Tax rate must be between 0 and 100 percent")
        tax_cents = int(
            (Decimal(subtotal) * rate / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )
    elif tax_mode == "manual":
        tax_cents = money_to_cents(manual_tax, "manual tax")
    else:
        raise ValueError("Tax mode must be none, rate, or manual")

    return InvoiceTotals(
        subtotal_cents=subtotal, tax_cents=tax_cents, total_cents=subtotal + tax_cents
    )


def due_date(invoice_date: str, net_days: int) -> str:
    if isinstance(net_days, bool) or not isinstance(net_days, int) or not 0 <= net_days <= 365:
        raise ValueError("Payment terms must be between 0 and 365 calendar days")
    return (date.fromisoformat(invoice_date) + timedelta(days=net_days)).isoformat()


def money_to_cents(value: str | Decimal | int, label: str = "amount") -> int:
    """Convert a decimal amount to exact integer cents using half-up rounding."""
    amount = _parse_decimal(value, label)
    if amount < 0:
        raise ValueError(f"{label.capitalize()} cannot be negative")
    return int(amount.quantize(CENT, rounding=ROUND_HALF_UP) * 100)


def _parse_decimal(value: str | Decimal | int, label: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError(f"{label.capitalize()} must be provided as a decimal string or Decimal")
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid {label}: {value!r}") from exc
    if not parsed.is_finite():
        raise ValueError(f"{label.capitalize()} must be finite")
    return parsed


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    return format(normalized, "f") if normalized else "0"
