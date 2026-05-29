"""add provider metadata to messages

Revision ID: 20260528_0002
Revises: 20260528_0001
Create Date: 2026-05-28
"""

from collections.abc import Sequence

from alembic import context
from alembic import op
import sqlalchemy as sa

revision: str = "20260528_0002"
down_revision: str | None = "20260528_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        op.add_column("messages", sa.Column("provider", sa.String(length=60), nullable=True))
        op.add_column("messages", sa.Column("provider_message_id", sa.String(length=180), nullable=True))
        op.create_index(op.f("ix_messages_provider"), "messages", ["provider"], unique=False)
        op.create_index(op.f("ix_messages_provider_message_id"), "messages", ["provider_message_id"], unique=False)
        op.create_index(
            "ux_messages_provider_message_id",
            "messages",
            ["provider", "provider_message_id"],
            unique=True,
        )
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("messages")}
    indexes = {index["name"] for index in inspector.get_indexes("messages")}

    if "provider" not in columns:
        op.add_column("messages", sa.Column("provider", sa.String(length=60), nullable=True))
    if "provider_message_id" not in columns:
        op.add_column("messages", sa.Column("provider_message_id", sa.String(length=180), nullable=True))
    if "ix_messages_provider" not in indexes:
        op.create_index(op.f("ix_messages_provider"), "messages", ["provider"], unique=False)
    if "ix_messages_provider_message_id" not in indexes:
        op.create_index(op.f("ix_messages_provider_message_id"), "messages", ["provider_message_id"], unique=False)
    if "ux_messages_provider_message_id" not in indexes:
        op.create_index(
            "ux_messages_provider_message_id",
            "messages",
            ["provider", "provider_message_id"],
            unique=True,
        )


def downgrade() -> None:
    if context.is_offline_mode():
        op.drop_index("ux_messages_provider_message_id", table_name="messages")
        op.drop_index(op.f("ix_messages_provider_message_id"), table_name="messages")
        op.drop_index(op.f("ix_messages_provider"), table_name="messages")
        op.drop_column("messages", "provider_message_id")
        op.drop_column("messages", "provider")
        return

    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("messages")}
    indexes = {index["name"] for index in inspector.get_indexes("messages")}

    if "ux_messages_provider_message_id" in indexes:
        op.drop_index("ux_messages_provider_message_id", table_name="messages")
    if "ix_messages_provider_message_id" in indexes:
        op.drop_index(op.f("ix_messages_provider_message_id"), table_name="messages")
    if "ix_messages_provider" in indexes:
        op.drop_index(op.f("ix_messages_provider"), table_name="messages")
    if "provider_message_id" in columns:
        op.drop_column("messages", "provider_message_id")
    if "provider" in columns:
        op.drop_column("messages", "provider")
