"""add proposal sharing, followups, events and company settings

Revision ID: 20260602_0009
Revises: 20260601_0008
Create Date: 2026-06-02
"""

from collections.abc import Sequence

from alembic import context
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260602_0009"
down_revision: str | None = "20260601_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if context.is_offline_mode():
        _create_tables()
        return

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("proposal_share_links"):
        _create_share_links()
    if not inspector.has_table("proposal_customer_responses"):
        _create_customer_responses()
    if not inspector.has_table("proposal_events"):
        _create_events()
    if not inspector.has_table("proposal_followups"):
        _create_followups()
    if not inspector.has_table("company_settings"):
        _create_company_settings()


def downgrade() -> None:
    if context.is_offline_mode():
        _drop_tables()
        return

    inspector = sa.inspect(op.get_bind())
    for table in [
        "company_settings",
        "proposal_followups",
        "proposal_events",
        "proposal_customer_responses",
        "proposal_share_links",
    ]:
        if inspector.has_table(table):
            for index in inspector.get_indexes(table):
                op.drop_index(index["name"], table_name=table)
            op.drop_table(table)


def _create_tables() -> None:
    _create_share_links()
    _create_customer_responses()
    _create_events()
    _create_followups()
    _create_company_settings()


def _create_share_links() -> None:
    op.create_table(
        "proposal_share_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("proposal_id", sa.String(length=36), nullable=False),
        sa.Column("token", sa.String(length=160), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("views_count", sa.Integer(), nullable=False),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["proposal_id"], ["proposals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_proposal_share_links_created_by"), "proposal_share_links", ["created_by"], unique=False)
    op.create_index(op.f("ix_proposal_share_links_expires_at"), "proposal_share_links", ["expires_at"], unique=False)
    op.create_index(op.f("ix_proposal_share_links_proposal_id"), "proposal_share_links", ["proposal_id"], unique=False)
    op.create_index(op.f("ix_proposal_share_links_revoked_at"), "proposal_share_links", ["revoked_at"], unique=False)
    op.create_index(op.f("ix_proposal_share_links_token"), "proposal_share_links", ["token"], unique=True)


def _create_customer_responses() -> None:
    op.create_table(
        "proposal_customer_responses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("proposal_id", sa.String(length=36), nullable=False),
        sa.Column("share_link_id", sa.String(length=36), nullable=False),
        sa.Column("response_type", sa.String(length=40), nullable=False),
        sa.Column("customer_name", sa.String(length=180), nullable=True),
        sa.Column("customer_email", sa.String(length=255), nullable=True),
        sa.Column("customer_phone", sa.String(length=40), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=80), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["proposal_id"], ["proposals.id"]),
        sa.ForeignKeyConstraint(["share_link_id"], ["proposal_share_links.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_proposal_customer_responses_proposal_id"), "proposal_customer_responses", ["proposal_id"], unique=False)
    op.create_index(op.f("ix_proposal_customer_responses_response_type"), "proposal_customer_responses", ["response_type"], unique=False)
    op.create_index(op.f("ix_proposal_customer_responses_share_link_id"), "proposal_customer_responses", ["share_link_id"], unique=False)


def _create_events() -> None:
    op.create_table(
        "proposal_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("proposal_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["proposal_id"], ["proposals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_proposal_events_channel"), "proposal_events", ["channel"], unique=False)
    op.create_index(op.f("ix_proposal_events_created_at"), "proposal_events", ["created_at"], unique=False)
    op.create_index(op.f("ix_proposal_events_event_type"), "proposal_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_proposal_events_proposal_id"), "proposal_events", ["proposal_id"], unique=False)


def _create_followups() -> None:
    op.create_table(
        "proposal_followups",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("proposal_id", sa.String(length=36), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.String(length=36), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"]),
        sa.ForeignKeyConstraint(["proposal_id"], ["proposals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_proposal_followups_assigned_to"), "proposal_followups", ["assigned_to"], unique=False)
    op.create_index(op.f("ix_proposal_followups_channel"), "proposal_followups", ["channel"], unique=False)
    op.create_index(op.f("ix_proposal_followups_due_at"), "proposal_followups", ["due_at"], unique=False)
    op.create_index(op.f("ix_proposal_followups_proposal_id"), "proposal_followups", ["proposal_id"], unique=False)
    op.create_index(op.f("ix_proposal_followups_status"), "proposal_followups", ["status"], unique=False)


def _create_company_settings() -> None:
    op.create_table(
        "company_settings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_name", sa.String(length=180), nullable=False),
        sa.Column("company_phone", sa.String(length=60), nullable=True),
        sa.Column("company_email", sa.String(length=255), nullable=True),
        sa.Column("company_website", sa.String(length=800), nullable=True),
        sa.Column("company_address", sa.Text(), nullable=True),
        sa.Column("company_logo_url", sa.String(length=800), nullable=True),
        sa.Column("primary_color", sa.String(length=20), nullable=False),
        sa.Column("secondary_color", sa.String(length=20), nullable=False),
        sa.Column("default_payment_conditions", sa.Text(), nullable=True),
        sa.Column("default_proposal_validity_days", sa.Integer(), nullable=False),
        sa.Column("default_proposal_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def _drop_tables() -> None:
    op.drop_table("company_settings")
    op.drop_index(op.f("ix_proposal_followups_status"), table_name="proposal_followups")
    op.drop_index(op.f("ix_proposal_followups_proposal_id"), table_name="proposal_followups")
    op.drop_index(op.f("ix_proposal_followups_due_at"), table_name="proposal_followups")
    op.drop_index(op.f("ix_proposal_followups_channel"), table_name="proposal_followups")
    op.drop_index(op.f("ix_proposal_followups_assigned_to"), table_name="proposal_followups")
    op.drop_table("proposal_followups")
    op.drop_index(op.f("ix_proposal_events_proposal_id"), table_name="proposal_events")
    op.drop_index(op.f("ix_proposal_events_event_type"), table_name="proposal_events")
    op.drop_index(op.f("ix_proposal_events_created_at"), table_name="proposal_events")
    op.drop_index(op.f("ix_proposal_events_channel"), table_name="proposal_events")
    op.drop_table("proposal_events")
    op.drop_index(op.f("ix_proposal_customer_responses_share_link_id"), table_name="proposal_customer_responses")
    op.drop_index(op.f("ix_proposal_customer_responses_response_type"), table_name="proposal_customer_responses")
    op.drop_index(op.f("ix_proposal_customer_responses_proposal_id"), table_name="proposal_customer_responses")
    op.drop_table("proposal_customer_responses")
    op.drop_index(op.f("ix_proposal_share_links_token"), table_name="proposal_share_links")
    op.drop_index(op.f("ix_proposal_share_links_revoked_at"), table_name="proposal_share_links")
    op.drop_index(op.f("ix_proposal_share_links_proposal_id"), table_name="proposal_share_links")
    op.drop_index(op.f("ix_proposal_share_links_expires_at"), table_name="proposal_share_links")
    op.drop_index(op.f("ix_proposal_share_links_created_by"), table_name="proposal_share_links")
    op.drop_table("proposal_share_links")
