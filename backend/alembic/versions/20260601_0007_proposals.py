"""add commercial proposals

Revision ID: 20260601_0007
Revises: 20260601_0006
Create Date: 2026-06-01
"""

from collections.abc import Sequence

from alembic import context
from alembic import op
import sqlalchemy as sa

revision: str = "20260601_0007"
down_revision: str | None = "20260601_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        _create_tables_unchecked()
        return

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("proposals"):
        _create_tables_unchecked()
        return

    if not inspector.has_table("proposal_items"):
        _create_items_table_unchecked()


def downgrade() -> None:
    if context.is_offline_mode():
        _drop_tables_unchecked()
        return

    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("proposal_items"):
        for index in inspector.get_indexes("proposal_items"):
            op.drop_index(index["name"], table_name="proposal_items")
        op.drop_table("proposal_items")
    if inspector.has_table("proposals"):
        for index in inspector.get_indexes("proposals"):
            op.drop_index(index["name"], table_name="proposals")
        op.drop_table("proposals")


def _create_tables_unchecked() -> None:
    op.create_table(
        "proposals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=True),
        sa.Column("lead_id", sa.String(length=36), nullable=True),
        sa.Column("conversation_id", sa.String(length=36), nullable=True),
        sa.Column("proposal_number", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("customer_name", sa.String(length=180), nullable=False),
        sa.Column("customer_phone", sa.String(length=40), nullable=True),
        sa.Column("customer_email", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column("property_type", sa.String(length=80), nullable=True),
        sa.Column("average_bill", sa.Numeric(12, 2), nullable=True),
        sa.Column("estimated_system_power_kwp", sa.Numeric(12, 3), nullable=True),
        sa.Column("estimated_monthly_generation_kwh", sa.Numeric(12, 2), nullable=True),
        sa.Column("estimated_savings_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("validity_days", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_conditions", sa.Text(), nullable=True),
        sa.Column("pdf_url", sa.String(length=800), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_proposals_city"), "proposals", ["city"], unique=False)
    op.create_index(op.f("ix_proposals_conversation_id"), "proposals", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_proposals_customer_id"), "proposals", ["customer_id"], unique=False)
    op.create_index(op.f("ix_proposals_lead_id"), "proposals", ["lead_id"], unique=False)
    op.create_index(op.f("ix_proposals_proposal_number"), "proposals", ["proposal_number"], unique=True)
    op.create_index(op.f("ix_proposals_status"), "proposals", ["status"], unique=False)
    _create_items_table_unchecked()


def _create_items_table_unchecked() -> None:
    op.create_table(
        "proposal_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("proposal_id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("editable", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["proposal_id"], ["proposals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_proposal_items_category"), "proposal_items", ["category"], unique=False)
    op.create_index(op.f("ix_proposal_items_proposal_id"), "proposal_items", ["proposal_id"], unique=False)


def _drop_tables_unchecked() -> None:
    op.drop_index(op.f("ix_proposal_items_proposal_id"), table_name="proposal_items")
    op.drop_index(op.f("ix_proposal_items_category"), table_name="proposal_items")
    op.drop_table("proposal_items")
    op.drop_index(op.f("ix_proposals_status"), table_name="proposals")
    op.drop_index(op.f("ix_proposals_proposal_number"), table_name="proposals")
    op.drop_index(op.f("ix_proposals_lead_id"), table_name="proposals")
    op.drop_index(op.f("ix_proposals_customer_id"), table_name="proposals")
    op.drop_index(op.f("ix_proposals_conversation_id"), table_name="proposals")
    op.drop_index(op.f("ix_proposals_city"), table_name="proposals")
    op.drop_table("proposals")
