"""add configurable proposal price table

Revision ID: 20260601_0008
Revises: 20260601_0007
Create Date: 2026-06-01
"""

from collections.abc import Sequence

from alembic import context
from alembic import op
import sqlalchemy as sa

revision: str = "20260601_0008"
down_revision: str | None = "20260601_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        _create_price_items_unchecked()
        return

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("proposal_price_items"):
        _create_price_items_unchecked()
        return

    indexes = {index["name"] for index in inspector.get_indexes("proposal_price_items")}
    if "ix_proposal_price_items_active" not in indexes:
        op.create_index(op.f("ix_proposal_price_items_active"), "proposal_price_items", ["active"], unique=False)
    if "ix_proposal_price_items_category" not in indexes:
        op.create_index(op.f("ix_proposal_price_items_category"), "proposal_price_items", ["category"], unique=False)


def downgrade() -> None:
    if context.is_offline_mode():
        _drop_price_items_unchecked()
        return

    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("proposal_price_items"):
        for index in inspector.get_indexes("proposal_price_items"):
            op.drop_index(index["name"], table_name="proposal_price_items")
        op.drop_table("proposal_price_items")


def _create_price_items_unchecked() -> None:
    op.create_table(
        "proposal_price_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("default_unit", sa.String(length=40), nullable=False),
        sa.Column("default_quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("default_unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_proposal_price_items_active"), "proposal_price_items", ["active"], unique=False)
    op.create_index(op.f("ix_proposal_price_items_category"), "proposal_price_items", ["category"], unique=False)


def _drop_price_items_unchecked() -> None:
    op.drop_index(op.f("ix_proposal_price_items_category"), table_name="proposal_price_items")
    op.drop_index(op.f("ix_proposal_price_items_active"), table_name="proposal_price_items")
    op.drop_table("proposal_price_items")
