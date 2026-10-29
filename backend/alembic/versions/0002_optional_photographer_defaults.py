"""Allow photographer profiles without optional company and booking defaults.

Revision ID: 0002_optional_profile_defaults
Revises: 0001_initial
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_optional_profile_defaults"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Make business name and profile defaults nullable without changing stored values."""
    with op.batch_alter_table("photographer_profiles") as batch_op:
        batch_op.alter_column("business_name", existing_type=sa.String(length=200), nullable=True)
        batch_op.alter_column(
            "default_payment_terms_days", existing_type=sa.Integer(), nullable=True
        )
        batch_op.alter_column(
            "default_photography_rate_cents", existing_type=sa.Integer(), nullable=True
        )
        batch_op.alter_column(
            "default_overtime_rate_cents", existing_type=sa.Integer(), nullable=True
        )
        batch_op.alter_column(
            "default_delivery_method", existing_type=sa.String(length=80), nullable=True
        )
        batch_op.alter_column(
            "default_delivery_deadline", existing_type=sa.String(length=120), nullable=True
        )


def downgrade() -> None:
    """Restore former required values before making the columns non-nullable again."""
    op.execute(
        sa.text(
            """
            UPDATE photographer_profiles
            SET business_name = COALESCE(business_name, ''),
                default_payment_terms_days = COALESCE(default_payment_terms_days, 15),
                default_photography_rate_cents = COALESCE(default_photography_rate_cents, 0),
                default_overtime_rate_cents = COALESCE(default_overtime_rate_cents, 15000),
                default_delivery_method = COALESCE(default_delivery_method, 'Online gallery'),
                default_delivery_deadline = COALESCE(
                    default_delivery_deadline,
                    'Within ten (10) business days after the event'
                )
            """
        )
    )
    with op.batch_alter_table("photographer_profiles") as batch_op:
        batch_op.alter_column("business_name", existing_type=sa.String(length=200), nullable=False)
        batch_op.alter_column(
            "default_payment_terms_days", existing_type=sa.Integer(), nullable=False
        )
        batch_op.alter_column(
            "default_photography_rate_cents", existing_type=sa.Integer(), nullable=False
        )
        batch_op.alter_column(
            "default_overtime_rate_cents", existing_type=sa.Integer(), nullable=False
        )
        batch_op.alter_column(
            "default_delivery_method", existing_type=sa.String(length=80), nullable=False
        )
        batch_op.alter_column(
            "default_delivery_deadline", existing_type=sa.String(length=120), nullable=False
        )
