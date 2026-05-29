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

export type Conversation = {
  id: string;
  customer_id: string | null;
  channel: string;
  status: string;
  intent: string | null;
  severity: string | null;
  assigned_to: string | null;
  summary: string | null;
  created_at: string;
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
  active: boolean;
  use_for_ai: boolean;
  created_at: string;
};
