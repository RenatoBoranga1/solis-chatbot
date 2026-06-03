"""add configurable photovoltaic proposal kits

Revision ID: 20260603_0010
Revises: 20260602_0009
Create Date: 2026-06-03
"""

from collections.abc import Sequence

from alembic import context
from alembic import op
import sqlalchemy as sa

revision: str = "20260603_0010"
down_revision: str | None = "20260602_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        _create_kits_unchecked()
        _create_kit_items_unchecked()
        _add_proposal_columns_unchecked()
        return

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("proposal_kits"):
        _create_kits_unchecked()
        inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("proposal_kit_items"):
        _create_kit_items_unchecked()
        inspector = sa.inspect(op.get_bind())

    proposal_columns = {column["name"] for column in inspector.get_columns("proposals")}
    if "recommended_kit_id" not in proposal_columns:
        op.add_column("proposals", sa.Column("recommended_kit_id", sa.String(length=36), nullable=True))
        op.create_index(op.f("ix_proposals_recommended_kit_id"), "proposals", ["recommended_kit_id"], unique=False)
        op.create_foreign_key("fk_proposals_recommended_kit_id_proposal_kits", "proposals", "proposal_kits", ["recommended_kit_id"], ["id"])
    if "recommended_kit_name" not in proposal_columns:
        op.add_column("proposals", sa.Column("recommended_kit_name", sa.String(length=180), nullable=True))
    if "kit_selection_reason" not in proposal_columns:
        op.add_column("proposals", sa.Column("kit_selection_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    if context.is_offline_mode():
        _drop_proposal_columns_unchecked()
        _drop_kits_unchecked()
        return

    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("proposals"):
        proposal_columns = {column["name"] for column in inspector.get_columns("proposals")}
        if "recommended_kit_id" in proposal_columns:
            for foreign_key in inspector.get_foreign_keys("proposals"):
                if foreign_key.get("constrained_columns") == ["recommended_kit_id"]:
                    op.drop_constraint(foreign_key["name"], "proposals", type_="foreignkey")
            for index in inspector.get_indexes("proposals"):
                if index["name"] == "ix_proposals_recommended_kit_id":
                    op.drop_index(index["name"], table_name="proposals")
            op.drop_column("proposals", "recommended_kit_id")
        if "recommended_kit_name" in proposal_columns:
            op.drop_column("proposals", "recommended_kit_name")
        if "kit_selection_reason" in proposal_columns:
            op.drop_column("proposals", "kit_selection_reason")

    for table in ["proposal_kit_items", "proposal_kits"]:
        if inspector.has_table(table):
            for index in inspector.get_indexes(table):
                op.drop_index(index["name"], table_name=table)
            op.drop_table(table)


def _create_kits_unchecked() -> None:
    op.create_table(
        "proposal_kits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("min_monthly_consumption_kwh", sa.Numeric(12, 2), nullable=True),
        sa.Column("max_monthly_consumption_kwh", sa.Numeric(12, 2), nullable=True),
        sa.Column("min_power_kwp", sa.Numeric(12, 3), nullable=True),
        sa.Column("max_power_kwp", sa.Numeric(12, 3), nullable=True),
        sa.Column("suggested_power_kwp", sa.Numeric(12, 3), nullable=False),
        sa.Column("estimated_monthly_generation_kwh", sa.Numeric(12, 2), nullable=True),
        sa.Column("module_count", sa.Integer(), nullable=True),
        sa.Column("module_power_wp", sa.Integer(), nullable=True),
        sa.Column("inverter_power_kw", sa.Numeric(12, 3), nullable=True),
        sa.Column("base_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_proposal_kits_active"), "proposal_kits", ["active"], unique=False)
    op.create_index(op.f("ix_proposal_kits_max_monthly_consumption_kwh"), "proposal_kits", ["max_monthly_consumption_kwh"], unique=False)
    op.create_index(op.f("ix_proposal_kits_max_power_kwp"), "proposal_kits", ["max_power_kwp"], unique=False)
    op.create_index(op.f("ix_proposal_kits_min_monthly_consumption_kwh"), "proposal_kits", ["min_monthly_consumption_kwh"], unique=False)
    op.create_index(op.f("ix_proposal_kits_min_power_kwp"), "proposal_kits", ["min_power_kwp"], unique=False)
    op.create_index(op.f("ix_proposal_kits_name"), "proposal_kits", ["name"], unique=True)
    op.create_index(op.f("ix_proposal_kits_suggested_power_kwp"), "proposal_kits", ["suggested_power_kwp"], unique=False)


def _create_kit_items_unchecked() -> None:
    op.create_table(
        "proposal_kit_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("kit_id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["kit_id"], ["proposal_kits.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_proposal_kit_items_category"), "proposal_kit_items", ["category"], unique=False)
    op.create_index(op.f("ix_proposal_kit_items_kit_id"), "proposal_kit_items", ["kit_id"], unique=False)


def _add_proposal_columns_unchecked() -> None:
    op.add_column("proposals", sa.Column("recommended_kit_id", sa.String(length=36), nullable=True))
    op.add_column("proposals", sa.Column("recommended_kit_name", sa.String(length=180), nullable=True))
    op.add_column("proposals", sa.Column("kit_selection_reason", sa.Text(), nullable=True))
    op.create_index(op.f("ix_proposals_recommended_kit_id"), "proposals", ["recommended_kit_id"], unique=False)
    op.create_foreign_key("fk_proposals_recommended_kit_id_proposal_kits", "proposals", "proposal_kits", ["recommended_kit_id"], ["id"])


def _drop_proposal_columns_unchecked() -> None:
    op.drop_constraint("fk_proposals_recommended_kit_id_proposal_kits", "proposals", type_="foreignkey")
    op.drop_index(op.f("ix_proposals_recommended_kit_id"), table_name="proposals")
    op.drop_column("proposals", "kit_selection_reason")
    op.drop_column("proposals", "recommended_kit_name")
    op.drop_column("proposals", "recommended_kit_id")


def _drop_kits_unchecked() -> None:
    op.drop_index(op.f("ix_proposal_kit_items_kit_id"), table_name="proposal_kit_items")
    op.drop_index(op.f("ix_proposal_kit_items_category"), table_name="proposal_kit_items")
    op.drop_table("proposal_kit_items")
    op.drop_index(op.f("ix_proposal_kits_suggested_power_kwp"), table_name="proposal_kits")
    op.drop_index(op.f("ix_proposal_kits_name"), table_name="proposal_kits")
    op.drop_index(op.f("ix_proposal_kits_min_power_kwp"), table_name="proposal_kits")
    op.drop_index(op.f("ix_proposal_kits_min_monthly_consumption_kwh"), table_name="proposal_kits")
    op.drop_index(op.f("ix_proposal_kits_max_power_kwp"), table_name="proposal_kits")
    op.drop_index(op.f("ix_proposal_kits_max_monthly_consumption_kwh"), table_name="proposal_kits")
    op.drop_index(op.f("ix_proposal_kits_active"), table_name="proposal_kits")
    op.drop_table("proposal_kits")
