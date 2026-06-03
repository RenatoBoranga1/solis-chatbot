import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=utc_now)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(40), index=True, nullable=False, default="suporte")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str | None] = mapped_column(String(180))
    phone: Mapped[str | None] = mapped_column(String(40), index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(2))
    document: Mapped[str | None] = mapped_column(String(512))
    lgpd_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lgpd_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="customer")
    leads: Mapped[list["Lead"]] = relationship(back_populates="customer")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="customer")
    channel_links: Mapped[list["ConversationChannelLink"]] = relationship(back_populates="customer")
    proposals: Mapped[list["Proposal"]] = relationship(back_populates="customer")


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), index=True)
    channel: Mapped[str] = mapped_column(String(40), index=True, default="site")
    external_id: Mapped[str | None] = mapped_column(String(180), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True, default="open")
    intent: Mapped[str | None] = mapped_column(String(80), index=True)
    severity: Mapped[str | None] = mapped_column(String(20), index=True)
    assigned_to: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    summary: Mapped[str | None] = mapped_column(Text)
    collected_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    bot_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transferred_to_human: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    customer: Mapped[Customer | None] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    handoffs: Mapped[list["Handoff"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    ai_analyses: Mapped[list["AIAnalysis"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")
    outbound_channel_links: Mapped[list["ConversationChannelLink"]] = relationship(
        back_populates="source_conversation",
        cascade="all, delete-orphan",
        foreign_keys="ConversationChannelLink.source_conversation_id",
    )
    inbound_channel_links: Mapped[list["ConversationChannelLink"]] = relationship(
        back_populates="target_conversation",
        foreign_keys="ConversationChannelLink.target_conversation_id",
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ux_messages_provider_message_id", "provider", "provider_message_id", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    sender_type: Mapped[str] = mapped_column(String(20), index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_url: Mapped[str | None] = mapped_column(String(800))
    provider: Mapped[str | None] = mapped_column(String(60), index=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(180), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="message", cascade="all, delete-orphan")


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    provider: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    provider_media_id: Mapped[str | None] = mapped_column(String(180), index=True)
    file_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    file_url: Mapped[str | None] = mapped_column(String(800))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    message: Mapped[Message] = relationship(back_populates="attachments")
    conversation: Mapped[Conversation] = relationship(back_populates="attachments")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (
        Index("ix_webhook_events_provider_event_id", "provider", "event_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    provider: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    event_id: Mapped[str] = mapped_column(String(180), index=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AIAnalysis(Base, TimestampMixin):
    __tablename__ = "ai_analyses"
    __table_args__ = (
        Index("ix_ai_analyses_target", "analysis_type", "conversation_id", "lead_id", "ticket_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"), index=True)
    lead_id: Mapped[str | None] = mapped_column(ForeignKey("leads.id"), index=True)
    ticket_id: Mapped[str | None] = mapped_column(ForeignKey("tickets.id"), index=True)
    analysis_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    customer_intent: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    customer_sentiment: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    urgency_level: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    commercial_opportunity: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    conversion_probability: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    technical_risk: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    priority_score: Mapped[int] = mapped_column(Integer, index=True, default=0, nullable=False)
    missing_data: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    recommended_next_action: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_reply: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    raw_analysis: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    conversation: Mapped[Conversation | None] = relationship(back_populates="ai_analyses")
    lead: Mapped["Lead | None"] = relationship(back_populates="ai_analyses")
    ticket: Mapped["Ticket | None"] = relationship(back_populates="ai_analyses")


class ConversationChannelLink(Base):
    __tablename__ = "conversation_channel_links"
    __table_args__ = (
        Index("ix_conversation_channel_links_phone_status", "phone", "status"),
        Index("ix_conversation_channel_links_source_target", "source_conversation_id", "target_conversation_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True, nullable=False)
    source_conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True, nullable=False)
    target_conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"), index=True)
    source_channel: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    target_channel: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(180), index=True)
    phone: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    lead_id: Mapped[str | None] = mapped_column(ForeignKey("leads.id"), index=True)
    ticket_id: Mapped[str | None] = mapped_column(ForeignKey("tickets.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True, default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped[Customer] = relationship(back_populates="channel_links")
    source_conversation: Mapped[Conversation] = relationship(
        back_populates="outbound_channel_links",
        foreign_keys=[source_conversation_id],
    )
    target_conversation: Mapped[Conversation | None] = relationship(
        back_populates="inbound_channel_links",
        foreign_keys=[target_conversation_id],
    )
    lead: Mapped["Lead | None"] = relationship()
    ticket: Mapped["Ticket | None"] = relationship()


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"), index=True)
    property_type: Mapped[str | None] = mapped_column(String(80))
    average_bill: Mapped[float | None] = mapped_column(Numeric(12, 2))
    utility_company: Mapped[str | None] = mapped_column(String(120))
    roof_type: Mapped[str | None] = mapped_column(String(80))
    financing_interest: Mapped[bool | None] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(String(60), index=True, default="Novo orçamento")
    notes: Mapped[str | None] = mapped_column(Text)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    customer: Mapped[Customer] = relationship(back_populates="leads")
    ai_analyses: Mapped[list[AIAnalysis]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    proposals: Mapped[list["Proposal"]] = relationship(back_populates="lead")


class Ticket(Base, TimestampMixin):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    problem_type: Mapped[str] = mapped_column(String(120), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(60), index=True, default="Novo")
    technical_notes: Mapped[str | None] = mapped_column(Text)
    assigned_technician: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    customer: Mapped[Customer] = relationship(back_populates="tickets")
    ai_analyses: Mapped[list[AIAnalysis]] = relationship(back_populates="ticket", cascade="all, delete-orphan")


class Proposal(Base, TimestampMixin):
    __tablename__ = "proposals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), index=True)
    lead_id: Mapped[str | None] = mapped_column(ForeignKey("leads.id"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"), index=True)
    proposal_number: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), index=True, default="draft", nullable=False)
    customer_name: Mapped[str] = mapped_column(String(180), nullable=False)
    customer_phone: Mapped[str | None] = mapped_column(String(40))
    customer_email: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(120), index=True)
    state: Mapped[str | None] = mapped_column(String(2))
    property_type: Mapped[str | None] = mapped_column(String(80))
    average_bill: Mapped[float | None] = mapped_column(Numeric(12, 2))
    estimated_system_power_kwp: Mapped[float | None] = mapped_column(Numeric(12, 3))
    estimated_monthly_generation_kwh: Mapped[float | None] = mapped_column(Numeric(12, 2))
    estimated_savings_percentage: Mapped[float | None] = mapped_column(Numeric(5, 2))
    validity_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    internal_notes: Mapped[str | None] = mapped_column(Text)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    discount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    payment_conditions: Mapped[str | None] = mapped_column(Text)
    pdf_url: Mapped[str | None] = mapped_column(String(800))

    customer: Mapped[Customer | None] = relationship(back_populates="proposals")
    lead: Mapped[Lead | None] = relationship(back_populates="proposals")
    conversation: Mapped[Conversation | None] = relationship()
    items: Mapped[list["ProposalItem"]] = relationship(
        back_populates="proposal",
        cascade="all, delete-orphan",
        order_by="ProposalItem.sort_order",
    )
    share_links: Mapped[list["ProposalShareLink"]] = relationship(back_populates="proposal", cascade="all, delete-orphan")
    customer_responses: Mapped[list["ProposalCustomerResponse"]] = relationship(back_populates="proposal", cascade="all, delete-orphan")
    events: Mapped[list["ProposalEvent"]] = relationship(back_populates="proposal", cascade="all, delete-orphan")
    followups: Mapped[list["ProposalFollowUp"]] = relationship(back_populates="proposal", cascade="all, delete-orphan")


class ProposalItem(Base, TimestampMixin):
    __tablename__ = "proposal_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("proposals.id"), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), default=1, nullable=False)
    unit: Mapped[str] = mapped_column(String(40), default="un", nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    editable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    proposal: Mapped[Proposal] = relationship(back_populates="items")


class ProposalPriceItem(Base, TimestampMixin):
    __tablename__ = "proposal_price_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    category: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    default_unit: Mapped[str] = mapped_column(String(40), default="un", nullable=False)
    default_quantity: Mapped[float] = mapped_column(Numeric(12, 3), default=1, nullable=False)
    default_unit_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class ProposalShareLink(Base, TimestampMixin):
    __tablename__ = "proposal_share_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("proposals.id"), index=True, nullable=False)
    token: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    views_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)

    proposal: Mapped[Proposal] = relationship(back_populates="share_links")


class ProposalCustomerResponse(Base):
    __tablename__ = "proposal_customer_responses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("proposals.id"), index=True, nullable=False)
    share_link_id: Mapped[str] = mapped_column(ForeignKey("proposal_share_links.id"), index=True, nullable=False)
    response_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(180))
    customer_email: Mapped[str | None] = mapped_column(String(255))
    customer_phone: Mapped[str | None] = mapped_column(String(40))
    message: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(80))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    proposal: Mapped[Proposal] = relationship(back_populates="customer_responses")
    share_link: Mapped[ProposalShareLink] = relationship()


class ProposalEvent(Base):
    __tablename__ = "proposal_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("proposals.id"), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    channel: Mapped[str | None] = mapped_column(String(40), index=True)
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)

    proposal: Mapped[Proposal] = relationship(back_populates="events")


class ProposalFollowUp(Base, TimestampMixin):
    __tablename__ = "proposal_followups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("proposals.id"), index=True, nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), index=True, default="pending", nullable=False)
    channel: Mapped[str] = mapped_column(String(40), index=True, default="manual", nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    assigned_to: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    proposal: Mapped[Proposal] = relationship(back_populates="followups")


class CompanySettings(Base, TimestampMixin):
    __tablename__ = "company_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_name: Mapped[str] = mapped_column(String(180), nullable=False)
    company_phone: Mapped[str | None] = mapped_column(String(60))
    company_email: Mapped[str | None] = mapped_column(String(255))
    company_website: Mapped[str | None] = mapped_column(String(800))
    company_address: Mapped[str | None] = mapped_column(Text)
    company_logo_url: Mapped[str | None] = mapped_column(String(800))
    primary_color: Mapped[str] = mapped_column(String(20), default="#FFCC33", nullable=False)
    secondary_color: Mapped[str] = mapped_column(String(20), default="#0B1F33", nullable=False)
    default_payment_conditions: Mapped[str | None] = mapped_column(Text)
    default_proposal_validity_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    default_proposal_notes: Mapped[str | None] = mapped_column(Text)


class KnowledgeBaseArticle(Base, TimestampMixin):
    __tablename__ = "knowledge_base_articles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    keywords: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    video_url: Mapped[str | None] = mapped_column(String(800))
    video_title: Mapped[str | None] = mapped_column(String(220))
    resource_url: Mapped[str | None] = mapped_column(String(800))
    resource_title: Mapped[str | None] = mapped_column(String(220))
    resource_type: Mapped[str | None] = mapped_column(String(60))
    send_video_with_answer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    send_resource_with_answer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    use_for_ai: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Handoff(Base):
    __tablename__ = "handoffs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    reason: Mapped[str] = mapped_column(String(180), nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="handoffs")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class UnansweredQuestion(Base):
    __tablename__ = "unanswered_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"), index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    detected_intent: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="new", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), index=True)
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
