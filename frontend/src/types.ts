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
  property_type: string | null;
  average_bill: number | null;
  utility_company: string | null;
  roof_type: string | null;
  financing_interest: boolean | null;
  status: string;
  notes: string | null;
  created_at: string;
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
