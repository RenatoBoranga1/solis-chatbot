"""add multimedia resources to knowledge base

Revision ID: 20260529_0005
Revises: 20260529_0004
Create Date: 2026-05-29
"""

from collections.abc import Sequence

from alembic import context
from alembic import op
import sqlalchemy as sa

revision: str = "20260529_0005"
down_revision: str | None = "20260529_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        _add_columns_unchecked()
        return

    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("knowledge_base_articles")}

    if "video_url" not in columns:
        op.add_column("knowledge_base_articles", sa.Column("video_url", sa.String(length=800), nullable=True))
    if "video_title" not in columns:
        op.add_column("knowledge_base_articles", sa.Column("video_title", sa.String(length=220), nullable=True))
    if "resource_url" not in columns:
        op.add_column("knowledge_base_articles", sa.Column("resource_url", sa.String(length=800), nullable=True))
    if "resource_title" not in columns:
        op.add_column("knowledge_base_articles", sa.Column("resource_title", sa.String(length=220), nullable=True))
    if "resource_type" not in columns:
        op.add_column("knowledge_base_articles", sa.Column("resource_type", sa.String(length=60), nullable=True))
    if "send_video_with_answer" not in columns:
        op.add_column(
            "knowledge_base_articles",
            sa.Column("send_video_with_answer", sa.Boolean(), server_default=sa.false(), nullable=False),
        )
        op.alter_column("knowledge_base_articles", "send_video_with_answer", server_default=None)
    if "send_resource_with_answer" not in columns:
        op.add_column(
            "knowledge_base_articles",
            sa.Column("send_resource_with_answer", sa.Boolean(), server_default=sa.false(), nullable=False),
        )
        op.alter_column("knowledge_base_articles", "send_resource_with_answer", server_default=None)


def downgrade() -> None:
    if context.is_offline_mode():
        for column in reversed(_column_names()):
            op.drop_column("knowledge_base_articles", column)
        return

    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("knowledge_base_articles")}
    for column in reversed(_column_names()):
        if column in columns:
            op.drop_column("knowledge_base_articles", column)


def _add_columns_unchecked() -> None:
    op.add_column("knowledge_base_articles", sa.Column("video_url", sa.String(length=800), nullable=True))
    op.add_column("knowledge_base_articles", sa.Column("video_title", sa.String(length=220), nullable=True))
    op.add_column("knowledge_base_articles", sa.Column("resource_url", sa.String(length=800), nullable=True))
    op.add_column("knowledge_base_articles", sa.Column("resource_title", sa.String(length=220), nullable=True))
    op.add_column("knowledge_base_articles", sa.Column("resource_type", sa.String(length=60), nullable=True))
    op.add_column(
        "knowledge_base_articles",
        sa.Column("send_video_with_answer", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "knowledge_base_articles",
        sa.Column("send_resource_with_answer", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def _column_names() -> list[str]:
    return [
        "video_url",
        "video_title",
        "resource_url",
        "resource_title",
        "resource_type",
        "send_video_with_answer",
        "send_resource_with_answer",
    ]
