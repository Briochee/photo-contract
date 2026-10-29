"""Adopt draft, pending, and finalized master-agreement statuses.

Revision ID: 0003_agreement_lifecycle
Revises: 0002_optional_profile_defaults
Create Date: 2026-10-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_agreement_lifecycle"
down_revision: str | Sequence[str] | None = "0002_optional_profile_defaults"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Map accepted agreements to finalized and saved draft PDFs to pending."""
    op.execute("UPDATE master_agreements SET status = 'finalized' WHERE status = 'accepted'")
    op.execute(
        """
        UPDATE master_agreements
        SET status = 'pending'
        WHERE status = 'draft'
          AND EXISTS (
              SELECT 1
              FROM generated_documents
              WHERE generated_documents.document_type = 'agreement'
                AND generated_documents.reference = master_agreements.agreement_ref
          )
        """
    )
    op.execute(
        """
        UPDATE generated_documents
        SET status = 'pending'
        WHERE document_type = 'agreement'
          AND status = 'draft'
          AND reference IN (
              SELECT agreement_ref
              FROM master_agreements
              WHERE status = 'pending'
          )
        """
    )


def downgrade() -> None:
    """Map finalized back to accepted and pending back to draft for older app versions."""
    op.execute("UPDATE master_agreements SET status = 'accepted' WHERE status = 'finalized'")
    op.execute("UPDATE master_agreements SET status = 'draft' WHERE status = 'pending'")
    op.execute(
        "UPDATE generated_documents SET status = 'draft' "
        "WHERE document_type = 'agreement' AND status = 'pending'"
    )
