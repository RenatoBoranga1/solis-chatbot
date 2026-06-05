from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.urls import validate_safe_url

Channel = Literal["site", "whatsapp", "instagram", "facebook", "admin"]
SenderType = Literal["customer", "bot", "human"]
Severity = Literal["baixa", "media", "alta"]
AnalysisType = Literal["conversation", "lead", "ticket", "daily_dashboard"]
EnergyBillExtractionStatus = Literal[
    "pending",
    "processing",
    "extracted",
    "needs_review",
    "confirmed",
    "failed",
    "discarded",
]
ProposalStatus = Literal[
    "draft",
    "under_review",
    "approved",
    "ready_to_send",
    "sent",
    "accepted",
    "rejected",
    "expired",
    "canceled",
]


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


class ChatAttachmentOut(BaseModel):
    attachment_url: str
    file_name: str
    media_type: str


class MessageOut(BaseModel):
    id: str
    sender_type: str
    content: str
    attachment_url: str | None
    provider: str | None = None
    provider_message_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationChannelLinkOut(BaseModel):
    id: str
    customer_id: str
    source_conversation_id: str
    target_conversation_id: str | None
    source_channel: str
    target_channel: str
    external_id: str | None
    phone: str
    lead_id: str | None
    ticket_id: str | None
    status: str
    created_at: datetime
    confirmed_at: datetime | None

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
    outbound_channel_links: list[ConversationChannelLinkOut] = Field(default_factory=list)
    inbound_channel_links: list[ConversationChannelLinkOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AssignIn(BaseModel):
    user_id: str | None = None


class HandoffIn(BaseModel):
    reason: str = Field(min_length=2, max_length=180)
    assigned_to: str | None = None


class ContinueWhatsAppIn(BaseModel):
    template_name: str = Field(default="continuar_atendimento_site", max_length=120)
    custom_message: str | None = Field(default=None, max_length=1200)
    review_confirmed: bool = False


class ContinueWhatsAppOut(BaseModel):
    status: str
    conversation_channel_link_id: str
    phone: str
    message: str
    target_conversation_id: str | None = None


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


class EnergyBillHistoryIn(BaseModel):
    period: str = Field(max_length=20)
    consumption_kwh: float
    bill_amount: float | None = None


class EnergyBillHistoryOut(EnergyBillHistoryIn):
    id: str
    extraction_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EnergyBillParsedData(BaseModel):
    distributor: str | None = None
    customer_name: str | None = None
    customer_document_masked: str | None = None
    installation_number: str | None = None
    customer_address: str | None = None
    customer_district: str | None = None
    customer_postal_code: str | None = None
    customer_unit_number: str | None = None
    tariff_flag: str | None = None
    city: str | None = None
    state: str | None = None
    reference_month: str | None = None
    due_date: str | None = None
    current_consumption_kwh: float | None = None
    current_bill_amount: float | None = None
    average_consumption_kwh: float | None = None
    average_bill_amount: float | None = None
    min_consumption_kwh: float | None = None
    max_consumption_kwh: float | None = None
    estimated_system_power_kwp: float | None = None
    estimated_monthly_generation_kwh: float | None = None
    estimated_monthly_savings: float | None = None
    confidence_score: float = 0
    needs_human_review: bool = True
    missing_fields: list[str] = Field(default_factory=list)
    parsed_fields: dict[str, Any] = Field(default_factory=dict)
    history: list[EnergyBillHistoryIn] = Field(default_factory=list)


class EnergyBillParseTextIn(BaseModel):
    raw_text: str = Field(min_length=1, max_length=60000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EnergyBillExtractionUpdate(BaseModel):
    status: EnergyBillExtractionStatus | None = None
    origin: str | None = Field(default=None, max_length=40)
    distributor: str | None = None
    customer_name: str | None = None
    customer_document_masked: str | None = None
    installation_number: str | None = None
    customer_address: str | None = None
    customer_district: str | None = None
    customer_postal_code: str | None = None
    customer_unit_number: str | None = None
    tariff_flag: str | None = None
    city: str | None = None
    state: str | None = Field(default=None, max_length=2)
    reference_month: str | None = None
    due_date: str | None = None
    current_consumption_kwh: float | None = None
    current_bill_amount: float | None = None
    average_consumption_kwh: float | None = None
    average_bill_amount: float | None = None
    min_consumption_kwh: float | None = None
    max_consumption_kwh: float | None = None
    estimated_system_power_kwp: float | None = None
    estimated_monthly_generation_kwh: float | None = None
    estimated_monthly_savings: float | None = None
    confidence_score: float | None = None
    needs_human_review: bool | None = None
    missing_fields: list[str] | None = None
    parsed_fields: dict[str, Any] | None = None
    history: list[EnergyBillHistoryIn] | None = None


class EnergyBillExtractionConfirm(BaseModel):
    distributor: str | None = None
    customer_name: str | None = None
    installation_number: str | None = None
    customer_address: str | None = None
    customer_district: str | None = None
    customer_postal_code: str | None = None
    customer_unit_number: str | None = None
    tariff_flag: str | None = None
    city: str | None = None
    state: str | None = Field(default=None, max_length=2)
    reference_month: str | None = None
    due_date: str | None = None
    current_consumption_kwh: float | None = None
    current_bill_amount: float | None = None
    average_consumption_kwh: float | None = None
    average_bill_amount: float | None = None
    history: list[EnergyBillHistoryIn] | None = None


class EnergyBillExtractionOut(BaseModel):
    id: str
    conversation_id: str | None
    customer_id: str | None
    lead_id: str | None
    attachment_id: str | None
    status: str
    source: str
    origin: str
    file_name: str | None
    file_type: str | None
    file_url: str | None
    distributor: str | None
    customer_name: str | None
    customer_document_masked: str | None
    installation_number: str | None
    customer_address: str | None
    customer_district: str | None
    customer_postal_code: str | None
    customer_unit_number: str | None
    tariff_flag: str | None
    city: str | None
    state: str | None
    reference_month: str | None
    due_date: str | None
    current_consumption_kwh: float | None
    current_bill_amount: float | None
    average_consumption_kwh: float | None
    average_bill_amount: float | None
    min_consumption_kwh: float | None
    max_consumption_kwh: float | None
    estimated_system_power_kwp: float | None
    estimated_monthly_generation_kwh: float | None
    estimated_monthly_savings: float | None
    confidence_score: float
    needs_human_review: bool
    missing_fields: list[str]
    parsed_fields: dict[str, Any]
    raw_extraction: dict[str, Any]
    raw_text_excerpt: str | None
    error_message: str | None
    confirmed_by: str | None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime | None
    history: list[EnergyBillHistoryOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


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
    video_url: str | None = None
    video_title: str | None = None
    resource_url: str | None = None
    resource_title: str | None = None
    resource_type: str | None = None
    send_video_with_answer: bool = False
    send_resource_with_answer: bool = False
    active: bool = True
    use_for_ai: bool = True

    @field_validator("video_url", "resource_url")
    @classmethod
    def safe_url(cls, value: str | None) -> str | None:
        try:
            return validate_safe_url(value)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


class KnowledgeOut(KnowledgeIn):
    id: str
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ProposalMetrics(BaseModel):
    created: int = 0
    sent: int = 0
    accepted: int = 0
    rejected: int = 0
    open: int = 0
    viewed: int = 0
    pending_followups: int = 0
    overdue_followups: int = 0
    total_pipeline_value: float = 0
    accepted_value: float = 0
    average_ticket: float = 0
    conversion_rate: float = 0
    leads_without_proposal: int = 0


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
    proposal_metrics: ProposalMetrics | None = None


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


class ProposalItemBase(BaseModel):
    category: str
    description: str
    quantity: float = 1
    unit: str = "un"
    unit_price: float = 0
    total_price: float | None = None
    editable: bool = True
    sort_order: int = 0


class ProposalItemCreate(ProposalItemBase):
    pass


class ProposalItemUpdate(BaseModel):
    category: str | None = None
    description: str | None = None
    quantity: float | None = None
    unit: str | None = None
    unit_price: float | None = None
    editable: bool | None = None
    sort_order: int | None = None


class ProposalItemOut(ProposalItemBase):
    id: str
    proposal_id: str
    total_price: float
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ProposalPriceItemBase(BaseModel):
    category: str
    description: str
    default_unit: str = "un"
    default_quantity: float = 1
    default_unit_price: float = 0
    active: bool = True
    sort_order: int = 0
    notes: str | None = None


class ProposalPriceItemCreate(ProposalPriceItemBase):
    pass


class ProposalPriceItemUpdate(BaseModel):
    category: str | None = None
    description: str | None = None
    default_unit: str | None = None
    default_quantity: float | None = None
    default_unit_price: float | None = None
    active: bool | None = None
    sort_order: int | None = None
    notes: str | None = None


class ProposalPriceItemOut(ProposalPriceItemBase):
    id: str
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ProposalPriceItemActivePatch(BaseModel):
    active: bool


class ProposalKitItemBase(BaseModel):
    category: str
    description: str
    quantity: float = 1
    unit: str = "un"
    unit_price: float = 0
    total_price: float | None = None
    sort_order: int = 0


class ProposalKitItemCreate(ProposalKitItemBase):
    pass


class ProposalKitItemUpdate(BaseModel):
    category: str | None = None
    description: str | None = None
    quantity: float | None = None
    unit: str | None = None
    unit_price: float | None = None
    sort_order: int | None = None


class ProposalKitItemOut(ProposalKitItemBase):
    id: str
    kit_id: str
    total_price: float
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ProposalKitBase(BaseModel):
    name: str = Field(max_length=180)
    description: str | None = None
    min_monthly_consumption_kwh: float | None = None
    max_monthly_consumption_kwh: float | None = None
    min_power_kwp: float | None = None
    max_power_kwp: float | None = None
    suggested_power_kwp: float
    estimated_monthly_generation_kwh: float | None = None
    module_count: int | None = None
    module_power_wp: int | None = None
    inverter_power_kw: float | None = None
    base_price: float = 0
    active: bool = True
    sort_order: int = 0
    notes: str | None = None


class ProposalKitCreate(ProposalKitBase):
    items: list[ProposalKitItemCreate] = Field(default_factory=list)


class ProposalKitUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=180)
    description: str | None = None
    min_monthly_consumption_kwh: float | None = None
    max_monthly_consumption_kwh: float | None = None
    min_power_kwp: float | None = None
    max_power_kwp: float | None = None
    suggested_power_kwp: float | None = None
    estimated_monthly_generation_kwh: float | None = None
    module_count: int | None = None
    module_power_wp: int | None = None
    inverter_power_kw: float | None = None
    base_price: float | None = None
    active: bool | None = None
    sort_order: int | None = None
    notes: str | None = None


class ProposalKitOut(ProposalKitBase):
    id: str
    created_at: datetime
    updated_at: datetime | None
    items: list[ProposalKitItemOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ProposalKitActivePatch(BaseModel):
    active: bool


class ProposalKitSimulationIn(BaseModel):
    average_bill: float | None = None
    estimated_monthly_generation_kwh: float | None = None
    estimated_power_kwp: float | None = None


class ProposalKitSimulationOut(BaseModel):
    average_bill: float | None
    estimated_monthly_generation_kwh: float | None
    estimated_power_kwp: float | None
    selected_kit: ProposalKitOut | None
    selection_reason: str | None


ProposalCustomerResponseType = Literal[
    "interested",
    "request_changes",
    "accepted",
    "rejected",
    "talk_to_consultant",
]
ProposalFollowUpStatus = Literal["pending", "completed", "canceled", "overdue"]
ProposalFollowUpChannel = Literal["whatsapp", "email", "phone", "manual"]


class ProposalShareLinkCreate(BaseModel):
    expires_in_days: int = Field(default=15, ge=1, le=90)


class ProposalShareLinkOut(BaseModel):
    id: str
    proposal_id: str
    token: str
    expires_at: datetime
    revoked_at: datetime | None
    views_count: int
    last_viewed_at: datetime | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime | None
    public_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProposalCustomerResponseIn(BaseModel):
    response_type: ProposalCustomerResponseType
    customer_name: str | None = Field(default=None, max_length=180)
    customer_email: EmailStr | None = None
    customer_phone: str | None = Field(default=None, max_length=40)
    message: str | None = Field(default=None, max_length=2000)


class ProposalCustomerResponseOut(BaseModel):
    id: str
    proposal_id: str
    share_link_id: str
    response_type: str
    customer_name: str | None
    customer_email: EmailStr | None
    customer_phone: str | None
    message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProposalEventOut(BaseModel):
    id: str
    proposal_id: str
    event_type: str
    channel: str | None
    details: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProposalFollowUpCreate(BaseModel):
    due_at: datetime
    channel: ProposalFollowUpChannel = "manual"
    note: str | None = Field(default=None, max_length=2000)
    assigned_to: str | None = None


class ProposalFollowUpOut(BaseModel):
    id: str
    proposal_id: str
    due_at: datetime
    status: str
    channel: str
    note: str | None
    assigned_to: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class CompanySettingsIn(BaseModel):
    company_name: str = Field(default="Solar Solucoes", max_length=180)
    company_phone: str | None = Field(default=None, max_length=60)
    company_email: EmailStr | None = None
    company_website: str | None = None
    company_address: str | None = None
    company_logo_url: str | None = None
    primary_color: str = Field(default="#FFCC33", max_length=20)
    secondary_color: str = Field(default="#0B1F33", max_length=20)
    default_payment_conditions: str | None = None
    default_proposal_validity_days: int = Field(default=7, ge=1, le=90)
    default_proposal_notes: str | None = None

    @field_validator("company_website", "company_logo_url")
    @classmethod
    def safe_company_url(cls, value: str | None) -> str | None:
        try:
            return validate_safe_url(value)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


class CompanySettingsOut(CompanySettingsIn):
    id: str
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ProposalBase(BaseModel):
    customer_id: str | None = None
    lead_id: str | None = None
    conversation_id: str | None = None
    proposal_number: str | None = None
    status: ProposalStatus = "draft"
    customer_name: str
    customer_phone: str | None = None
    customer_email: EmailStr | None = None
    city: str | None = None
    state: str | None = Field(default=None, max_length=2)
    property_type: str | None = None
    average_bill: float | None = None
    estimated_system_power_kwp: float | None = None
    estimated_monthly_generation_kwh: float | None = None
    estimated_savings_percentage: float | None = None
    recommended_kit_id: str | None = None
    recommended_kit_name: str | None = None
    kit_selection_reason: str | None = None
    validity_days: int = 7
    notes: str | None = None
    internal_notes: str | None = None
    subtotal: float = 0
    discount: float = 0
    total_amount: float = 0
    payment_conditions: str | None = None
    pdf_url: str | None = None


class ProposalCreate(ProposalBase):
    items: list[ProposalItemCreate] = Field(default_factory=list)


class ProposalUpdate(BaseModel):
    status: ProposalStatus | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_email: EmailStr | None = None
    city: str | None = None
    state: str | None = Field(default=None, max_length=2)
    property_type: str | None = None
    average_bill: float | None = None
    estimated_system_power_kwp: float | None = None
    estimated_monthly_generation_kwh: float | None = None
    estimated_savings_percentage: float | None = None
    recommended_kit_id: str | None = None
    recommended_kit_name: str | None = None
    kit_selection_reason: str | None = None
    validity_days: int | None = None
    notes: str | None = None
    internal_notes: str | None = None
    discount: float | None = None
    payment_conditions: str | None = None


class ProposalOut(ProposalBase):
    id: str
    proposal_number: str
    subtotal: float
    total_amount: float
    created_at: datetime
    updated_at: datetime | None
    items: list[ProposalItemOut] = Field(default_factory=list)
    share_links: list[ProposalShareLinkOut] = Field(default_factory=list)
    events: list[ProposalEventOut] = Field(default_factory=list)
    followups: list[ProposalFollowUpOut] = Field(default_factory=list)
    customer_responses: list[ProposalCustomerResponseOut] = Field(default_factory=list)
    recommended_kit: ProposalKitOut | None = None

    model_config = ConfigDict(from_attributes=True)


class ProposalStatusUpdate(BaseModel):
    status: ProposalStatus


class ProposalSendRequest(BaseModel):
    channel: Literal["manual", "whatsapp", "email", "secure_link"] = "manual"
    recipient_phone: str | None = None
    recipient_email: EmailStr | None = None
    message: str | None = None
    use_template: bool | None = None
    template_name: str | None = None
    mark_as_sent: bool = False


class ProposalSendResult(BaseModel):
    status: str
    channel: str
    message: str
    pdf_url: str | None = None
    delivery_reference: str | None = None
    sent_at: datetime | None = None


class PublicProposalOut(BaseModel):
    proposal: ProposalOut
    share_link: ProposalShareLinkOut
    company: CompanySettingsOut
    pdf_download_url: str


class PublicProposalResponseResult(BaseModel):
    status: str
    message: str
    response: ProposalCustomerResponseOut
