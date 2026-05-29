"""add ai analysis records

Revision ID: 20260529_0004
Revises: 20260529_0003
Create Date: 2026-05-29
"""

from collections.abc import Sequence

from alembic import context
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260529_0004"
down_revision: str | None = "20260529_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        _create_ai_analyses_unchecked()
        return

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("ai_analyses"):
        _create_ai_analyses_unchecked()
        return

    indexes = {index["name"] for index in inspector.get_indexes("ai_analyses")}
    _create_index_if_missing("ix_ai_analyses_analysis_type", ["analysis_type"], indexes)
    _create_index_if_missing("ix_ai_analyses_conversation_id", ["conversation_id"], indexes)
    _create_index_if_missing("ix_ai_analyses_customer_intent", ["customer_intent"], indexes)
    _create_index_if_missing("ix_ai_analyses_customer_sentiment", ["customer_sentiment"], indexes)
    _create_index_if_missing("ix_ai_analyses_lead_id", ["lead_id"], indexes)
    _create_index_if_missing("ix_ai_analyses_priority_score", ["priority_score"], indexes)
    _create_index_if_missing("ix_ai_analyses_technical_risk", ["technical_risk"], indexes)
    _create_index_if_missing("ix_ai_analyses_ticket_id", ["ticket_id"], indexes)
    _create_index_if_missing("ix_ai_analyses_urgency_level", ["urgency_level"], indexes)
    _create_index_if_missing("ix_ai_analyses_target", ["analysis_type", "conversation_id", "lead_id", "ticket_id"], indexes)


def downgrade() -> None:
    if context.is_offline_mode():
        _drop_ai_analyses_unchecked()
        return

    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("ai_analyses"):
        for index in inspector.get_indexes("ai_analyses"):
            op.drop_index(index["name"], table_name="ai_analyses")
        op.drop_table("ai_analyses")


def _create_ai_analyses_unchecked() -> None:
    op.create_table(
        "ai_analyses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=True),
        sa.Column("lead_id", sa.String(length=36), nullable=True),
        sa.Column("ticket_id", sa.String(length=36), nullable=True),
        sa.Column("analysis_type", sa.String(length=40), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("customer_intent", sa.String(length=80), nullable=False),
        sa.Column("customer_sentiment", sa.String(length=40), nullable=False),
        sa.Column("urgency_level", sa.String(length=40), nullable=False),
        sa.Column("commercial_opportunity", sa.String(length=40), nullable=False),
        sa.Column("conversion_probability", sa.String(length=40), nullable=False),
        sa.Column("technical_risk", sa.String(length=40), nullable=False),
        sa.Column("priority_score", sa.Integer(), nullable=False),
        sa.Column("missing_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommended_next_action", sa.Text(), nullable=False),
        sa.Column("suggested_reply", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_analyses_analysis_type"), "ai_analyses", ["analysis_type"], unique=False)
    op.create_index(op.f("ix_ai_analyses_conversation_id"), "ai_analyses", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_ai_analyses_customer_intent"), "ai_analyses", ["customer_intent"], unique=False)
    op.create_index(op.f("ix_ai_analyses_customer_sentiment"), "ai_analyses", ["customer_sentiment"], unique=False)
    op.create_index(op.f("ix_ai_analyses_lead_id"), "ai_analyses", ["lead_id"], unique=False)
    op.create_index(op.f("ix_ai_analyses_priority_score"), "ai_analyses", ["priority_score"], unique=False)
    op.create_index(op.f("ix_ai_analyses_technical_risk"), "ai_analyses", ["technical_risk"], unique=False)
    op.create_index(op.f("ix_ai_analyses_ticket_id"), "ai_analyses", ["ticket_id"], unique=False)
    op.create_index(op.f("ix_ai_analyses_urgency_level"), "ai_analyses", ["urgency_level"], unique=False)
    op.create_index(
        "ix_ai_analyses_target",
        "ai_analyses",
        ["analysis_type", "conversation_id", "lead_id", "ticket_id"],
        unique=False,
    )


def _drop_ai_analyses_unchecked() -> None:
    op.drop_index("ix_ai_analyses_target", table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_urgency_level"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_ticket_id"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_technical_risk"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_priority_score"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_lead_id"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_customer_sentiment"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_customer_intent"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_conversation_id"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_analysis_type"), table_name="ai_analyses")
    op.drop_table("ai_analyses")


def _create_index_if_missing(name: str, columns: list[str], indexes: set[str]) -> None:
    if name not in indexes:
        op.create_index(name, "ai_analyses", columns, unique=False)
