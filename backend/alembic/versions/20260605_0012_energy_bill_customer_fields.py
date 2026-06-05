"""add customer fields to energy bill extractions

Revision ID: 20260605_0012
Revises: 20260603_0011
Create Date: 2026-06-05
"""

from collections.abc import Sequence

from alembic import context
from alembic import op
import sqlalchemy as sa

revision: str = "20260605_0012"
down_revision: str | None = "20260603_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ENERGY_BILL_COLUMNS = {
    "customer_address": sa.Column("customer_address", sa.String(length=260), nullable=True),
    "customer_district": sa.Column("customer_district", sa.String(length=120), nullable=True),
    "customer_postal_code": sa.Column("customer_postal_code", sa.String(length=20), nullable=True),
    "customer_unit_number": sa.Column("customer_unit_number", sa.String(length=120), nullable=True),
    "tariff_flag": sa.Column("tariff_flag", sa.String(length=80), nullable=True),
}


def upgrade() -> None:
    if context.is_offline_mode():
        for column in ENERGY_BILL_COLUMNS.values():
            op.add_column("energy_bill_extractions", column.copy())
        op.create_index("ix_energy_bill_extractions_customer_postal_code", "energy_bill_extractions", ["customer_postal_code"])
        op.create_index("ix_energy_bill_extractions_customer_unit_number", "energy_bill_extractions", ["customer_unit_number"])
        return

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("energy_bill_extractions"):
        return
    existing_columns = {column["name"] for column in inspector.get_columns("energy_bill_extractions")}
    for name, column in ENERGY_BILL_COLUMNS.items():
        if name not in existing_columns:
            op.add_column("energy_bill_extractions", column.copy())

    existing_indexes = {index["name"] for index in inspector.get_indexes("energy_bill_extractions")}
    if "ix_energy_bill_extractions_customer_postal_code" not in existing_indexes:
        op.create_index("ix_energy_bill_extractions_customer_postal_code", "energy_bill_extractions", ["customer_postal_code"])
    if "ix_energy_bill_extractions_customer_unit_number" not in existing_indexes:
        op.create_index("ix_energy_bill_extractions_customer_unit_number", "energy_bill_extractions", ["customer_unit_number"])


def downgrade() -> None:
    if context.is_offline_mode():
        op.drop_index("ix_energy_bill_extractions_customer_unit_number", table_name="energy_bill_extractions")
        op.drop_index("ix_energy_bill_extractions_customer_postal_code", table_name="energy_bill_extractions")
        for name in reversed(tuple(ENERGY_BILL_COLUMNS)):
            op.drop_column("energy_bill_extractions", name)
        return

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("energy_bill_extractions"):
        return
    existing_indexes = {index["name"] for index in inspector.get_indexes("energy_bill_extractions")}
    if "ix_energy_bill_extractions_customer_unit_number" in existing_indexes:
        op.drop_index("ix_energy_bill_extractions_customer_unit_number", table_name="energy_bill_extractions")
    if "ix_energy_bill_extractions_customer_postal_code" in existing_indexes:
        op.drop_index("ix_energy_bill_extractions_customer_postal_code", table_name="energy_bill_extractions")

    existing_columns = {column["name"] for column in inspector.get_columns("energy_bill_extractions")}
    for name in reversed(tuple(ENERGY_BILL_COLUMNS)):
        if name in existing_columns:
            op.drop_column("energy_bill_extractions", name)
