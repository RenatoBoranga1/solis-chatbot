from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Channel = Literal["site", "whatsapp", "instagram", "facebook", "admin"]
SenderType = Literal["customer", "bot", "human"]
Severity = Literal["baixa", "media", "alta"]
AnalysisType = Literal["conversation", "lead", "ticket", "daily_dashboard"]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerIn(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    city: str | None = None
    state: str | None = Field(default=None, max_length=2)
    document: str | None = None
    lgpd_consent: bool = False


class CustomerOut(BaseModel):
    id: str
    name: str | None
    phone: str | None
    email: EmailStr | None
    city: str | None
    state: str | None
    lgpd_consent: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatMessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    channel: Channel = "site"
    conversation_id: str | None = None
    customer_id: str | None = None
    external_id: str | None = None
    provider: str | None = None
    provider_message_id: str | None = None
    attachment_url: str | None = None
    media_id: str | None = None
    media_type: str | None = None
    customer: CustomerIn | None = None


class QuickReply(BaseModel):
    label: str
    value: str


class ChatMessageOut(BaseModel):
    conversation_id: str
    customer_id: str | None
    response: str
    intent: str | None
    severity: str | None
    status: str
    handoff_required: bool = False
    created_lead_id: str | None = None
    created_ticket_id: str | None = None
    next_question_key: str | None = None
    quick_replies: list[QuickReply] = Field(default_factory=list)
    summary: str | None = None


class MessageOut(BaseModel):
    id: str
    sender_type: str
    content: str
    attachment_url: str | None
    provider: str | None = None
    provider_message_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationOut(BaseModel):
    id: str
    customer_id: str | None
    channel: str
    status: str
    intent: str | None
    severity: str | None
    assigned_to: str | None
    summary: str | None
    collected_data: dict[str, Any]
    bot_resolved: bool
    transferred_to_human: bool
    created_at: datetime
    updated_at: datetime | None
    messages: list[MessageOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AssignIn(BaseModel):
    user_id: str | None = None


class HandoffIn(BaseModel):
    reason: str = Field(min_length=2, max_length=180)
    assigned_to: str | None = None


class LeadIn(BaseModel):
    customer_id: str
    conversation_id: str | None = None
    property_type: str | None = None
    average_bill: float | None = None
    utility_company: str | None = None
    roof_type: str | None = None
    financing_interest: bool | None = None
    status: str = "Novo orçamento"
    notes: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class LeadOut(LeadIn):
    id: str
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class LeadUpdate(BaseModel):
    property_type: str | None = None
    average_bill: float | None = None
    utility_company: str | None = None
    roof_type: str | None = None
    financing_interest: bool | None = None
    status: str | None = None
    notes: str | None = None
    extra: dict[str, Any] | None = None


class StatusPatch(BaseModel):
    status: str = Field(min_length=2, max_length=80)


class SeverityPatch(BaseModel):
    severity: Severity


class TicketIn(BaseModel):
    customer_id: str
    conversation_id: str
    problem_type: str
    severity: Severity = "baixa"
    status: str = "Novo"
    technical_notes: str | None = None
    assigned_technician: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class TicketOut(TicketIn):
    id: str
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TicketUpdate(BaseModel):
    problem_type: str | None = None
    severity: Severity | None = None
    status: str | None = None
    technical_notes: str | None = None
    assigned_technician: str | None = None
    extra: dict[str, Any] | None = None


class KnowledgeIn(BaseModel):
    title: str
    question: str
    answer: str
    category: str
    keywords: list[str] = Field(default_factory=list)
    active: bool = True
    use_for_ai: bool = True


class KnowledgeOut(KnowledgeIn):
    id: str
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class DashboardMetrics(BaseModel):
    total_atendimentos: int
    leads_orcamento: int
    chamados_abertos: int
    baixa_gravidade: int
    media_gravidade: int
    alta_gravidade: int
    resolvidos_pelo_bot: int
    transferidos_para_humano: int
    taxa_conversao_orcamento: float
    satisfacao_media: float | None


class AIAnalysisOut(BaseModel):
    id: str
    conversation_id: str | None
    lead_id: str | None
    ticket_id: str | None
    analysis_type: AnalysisType
    executive_summary: str
    customer_intent: str
    customer_sentiment: str
    urgency_level: str
    commercial_opportunity: str
    conversion_probability: str
    technical_risk: str
    priority_score: int
    missing_data: list[str]
    recommended_next_action: str
    suggested_reply: str
    tags: list[str]
    raw_analysis: dict[str, Any]
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SuggestedReplyOut(BaseModel):
    conversation_id: str
    suggested_reply: str


class DashboardAIInsights(BaseModel):
    leads_quentes: int
    chamados_criticos: int
    clientes_irritados: int
    oportunidades_financiamento: int
    problemas_tecnicos_recorrentes: list[str] = Field(default_factory=list)
    principais_motivos: list[str] = Field(default_factory=list)
    principais_cidades: list[str] = Field(default_factory=list)
    taxa_handoff: float
    recomendacoes: list[str] = Field(default_factory=list)
