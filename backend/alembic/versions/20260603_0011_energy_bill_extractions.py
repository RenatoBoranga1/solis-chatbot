"""add energy bill extraction tables

Revision ID: 20260603_0011
Revises: 20260603_0010
Create Date: 2026-06-03
"""

from collections.abc import Sequence

from alembic import context
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260603_0011"
down_revision: str | None = "20260603_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        _create_extractions_unchecked()
        _create_history_unchecked()
        return

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("energy_bill_extractions"):
        _create_extractions_unchecked()
        inspector = sa.inspect(op.get_bind())
    else:
        _ensure_origin_column(inspector)
    if not inspector.has_table("energy_bill_consumption_history"):
        _create_history_unchecked()


def downgrade() -> None:
    if context.is_offline_mode():
        _drop_history_unchecked()
        _drop_extractions_unchecked()
        return

    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("energy_bill_consumption_history"):
        for index in inspector.get_indexes("energy_bill_consumption_history"):
            op.drop_index(index["name"], table_name="energy_bill_consumption_history")
        op.drop_table("energy_bill_consumption_history")
    if inspector.has_table("energy_bill_extractions"):
        for index in inspector.get_indexes("energy_bill_extractions"):
            op.drop_index(index["name"], table_name="energy_bill_extractions")
        op.drop_table("energy_bill_extractions")


def _create_extractions_unchecked() -> None:
    op.create_table(
        "energy_bill_extractions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=True),
        sa.Column("customer_id", sa.String(length=36), nullable=True),
        sa.Column("lead_id", sa.String(length=36), nullable=True),
        sa.Column("attachment_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("origin", sa.String(length=40), nullable=False),
        sa.Column("file_name", sa.String(length=260), nullable=True),
        sa.Column("file_type", sa.String(length=80), nullable=True),
        sa.Column("file_url", sa.String(length=800), nullable=True),
        sa.Column("distributor", sa.String(length=180), nullable=True),
        sa.Column("customer_name", sa.String(length=180), nullable=True),
        sa.Column("customer_document_masked", sa.String(length=80), nullable=True),
        sa.Column("installation_number", sa.String(length=120), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column("reference_month", sa.String(length=20), nullable=True),
        sa.Column("due_date", sa.String(length=20), nullable=True),
        sa.Column("current_consumption_kwh", sa.Numeric(12, 2), nullable=True),
        sa.Column("current_bill_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("average_consumption_kwh", sa.Numeric(12, 2), nullable=True),
        sa.Column("average_bill_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("min_consumption_kwh", sa.Numeric(12, 2), nullable=True),
        sa.Column("max_consumption_kwh", sa.Numeric(12, 2), nullable=True),
        sa.Column("estimated_system_power_kwp", sa.Numeric(12, 3), nullable=True),
        sa.Column("estimated_monthly_generation_kwh", sa.Numeric(12, 2), nullable=True),
        sa.Column("estimated_monthly_savings", sa.Numeric(12, 2), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("needs_human_review", sa.Boolean(), nullable=False),
        sa.Column("missing_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("parsed_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_extraction", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_text_excerpt", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("confirmed_by", sa.String(length=36), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["attachment_id"], ["attachments.id"]),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in [
        "attachment_id",
        "city",
        "confidence_score",
        "confirmed_by",
        "conversation_id",
        "customer_id",
        "distributor",
        "file_type",
        "installation_number",
        "lead_id",
        "needs_human_review",
        "origin",
        "reference_month",
        "source",
        "state",
        "status",
    ]:
        op.create_index(op.f(f"ix_energy_bill_extractions_{column}"), "energy_bill_extractions", [column], unique=False)
    op.create_index(
        "ix_energy_bill_extractions_status_confidence",
        "energy_bill_extractions",
        ["status", "confidence_score"],
        unique=False,
    )


def _create_history_unchecked() -> None:
    op.create_table(
        "energy_bill_consumption_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("extraction_id", sa.String(length=36), nullable=False),
        sa.Column("period", sa.String(length=20), nullable=False),
        sa.Column("consumption_kwh", sa.Numeric(12, 2), nullable=False),
        sa.Column("bill_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["extraction_id"], ["energy_bill_extractions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_energy_bill_consumption_history_extraction_id"), "energy_bill_consumption_history", ["extraction_id"], unique=False)
    op.create_index(op.f("ix_energy_bill_consumption_history_period"), "energy_bill_consumption_history", ["period"], unique=False)
    op.create_index(
        "ix_energy_bill_history_extraction_period",
        "energy_bill_consumption_history",
        ["extraction_id", "period"],
        unique=False,
    )


def _ensure_origin_column(inspector) -> None:
    columns = {column["name"] for column in inspector.get_columns("energy_bill_extractions")}
    indexes = {index["name"] for index in inspector.get_indexes("energy_bill_extractions")}
    if "origin" not in columns:
        op.add_column(
            "energy_bill_extractions",
            sa.Column("origin", sa.String(length=40), nullable=False, server_default="api"),
        )
        op.alter_column("energy_bill_extractions", "origin", server_default=None)
    if "ix_energy_bill_extractions_origin" not in indexes:
        op.create_index(op.f("ix_energy_bill_extractions_origin"), "energy_bill_extractions", ["origin"], unique=False)


def _drop_history_unchecked() -> None:
    op.drop_index("ix_energy_bill_history_extraction_period", table_name="energy_bill_consumption_history")
    op.drop_index(op.f("ix_energy_bill_consumption_history_period"), table_name="energy_bill_consumption_history")
    op.drop_index(op.f("ix_energy_bill_consumption_history_extraction_id"), table_name="energy_bill_consumption_history")
    op.drop_table("energy_bill_consumption_history")


def _drop_extractions_unchecked() -> None:
    op.drop_index("ix_energy_bill_extractions_status_confidence", table_name="energy_bill_extractions")
    for column in [
        "status",
        "state",
        "source",
        "reference_month",
        "origin",
        "needs_human_review",
        "lead_id",
        "installation_number",
        "file_type",
        "distributor",
        "customer_id",
        "conversation_id",
        "confirmed_by",
        "confidence_score",
        "city",
        "attachment_id",
    ]:
        op.drop_index(op.f(f"ix_energy_bill_extractions_{column}"), table_name="energy_bill_extractions")
    op.drop_table("energy_bill_extractions")
