"""SQLAlchemy 2.x persistence models for clients, bookings, invoices, and documents."""

from datetime import UTC, date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base metadata shared by application models and Alembic."""


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class Client(TimestampMixin, Base):
    __tablename__ = "clients"
    __table_args__ = (Index("ix_clients_legal_name", "legal_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200))
    mailing_address: Mapped[str] = mapped_column(Text, default="", nullable=False)
    primary_contact_name: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    primary_contact_title: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    contact_email: Mapped[str] = mapped_column(String(254), default="", nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    agreements: Mapped[list["MasterAgreement"]] = relationship(back_populates="client")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="client")


class PhotographerProfile(TimestampMixin, Base):
    __tablename__ = "photographer_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    legal_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    business_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mailing_address: Mapped[str] = mapped_column(Text, default="", nullable=False)
    email: Mapped[str] = mapped_column(String(254), default="", nullable=False)
    phone: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    payment_instructions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    default_payment_terms_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    default_photography_rate_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_overtime_rate_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_delivery_method: Mapped[str | None] = mapped_column(String(80), nullable=True)
    default_delivery_deadline: Mapped[str | None] = mapped_column(String(120), nullable=True)


class MasterAgreement(TimestampMixin, Base):
    __tablename__ = "master_agreements"
    __table_args__ = (UniqueConstraint("agreement_ref", name="uq_agreements_reference"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    agreement_ref: Mapped[str] = mapped_column(String(32), nullable=False)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False
    )
    photographer_profile_id: Mapped[int] = mapped_column(
        ForeignKey("photographer_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    template_version: Mapped[str] = mapped_column(String(32), nullable=False)
    legal_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    legal_text_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    source_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acceptance_reference: Mapped[str] = mapped_column(String(200), default="", nullable=False)

    client: Mapped[Client] = relationship(back_populates="agreements")
    photographer: Mapped[PhotographerProfile] = relationship()
    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="agreement", passive_deletes="all"
    )


class Booking(TimestampMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("booking_ref", name="uq_bookings_reference"),
        CheckConstraint(
            "payment_terms_days >= 0 AND payment_terms_days <= 365", name="ck_booking_terms"
        ),
        Index("ix_bookings_event_date_status", "event_date", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_ref: Mapped[str] = mapped_column(String(32), nullable=False)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False
    )
    agreement_id: Mapped[int | None] = mapped_column(
        ForeignKey("master_agreements.id", ondelete="RESTRICT")
    )
    agreement_date_snapshot: Mapped[str] = mapped_column(String(10), default="", nullable=False)
    event_name: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    venue: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    venue_address: Mapped[str] = mapped_column(Text, default="", nullable=False)
    coverage_start: Mapped[str] = mapped_column(String(20), default="09:00", nullable=False)
    coverage_end: Mapped[str] = mapped_column(String(20), default="15:00", nullable=False)
    coverage_hours: Mapped[str] = mapped_column(String(24), default="6", nullable=False)
    scope: Mapped[str] = mapped_column(Text, default="", nullable=False)
    delivery_method: Mapped[str] = mapped_column(
        String(100), default="Online gallery", nullable=False
    )
    delivery_deadline: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    special_deliverables: Mapped[str] = mapped_column(Text, default="", nullable=False)
    guaranteed_image_count: Mapped[int | None] = mapped_column(Integer)
    overtime_rate_cents: Mapped[int] = mapped_column(Integer, default=15000, nullable=False)
    authorized_expense_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    exceptions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acceptance_reference: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    accepted_snapshot_json: Mapped[str | None] = mapped_column(Text)

    client: Mapped[Client] = relationship(back_populates="bookings")
    agreement: Mapped[MasterAgreement | None] = relationship(back_populates="bookings")
    line_items: Mapped[list["BookingLineItem"]] = relationship(
        back_populates="booking",
        cascade="all, delete-orphan",
        order_by="BookingLineItem.sort_order",
    )
    additional_expenses: Mapped[list["AdditionalExpense"]] = relationship(
        back_populates="booking",
        cascade="all, delete-orphan",
        order_by="AdditionalExpense.sort_order",
    )
    amendments: Mapped[list["BookingAmendment"]] = relationship(
        back_populates="booking",
        cascade="all, delete-orphan",
        order_by="BookingAmendment.created_at",
    )
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="booking")


class BookingLineItem(Base):
    __tablename__ = "booking_line_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[str] = mapped_column(String(24), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), default="service", nullable=False)
    unit_rate_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="photography", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    booking: Mapped[Booking] = relationship(back_populates="line_items")


class AdditionalExpense(Base):
    __tablename__ = "additional_expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[str] = mapped_column(String(24), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), default="service", nullable=False)
    unit_rate_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    authorization_status: Mapped[str] = mapped_column(
        String(20), default="proposed", nullable=False
    )
    authorization_date: Mapped[date | None] = mapped_column(Date)
    authorization_reference: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    booking: Mapped[Booking] = relationship(back_populates="additional_expenses")


class BookingAmendment(TimestampMixin, Base):
    __tablename__ = "booking_amendments"
    __table_args__ = (UniqueConstraint("amendment_ref", name="uq_amendments_reference"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    amendment_ref: Mapped[str] = mapped_column(String(40), nullable=False)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False
    )
    change_summary: Mapped[str] = mapped_column(Text, nullable=False)
    changes_json: Mapped[str] = mapped_column(Text, nullable=False)
    previous_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="proposed", nullable=False)
    written_acceptance_date: Mapped[date | None] = mapped_column(Date)
    acceptance_reference: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    booking: Mapped[Booking] = relationship(back_populates="amendments")


class Invoice(TimestampMixin, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("invoice_ref", name="uq_invoices_reference"),
        CheckConstraint("version >= 1", name="ck_invoice_version"),
        Index("ix_invoices_status_due_date", "status", "due_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_ref: Mapped[str] = mapped_column(String(32), nullable=False)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False
    )
    revision_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("invoices.id", ondelete="RESTRICT")
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    tax_mode: Mapped[str] = mapped_column(String(12), default="manual", nullable=False)
    tax_rate: Mapped[str] = mapped_column(String(16), default="0", nullable=False)
    subtotal_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tax_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    issued_snapshot_json: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    booking: Mapped[Booking] = relationship(back_populates="invoices")
    line_items: Mapped[list["InvoiceLineItem"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLineItem.sort_order",
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="Payment.paid_at"
    )
    revision_of: Mapped["Invoice | None"] = relationship(
        remote_side="Invoice.id", back_populates="revisions", foreign_keys=[revision_of_id]
    )
    revisions: Mapped[list["Invoice"]] = relationship(
        back_populates="revision_of", foreign_keys=[revision_of_id]
    )


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    source_booking_line_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("booking_line_items.id", ondelete="SET NULL")
    )
    source_expense_id: Mapped[int | None] = mapped_column(
        ForeignKey("additional_expenses.id", ondelete="SET NULL")
    )
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[str] = mapped_column(String(24), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), default="service", nullable=False)
    unit_rate_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    invoice: Mapped[Invoice] = relationship(back_populates="line_items")


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount_cents > 0", name="ck_payment_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    paid_at: Mapped[date] = mapped_column(Date, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    method: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    reference: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    invoice: Mapped[Invoice] = relationship(back_populates="payments")


class GeneratedDocument(TimestampMixin, Base):
    __tablename__ = "generated_documents"
    __table_args__ = (
        UniqueConstraint("document_type", "reference", "version", name="uq_document_version"),
        Index("ix_documents_type_created_at", "document_type", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False
    )
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id", ondelete="RESTRICT"))
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id", ondelete="RESTRICT"))
    reference: Mapped[str] = mapped_column(String(40), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="final", nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    template_version: Mapped[str] = mapped_column(String(32), nullable=False)
    source_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)

    client: Mapped[Client] = relationship()
    booking: Mapped[Booking | None] = relationship()
    invoice: Mapped[Invoice | None] = relationship()


class ReferenceSequence(Base):
    __tablename__ = "reference_sequences"

    kind: Mapped[str] = mapped_column(String(16), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
