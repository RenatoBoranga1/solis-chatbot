"""add webhook event and attachment storage

Revision ID: 20260529_0003
Revises: 20260528_0002
Create Date: 2026-05-29
"""

from collections.abc import Sequence

from alembic import context
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260529_0003"
down_revision: str | None = "20260528_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _ensure_message_provider_metadata()
    _ensure_webhook_events()
    _ensure_attachments()


def downgrade() -> None:
    if context.is_offline_mode():
        _drop_attachments_unchecked()
        _drop_webhook_events_unchecked()
        return

    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("attachments"):
        _drop_indexes_if_present("attachments", inspector)
        op.drop_table("attachments")
    if inspector.has_table("webhook_events"):
        _drop_indexes_if_present("webhook_events", inspector)
        op.drop_table("webhook_events")


def _ensure_message_provider_metadata() -> None:
    if context.is_offline_mode():
        return

    inspector = sa.inspect(op.get_bind())
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


def _ensure_webhook_events() -> None:
    if context.is_offline_mode():
        _create_webhook_events_unchecked()
        return

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("webhook_events"):
        _create_webhook_events_unchecked()
        return

    indexes = {index["name"] for index in inspector.get_indexes("webhook_events")}
    _create_index_if_missing("ix_webhook_events_event_id", "webhook_events", ["event_id"], indexes)
    _create_index_if_missing("ix_webhook_events_processed", "webhook_events", ["processed"], indexes)
    _create_index_if_missing("ix_webhook_events_provider", "webhook_events", ["provider"], indexes)
    _create_index_if_missing("ix_webhook_events_provider_event_id", "webhook_events", ["provider", "event_id"], indexes)


def _ensure_attachments() -> None:
    if context.is_offline_mode():
        _create_attachments_unchecked()
        return

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("attachments"):
        _create_attachments_unchecked()
        return

    indexes = {index["name"] for index in inspector.get_indexes("attachments")}
    _create_index_if_missing("ix_attachments_conversation_id", "attachments", ["conversation_id"], indexes)
    _create_index_if_missing("ix_attachments_file_type", "attachments", ["file_type"], indexes)
    _create_index_if_missing("ix_attachments_message_id", "attachments", ["message_id"], indexes)
    _create_index_if_missing("ix_attachments_provider", "attachments", ["provider"], indexes)
    _create_index_if_missing("ix_attachments_provider_media_id", "attachments", ["provider_media_id"], indexes)


def _create_webhook_events_unchecked() -> None:
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=60), nullable=False),
        sa.Column("event_id", sa.String(length=180), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_webhook_events_event_id"), "webhook_events", ["event_id"], unique=False)
    op.create_index(op.f("ix_webhook_events_processed"), "webhook_events", ["processed"], unique=False)
    op.create_index(op.f("ix_webhook_events_provider"), "webhook_events", ["provider"], unique=False)
    op.create_index(
        "ix_webhook_events_provider_event_id",
        "webhook_events",
        ["provider", "event_id"],
        unique=False,
    )


def _create_attachments_unchecked() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=60), nullable=False),
        sa.Column("provider_media_id", sa.String(length=180), nullable=True),
        sa.Column("file_type", sa.String(length=40), nullable=False),
        sa.Column("file_url", sa.String(length=800), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_attachments_conversation_id"), "attachments", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_attachments_file_type"), "attachments", ["file_type"], unique=False)
    op.create_index(op.f("ix_attachments_message_id"), "attachments", ["message_id"], unique=False)
    op.create_index(op.f("ix_attachments_provider"), "attachments", ["provider"], unique=False)
    op.create_index(op.f("ix_attachments_provider_media_id"), "attachments", ["provider_media_id"], unique=False)


def _drop_attachments_unchecked() -> None:
    op.drop_index(op.f("ix_attachments_provider_media_id"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_provider"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_message_id"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_file_type"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_conversation_id"), table_name="attachments")
    op.drop_table("attachments")


def _drop_webhook_events_unchecked() -> None:
    op.drop_index("ix_webhook_events_provider_event_id", table_name="webhook_events")
    op.drop_index(op.f("ix_webhook_events_provider"), table_name="webhook_events")
    op.drop_index(op.f("ix_webhook_events_processed"), table_name="webhook_events")
    op.drop_index(op.f("ix_webhook_events_event_id"), table_name="webhook_events")
    op.drop_table("webhook_events")


def _create_index_if_missing(name: str, table_name: str, columns: list[str], indexes: set[str]) -> None:
    if name not in indexes:
        op.create_index(name, table_name, columns, unique=False)


def _drop_indexes_if_present(table_name: str, inspector) -> None:
    for index in inspector.get_indexes(table_name):
        op.drop_index(index["name"], table_name=table_name)
