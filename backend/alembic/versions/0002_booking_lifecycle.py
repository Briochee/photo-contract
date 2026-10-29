"""Align saved booking confirmations with the pending/finalized lifecycle.

Revision ID: 0002_booking_lifecycle
Revises: 0001_current_schema
Create Date: 2026-10-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_booking_lifecycle"
down_revision: str | Sequence[str] | None = "0001_current_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Promote accepted bookings and saved unsigned confirmations in existing data."""
    op.execute("UPDATE bookings SET status = 'finalized' WHERE status = 'accepted'")
    op.execute(
        """
        UPDATE bookings
        SET status = 'pending'
        WHERE status = 'draft'
          AND EXISTS (
              SELECT 1
              FROM generated_documents
              WHERE generated_documents.document_type = 'booking_confirmation'
                AND generated_documents.reference = bookings.booking_ref
          )
        """
    )
    op.execute(
        """
        UPDATE generated_documents
        SET status = 'pending'
        WHERE document_type = 'booking_confirmation'
          AND status = 'draft'
          AND reference IN (
              SELECT booking_ref FROM bookings WHERE status = 'pending'
          )
        """
    )


def downgrade() -> None:
    """Restore pre-lifecycle booking labels for compatibility with the prior application."""
    op.execute(
        """
        UPDATE generated_documents
        SET status = 'draft'
        WHERE document_type = 'booking_confirmation'
          AND status = 'pending'
          AND reference IN (
              SELECT booking_ref FROM bookings WHERE status = 'pending'
          )
        """
    )
    op.execute("UPDATE bookings SET status = 'draft' WHERE status = 'pending'")
    op.execute("UPDATE bookings SET status = 'accepted' WHERE status = 'finalized'")
