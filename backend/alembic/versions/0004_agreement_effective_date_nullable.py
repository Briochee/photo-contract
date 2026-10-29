"""Keep an agreement's effective date unset until it is finalized.

Revision ID: 0004_agreement_effective_date_nullable
Revises: 0003_agreement_lifecycle
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_agreement_effective_date_nullable"
down_revision: str | Sequence[str] | None = "0003_agreement_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove placeholder dates from unsigned agreements and allow a null effective date."""
    op.execute(
        "UPDATE master_agreements SET effective_date = NULL WHERE status IN ('draft', 'pending')"
    )
    with op.batch_alter_table("master_agreements") as batch_op:
        batch_op.alter_column("effective_date", existing_type=sa.Date(), nullable=True)


def downgrade() -> None:
    """Restore a creation-date fallback before requiring the column again."""
    op.execute(
        sa.text(
            """
            UPDATE master_agreements
            SET effective_date = date(created_at)
            WHERE effective_date IS NULL
            """
        )
    )
    with op.batch_alter_table("master_agreements") as batch_op:
        batch_op.alter_column("effective_date", existing_type=sa.Date(), nullable=False)
