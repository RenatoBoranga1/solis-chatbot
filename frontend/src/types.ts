export type ChatMessage = {
  id: string;
  sender: "customer" | "bot" | "human";
  content: string;
  processing?: boolean;
};

export type QuickReply = {
  label: string;
  value: string;
};

export type ChatResponse = {
  conversation_id: string;
  customer_id: string | null;
  response: string;
  intent: string | null;
  severity: string | null;
  status: string;
  handoff_required: boolean;
  created_lead_id: string | null;
  created_ticket_id: string | null;
  next_question_key: string | null;
  quick_replies: QuickReply[];
  summary: string | null;
  demo?: boolean;
};

export type DashboardMetrics = {
  total_atendimentos: number;
  leads_orcamento: number;
  chamados_abertos: number;
  baixa_gravidade: number;
  media_gravidade: number;
  alta_gravidade: number;
  resolvidos_pelo_bot: number;
  transferidos_para_humano: number;
  taxa_conversao_orcamento: number;
  satisfacao_media: number | null;
  proposal_metrics: ProposalMetrics | null;
};

export type ProposalMetrics = {
  created: number;
  sent: number;
  accepted: number;
  rejected: number;
  open: number;
  viewed: number;
  pending_followups: number;
  overdue_followups: number;
  total_pipeline_value: number;
  accepted_value: number;
  average_ticket: number;
  conversion_rate: number;
  leads_without_proposal: number;
};

export type AIAnalysis = {
  id: string;
  conversation_id: string | null;
  lead_id: string | null;
  ticket_id: string | null;
  analysis_type: "conversation" | "lead" | "ticket" | "daily_dashboard";
  executive_summary: string;
  customer_intent: string;
  customer_sentiment: string;
  urgency_level: string;
  commercial_opportunity: string;
  conversion_probability: string;
  technical_risk: string;
  priority_score: number;
  missing_data: string[];
  recommended_next_action: string;
  suggested_reply: string;
  tags: string[];
  raw_analysis: Record<string, unknown>;
  created_at: string;
  updated_at: string | null;
};

export type DashboardAIInsights = {
  leads_quentes: number;
  chamados_criticos: number;
  clientes_irritados: number;
  oportunidades_financiamento: number;
  problemas_tecnicos_recorrentes: string[];
  principais_motivos: string[];
  principais_cidades: string[];
  taxa_handoff: number;
  recomendacoes: string[];
};

export type ProposalItem = {
  id: string;
  proposal_id: string;
  category: string;
  description: string;
  quantity: number;
  unit: string;
  unit_price: number;
  total_price: number;
  editable: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string | null;
};

export type ProposalKitItem = {
  id: string;
  kit_id: string;
  category: string;
  description: string;
  quantity: number;
  unit: string;
  unit_price: number;
  total_price: number;
  sort_order: number;
  created_at: string;
  updated_at: string | null;
};

export type ProposalKit = {
  id: string;
  name: string;
  description: string | null;
  min_monthly_consumption_kwh: number | null;
  max_monthly_consumption_kwh: number | null;
  min_power_kwp: number | null;
  max_power_kwp: number | null;
  suggested_power_kwp: number;
  estimated_monthly_generation_kwh: number | null;
  module_count: number | null;
  module_power_wp: number | null;
  inverter_power_kw: number | null;
  base_price: number;
  active: boolean;
  sort_order: number;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
  items: ProposalKitItem[];
};

export type ProposalKitSimulation = {
  average_bill: number | null;
  estimated_monthly_generation_kwh: number | null;
  estimated_power_kwp: number | null;
  selected_kit: ProposalKit | null;
  selection_reason: string | null;
};

export type Proposal = {
  id: string;
  customer_id: string | null;
  lead_id: string | null;
  conversation_id: string | null;
  proposal_number: string;
  status: string;
  customer_name: string;
  customer_phone: string | null;
  customer_email: string | null;
  city: string | null;
  state: string | null;
  property_type: string | null;
  average_bill: number | null;
  estimated_system_power_kwp: number | null;
  estimated_monthly_generation_kwh: number | null;
  estimated_savings_percentage: number | null;
  recommended_kit_id: string | null;
  recommended_kit_name: string | null;
  kit_selection_reason: string | null;
  validity_days: number;
  notes: string | null;
  internal_notes: string | null;
  subtotal: number;
  discount: number;
  total_amount: number;
  payment_conditions: string | null;
  pdf_url: string | null;
  created_at: string;
  updated_at: string | null;
  items: ProposalItem[];
  recommended_kit?: ProposalKit | null;
  share_links?: ProposalShareLink[];
  events?: ProposalEvent[];
  followups?: ProposalFollowUp[];
  customer_responses?: ProposalCustomerResponse[];
};

export type ProposalShareLink = {
  id: string;
  proposal_id: string;
  token: string;
  expires_at: string;
  revoked_at: string | null;
  views_count: number;
  last_viewed_at: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string | null;
  public_url: string | null;
};

export type ProposalEvent = {
  id: string;
  proposal_id: string;
  event_type: string;
  channel: string | null;
  details: Record<string, unknown>;
  created_at: string;
};

export type ProposalCustomerResponse = {
  id: string;
  proposal_id: string;
  share_link_id: string;
  response_type: "interested" | "request_changes" | "accepted" | "rejected" | "talk_to_consultant" | string;
  customer_name: string | null;
  customer_email: string | null;
  customer_phone: string | null;
  message: string | null;
  created_at: string;
};

export type ProposalFollowUp = {
  id: string;
  proposal_id: string;
  due_at: string;
  status: "pending" | "completed" | "canceled" | "overdue" | string;
  channel: "whatsapp" | "email" | "phone" | "manual" | string;
  note: string | null;
  assigned_to: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string | null;
};

export type CompanySettings = {
  id: string;
  company_name: string;
  company_phone: string | null;
  company_email: string | null;
  company_website: string | null;
  company_address: string | null;
  company_logo_url: string | null;
  primary_color: string;
  secondary_color: string;
  default_payment_conditions: string | null;
  default_proposal_validity_days: number;
  default_proposal_notes: string | null;
  created_at: string;
  updated_at: string | null;
};

export type PublicProposal = {
  proposal: Proposal;
  share_link: ProposalShareLink;
  company: CompanySettings;
  pdf_download_url: string;
};

export type ProposalPriceItem = {
  id: string;
  category: string;
  description: string;
  default_unit: string;
  default_quantity: number;
  default_unit_price: number;
  active: boolean;
  sort_order: number;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
};

export type ProposalSendRequest = {
  channel: "manual" | "whatsapp" | "email" | "secure_link";
  recipient_phone?: string | null;
  recipient_email?: string | null;
  message?: string | null;
  use_template?: boolean | null;
  template_name?: string | null;
  mark_as_sent?: boolean;
};

export type ProposalSendResult = {
  status: string;
  channel: string;
  message: string;
  pdf_url: string | null;
  delivery_reference: string | null;
  sent_at: string | null;
};

export type Conversation = {
  id: string;
  customer_id: string | null;
  channel: string;
  status: string;
  intent: string | null;
  severity: string | null;
  assigned_to: string | null;
  summary: string | null;
  outbound_channel_links?: ConversationChannelLink[];
  inbound_channel_links?: ConversationChannelLink[];
  created_at: string;
};

export type ConversationChannelLink = {
  id: string;
  customer_id: string;
  source_conversation_id: string;
  target_conversation_id: string | null;
  source_channel: string;
  target_channel: string;
  external_id: string | null;
  phone: string;
  lead_id: string | null;
  ticket_id: string | null;
  status: "pending" | "invited" | "confirmed" | "expired" | "failed" | string;
  created_at: string;
  confirmed_at: string | null;
};

export type ContinueWhatsAppResponse = {
  status: "sent" | "simulated" | "error" | string;
  conversation_channel_link_id: string;
  phone: string;
  message: string;
  target_conversation_id: string | null;
};

export type Lead = {
  id: string;
  customer_id: string;
  conversation_id: string | null;
  property_type: string | null;
  average_bill: number | null;
  utility_company: string | null;
  roof_type: string | null;
  financing_interest: boolean | null;
  status: string;
  notes: string | null;
  extra: Record<string, unknown>;
  created_at: string;
  updated_at: string | null;
};

export type EnergyBillHistory = {
  id?: string;
  extraction_id?: string;
  period: string;
  consumption_kwh: number;
  bill_amount: number | null;
  created_at?: string;
};

export type EnergyBillParsedData = {
  distributor: string | null;
  customer_name: string | null;
  customer_document_masked: string | null;
  installation_number: string | null;
  customer_address: string | null;
  customer_district: string | null;
  customer_postal_code: string | null;
  customer_unit_number: string | null;
  tariff_flag: string | null;
  city: string | null;
  state: string | null;
  reference_month: string | null;
  due_date: string | null;
  current_consumption_kwh: number | null;
  current_bill_amount: number | null;
  average_consumption_kwh: number | null;
  average_bill_amount: number | null;
  min_consumption_kwh: number | null;
  max_consumption_kwh: number | null;
  estimated_system_power_kwp: number | null;
  estimated_monthly_generation_kwh: number | null;
  estimated_monthly_savings: number | null;
  confidence_score: number;
  needs_human_review: boolean;
  missing_fields: string[];
  parsed_fields: Record<string, unknown>;
  history: EnergyBillHistory[];
};

export type EnergyBillExtraction = EnergyBillParsedData & {
  id: string;
  conversation_id: string | null;
  customer_id: string | null;
  lead_id: string | null;
  attachment_id: string | null;
  status: string;
  source: string;
  origin: string;
  file_name: string | null;
  file_type: string | null;
  file_url: string | null;
  raw_extraction: Record<string, unknown>;
  raw_text_excerpt: string | null;
  error_message: string | null;
  confirmed_by: string | null;
  confirmed_at: string | null;
  created_at: string;
  updated_at: string | null;
};

export type Ticket = {
  id: string;
  customer_id: string;
  problem_type: string;
  severity: "baixa" | "media" | "alta";
  status: string;
  technical_notes: string | null;
  created_at: string;
};

export type KnowledgeArticle = {
  id: string;
  title: string;
  question: string;
  answer: string;
  category: string;
  keywords: string[];
  video_url: string | null;
  video_title: string | null;
  resource_url: string | null;
  resource_title: string | null;
  resource_type: string | null;
  send_video_with_answer: boolean;
  send_resource_with_answer: boolean;
  active: boolean;
  use_for_ai: boolean;
  created_at: string;
};
