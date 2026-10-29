"""Allow locally stored reference files without a client association.

Revision ID: 0003_optional_document_client
Revises: 0002_booking_lifecycle
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_optional_document_client"
down_revision: str | Sequence[str] | None = "0002_booking_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Permit W-9 and other photographer-owned uploads in the document library."""
    bind = op.get_bind()
    document_columns = {
        column["name"]: column for column in sa.inspect(bind).get_columns("generated_documents")
    }
    if not document_columns["client_id"]["nullable"]:
        with op.batch_alter_table("generated_documents") as batch_op:
            batch_op.alter_column("client_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    """Keep the nullable relationship to avoid deleting standalone local documents."""
    raise NotImplementedError("Standalone document records cannot be downgraded without data loss.")
