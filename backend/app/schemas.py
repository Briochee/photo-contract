"""Validated API contracts; monetary input is always represented as a decimal string."""

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class APIModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ClientInput(APIModel):
    legal_name: str = Field(min_length=1, max_length=200)
    display_name: str | None = Field(default=None, max_length=200)
    mailing_address: str = Field(default="", max_length=4000)
    primary_contact_name: str = Field(default="", max_length=160)
    primary_contact_title: str = Field(default="", max_length=160)
    contact_email: str = Field(default="", max_length=254)
    contact_phone: str = Field(default="", max_length=80)
    notes: str = Field(default="", max_length=10000)

    @field_validator("contact_email")
    @classmethod
    def valid_optional_email(cls, value: str) -> str:
        if value and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Enter a valid email address")
        return value


class LineItemInput(APIModel):
    description: str = Field(min_length=1, max_length=300)
    quantity: str = Field(default="1", max_length=24)
    unit: str = Field(default="service", max_length=40)
    unit_rate: str = Field(default="0", max_length=32)
    category: str = Field(default="service", max_length=80)


class ExpenseInput(LineItemInput):
    authorization_status: Literal["proposed", "approved", "rejected"] = "proposed"
    authorization_date: date | None = None
    authorization_reference: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=2000)

    @field_validator("authorization_reference")
    @classmethod
    def trim_authorization_reference(cls, value: str) -> str:
        return value.strip()


class ExpenseAuthorizationInput(APIModel):
    authorization_status: Literal["proposed", "approved", "rejected"]
    authorization_date: date | None = None
    authorization_reference: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=2000)


class BookingInput(APIModel):
    client_id: int = Field(gt=0)
    agreement_id: int | None = Field(default=None, gt=0)
    event_name: str = Field(min_length=1, max_length=200)
    event_type: str = Field(default="", max_length=120)
    event_date: date
    venue: str = Field(default="", max_length=200)
    venue_address: str = Field(default="", max_length=4000)
    coverage_start: str = Field(default="09:00", max_length=20)
    coverage_end: str = Field(default="15:00", max_length=20)
    coverage_hours: str = Field(default="6", max_length=24)
    scope: str = Field(default="", max_length=10000)
    delivery_method: str = Field(default="Online gallery", max_length=100)
    delivery_deadline: str = Field(default="", max_length=120)
    special_deliverables: str = Field(default="", max_length=5000)
    guaranteed_image_count: int | None = Field(default=None, ge=0, le=100000)
    overtime_rate: str = Field(default="150.00", max_length=32)
    payment_terms_days: int = Field(default=15, ge=0, le=365)
    exceptions: str = Field(default="", max_length=5000)
    line_items: list[LineItemInput] = Field(default_factory=list, max_length=100)
    additional_expenses: list[ExpenseInput] = Field(default_factory=list, max_length=100)

    @field_validator("coverage_hours")
    @classmethod
    def valid_coverage_hours(cls, value: str) -> str:
        from decimal import Decimal, InvalidOperation

        try:
            hours = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("Coverage hours must be a positive decimal value") from exc
        if not hours.is_finite() or hours <= 0:
            raise ValueError("Coverage hours must be a positive decimal value")
        return value

    @field_validator("coverage_start", "coverage_end")
    @classmethod
    def valid_coverage_time(cls, value: str) -> str:
        from datetime import time

        try:
            time.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("Coverage time must use HH:MM format") from exc
        return value

    @field_validator("exceptions")
    @classmethod
    def identify_exception_section(cls, value: str) -> str:
        if value and value.casefold() not in {"none", "no exceptions"}:
            if not re.search(r"(?:section|§)\s*(?:[1-9]|1[0-6])(?:\.\d+)?", value, re.IGNORECASE):
                raise ValueError(
                    "Identify the affected Master Agreement section for each exception"
                )
        return value


class BookingAcceptInput(APIModel):
    accepted_date: date
    acceptance_reference: str = Field(default="", max_length=200)


class AmendmentInput(APIModel):
    change_summary: str = Field(min_length=1, max_length=4000)
    changes: dict[str, object]
    written_acceptance_date: date | None = None
    acceptance_reference: str = Field(default="", max_length=200)
    accepted: bool = False


class InvoiceInput(APIModel):
    booking_id: int = Field(gt=0)
    invoice_date: date
    due_date: date
    tax_mode: Literal["none", "rate", "manual"] = "none"
    tax_rate: str = "0"
    manual_tax: str = "0"
    notes: str = Field(default="", max_length=5000)
    line_items: list["InvoiceLineInput"] = Field(default_factory=list, max_length=100)


class InvoiceLineInput(APIModel):
    source_booking_line_item_id: int | None = Field(default=None, gt=0)
    source_expense_id: int | None = Field(default=None, gt=0)
    description: str = Field(min_length=1, max_length=300)
    quantity: str = Field(min_length=1, max_length=24)
    unit: str = Field(default="service", max_length=40)
    unit_rate: str = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def require_one_source(self):
        if (self.source_booking_line_item_id is None) == (self.source_expense_id is None):
            raise ValueError(
                "Each invoice line must refer to exactly one booking item or approved expense"
            )
        return self


class PaymentInput(APIModel):
    paid_at: date
    amount: str = Field(min_length=1, max_length=32)
    method: str = Field(default="", max_length=80)
    reference: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=2000)


class ProfileInput(APIModel):
    legal_name: str = Field(default="", max_length=200)
    business_name: str = Field(default="", max_length=200)
    mailing_address: str = Field(default="", max_length=4000)
    email: str = Field(default="", max_length=254)
    phone: str = Field(default="", max_length=80)
    payment_instructions: str = Field(default="", max_length=4000)
    default_payment_terms_days: int = Field(default=15, ge=0, le=365)
    currency: Literal["USD"] = "USD"
    default_photography_rate: str = "0"
    default_overtime_rate: str = "150.00"
    default_delivery_method: str = Field(default="Online gallery", max_length=80)
    default_delivery_deadline: str = Field(
        default="Within ten (10) business days after the event", max_length=120
    )

    @field_validator("email")
    @classmethod
    def valid_optional_email(cls, value: str) -> str:
        if value and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Enter a valid email address")
        return value


class AgreementInput(APIModel):
    client_id: int = Field(gt=0)
    effective_date: date
    accepted: bool = False
    accepted_date: date | None = None
    acceptance_reference: str = Field(default="", max_length=200)


class AgreementAcceptInput(APIModel):
    accepted_date: date
    acceptance_reference: str = Field(min_length=1, max_length=200)


InvoiceInput.model_rebuild()


class DocumentRequest(APIModel):
    document_type: Literal["agreement", "booking_confirmation", "invoice"]
    entity_id: int = Field(gt=0)
