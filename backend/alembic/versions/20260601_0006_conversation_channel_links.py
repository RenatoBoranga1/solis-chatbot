"""add omnichannel conversation links

Revision ID: 20260601_0006
Revises: 20260529_0005
Create Date: 2026-06-01
"""

from collections.abc import Sequence

from alembic import context
from alembic import op
import sqlalchemy as sa

revision: str = "20260601_0006"
down_revision: str | None = "20260529_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        _create_table_unchecked()
        return

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("conversation_channel_links"):
        _create_table_unchecked()
        return

    indexes = {index["name"] for index in inspector.get_indexes("conversation_channel_links")}
    _create_index_if_missing("ix_conversation_channel_links_customer_id", ["customer_id"], indexes)
    _create_index_if_missing("ix_conversation_channel_links_external_id", ["external_id"], indexes)
    _create_index_if_missing("ix_conversation_channel_links_lead_id", ["lead_id"], indexes)
    _create_index_if_missing("ix_conversation_channel_links_phone", ["phone"], indexes)
    _create_index_if_missing("ix_conversation_channel_links_phone_status", ["phone", "status"], indexes)
    _create_index_if_missing("ix_conversation_channel_links_source_channel", ["source_channel"], indexes)
    _create_index_if_missing("ix_conversation_channel_links_source_conversation_id", ["source_conversation_id"], indexes)
    _create_index_if_missing(
        "ix_conversation_channel_links_source_target",
        ["source_conversation_id", "target_conversation_id"],
        indexes,
    )
    _create_index_if_missing("ix_conversation_channel_links_status", ["status"], indexes)
    _create_index_if_missing("ix_conversation_channel_links_target_channel", ["target_channel"], indexes)
    _create_index_if_missing("ix_conversation_channel_links_target_conversation_id", ["target_conversation_id"], indexes)
    _create_index_if_missing("ix_conversation_channel_links_ticket_id", ["ticket_id"], indexes)


def downgrade() -> None:
    if context.is_offline_mode():
        _drop_table_unchecked()
        return

    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("conversation_channel_links"):
        for index in inspector.get_indexes("conversation_channel_links"):
            op.drop_index(index["name"], table_name="conversation_channel_links")
        op.drop_table("conversation_channel_links")


def _create_table_unchecked() -> None:
    op.create_table(
        "conversation_channel_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column("source_conversation_id", sa.String(length=36), nullable=False),
        sa.Column("target_conversation_id", sa.String(length=36), nullable=True),
        sa.Column("source_channel", sa.String(length=40), nullable=False),
        sa.Column("target_channel", sa.String(length=40), nullable=False),
        sa.Column("external_id", sa.String(length=180), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=False),
        sa.Column("lead_id", sa.String(length=36), nullable=True),
        sa.Column("ticket_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.ForeignKeyConstraint(["source_conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["target_conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_conversation_channel_links_customer_id"), "conversation_channel_links", ["customer_id"], unique=False)
    op.create_index(op.f("ix_conversation_channel_links_external_id"), "conversation_channel_links", ["external_id"], unique=False)
    op.create_index(op.f("ix_conversation_channel_links_lead_id"), "conversation_channel_links", ["lead_id"], unique=False)
    op.create_index(op.f("ix_conversation_channel_links_phone"), "conversation_channel_links", ["phone"], unique=False)
    op.create_index("ix_conversation_channel_links_phone_status", "conversation_channel_links", ["phone", "status"], unique=False)
    op.create_index(op.f("ix_conversation_channel_links_source_channel"), "conversation_channel_links", ["source_channel"], unique=False)
    op.create_index(
        op.f("ix_conversation_channel_links_source_conversation_id"),
        "conversation_channel_links",
        ["source_conversation_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversation_channel_links_source_target",
        "conversation_channel_links",
        ["source_conversation_id", "target_conversation_id"],
        unique=False,
    )
    op.create_index(op.f("ix_conversation_channel_links_status"), "conversation_channel_links", ["status"], unique=False)
    op.create_index(op.f("ix_conversation_channel_links_target_channel"), "conversation_channel_links", ["target_channel"], unique=False)
    op.create_index(
        op.f("ix_conversation_channel_links_target_conversation_id"),
        "conversation_channel_links",
        ["target_conversation_id"],
        unique=False,
    )
    op.create_index(op.f("ix_conversation_channel_links_ticket_id"), "conversation_channel_links", ["ticket_id"], unique=False)


def _drop_table_unchecked() -> None:
    op.drop_index(op.f("ix_conversation_channel_links_ticket_id"), table_name="conversation_channel_links")
    op.drop_index(op.f("ix_conversation_channel_links_target_conversation_id"), table_name="conversation_channel_links")
    op.drop_index(op.f("ix_conversation_channel_links_target_channel"), table_name="conversation_channel_links")
    op.drop_index(op.f("ix_conversation_channel_links_status"), table_name="conversation_channel_links")
    op.drop_index("ix_conversation_channel_links_source_target", table_name="conversation_channel_links")
    op.drop_index(op.f("ix_conversation_channel_links_source_conversation_id"), table_name="conversation_channel_links")
    op.drop_index(op.f("ix_conversation_channel_links_source_channel"), table_name="conversation_channel_links")
    op.drop_index("ix_conversation_channel_links_phone_status", table_name="conversation_channel_links")
    op.drop_index(op.f("ix_conversation_channel_links_phone"), table_name="conversation_channel_links")
    op.drop_index(op.f("ix_conversation_channel_links_lead_id"), table_name="conversation_channel_links")
    op.drop_index(op.f("ix_conversation_channel_links_external_id"), table_name="conversation_channel_links")
    op.drop_index(op.f("ix_conversation_channel_links_customer_id"), table_name="conversation_channel_links")
    op.drop_table("conversation_channel_links")


def _create_index_if_missing(name: str, columns: list[str], indexes: set[str]) -> None:
    if name not in indexes:
        op.create_index(name, "conversation_channel_links", columns, unique=False)
