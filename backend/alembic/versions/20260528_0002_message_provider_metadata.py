"""add provider metadata to messages

Revision ID: 20260528_0002
Revises: 20260528_0001
Create Date: 2026-05-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260528_0002"
down_revision: str | None = "20260528_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_index("ux_messages_provider_message_id", table_name="messages")
    op.drop_index(op.f("ix_messages_provider_message_id"), table_name="messages")
    op.drop_index(op.f("ix_messages_provider"), table_name="messages")
    op.drop_column("messages", "provider_message_id")
    op.drop_column("messages", "provider")
