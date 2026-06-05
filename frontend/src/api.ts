import type {
  AIAnalysis,
  ChatResponse,
  CompanySettings,
  Conversation,
  ContinueWhatsAppResponse,
  DashboardAIInsights,
  DashboardMetrics,
  EnergyBillExtraction,
  EnergyBillParsedData,
  KnowledgeArticle,
  Lead,
  Proposal,
  ProposalCustomerResponse,
  ProposalFollowUp,
  ProposalKit,
  ProposalKitItem,
  ProposalKitSimulation,
  ProposalPriceItem,
  ProposalShareLink,
  ProposalSendRequest,
  ProposalSendResult,
  PublicProposal,
  Ticket,
} from "./types";
import { API_BASE_URL, ENABLE_DEMO_FALLBACK, apiUrl, diagnosticsConfig } from "./config";

export type HealthResponse = {
  status: string;
  service: string;
  environment: string;
};

export class ApiRequestError extends Error {
  endpoint: string;
  status?: number;

  constructor(message: string, endpoint: string, status?: number) {
    super(message);
    this.name = "ApiRequestError";
    this.endpoint = endpoint;
    this.status = status;
  }
}

export { API_BASE_URL, ENABLE_DEMO_FALLBACK, diagnosticsConfig };

export async function checkApiHealth(): Promise<HealthResponse> {
  const endpoint = "/health";
  try {
    const response = await fetch(apiUrl(endpoint), { cache: "no-store" });
    if (!response.ok) {
      throw new ApiRequestError(`Healthcheck retornou HTTP ${response.status}.`, endpoint, response.status);
    }
    const data = (await response.json()) as HealthResponse;
    if (data.status !== "ok") {
      throw new ApiRequestError("Healthcheck nao retornou status ok.", endpoint, response.status);
    }
    return data;
  } catch (error) {
    logApiFailure(endpoint, error, false);
    throw error;
  }
}

function logApiFailure(endpoint: string, error: unknown, fallbackUsed: boolean) {
  if (!import.meta.env.DEV) return;
  console.error("[Solis API] Falha de conexao", {
    apiBaseUrl: API_BASE_URL || "nao configurado",
    endpoint,
    status: error instanceof ApiRequestError ? error.status : undefined,
    message: error instanceof Error ? error.message : String(error),
    fallbackUsed,
  });
}

async function apiErrorFromResponse(response: Response, endpoint: string) {
  let message = `Falha HTTP ${response.status}.`;
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") {
      message = body.detail;
    }
  } catch {
    message = response.statusText || message;
  }
  return new ApiRequestError(message, endpoint, response.status);
}

export async function sendChatMessage(input: {
  message: string;
  conversationId?: string;
  attachmentUrl?: string;
  mediaType?: string;
}): Promise<ChatResponse> {
  const endpoint = "/chat/message";
  try {
    const response = await fetch(apiUrl(endpoint), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        channel: "site",
        conversation_id: input.conversationId,
        message: input.message,
        attachment_url: input.attachmentUrl,
        media_type: input.mediaType,
      }),
    });
    if (!response.ok) throw await apiErrorFromResponse(response, endpoint);
    return response.json();
  } catch (error) {
    logApiFailure(endpoint, error, ENABLE_DEMO_FALLBACK);
    if (!ENABLE_DEMO_FALLBACK) throw error;
    return buildDemoResponse(input.message, input.conversationId);
  }
}

export async function uploadChatAttachment(file: File): Promise<{
  attachment_url: string;
  file_name: string;
  media_type: string;
}> {
  const endpoint = "/chat/attachments";
  const formData = new FormData();
  formData.append("file", file);
  try {
    const response = await fetch(apiUrl(endpoint), {
      method: "POST",
      body: formData,
    });
    if (!response.ok) throw await apiErrorFromResponse(response, endpoint);
    return response.json();
  } catch (error) {
    logApiFailure(endpoint, error, false);
    throw error;
  }
}

function buildDemoResponse(message: string, conversationId?: string): ChatResponse {
  const normalized = message
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();

  const id = conversationId ?? `demo-${crypto.randomUUID()}`;
  const base = {
    conversation_id: id,
    customer_id: null,
    severity: "baixa",
    status: "demo_offline",
    handoff_required: false,
    created_lead_id: null,
    created_ticket_id: null,
    summary: "Resposta gerada em modo demonstracao; mensagens nao sao salvas no painel.",
    demo: true,
    quick_replies: [
      { label: "Quero um orçamento", value: "Quero um orçamento" },
      { label: "Preciso de suporte técnico", value: "Preciso de suporte técnico" },
      { label: "Quero falar com atendente", value: "Quero falar com atendente" },
    ],
  };

  if (normalized.includes("orcamento") || normalized.includes("instalar") || normalized.includes("energia solar")) {
    return {
      ...base,
      intent: "orcamento",
      response:
        "Estou em modo demonstracao porque nao consegui conectar ao servidor do Solis. As mensagens deste teste nao serao salvas no painel.\n\nPerfeito, vou te ajudar com o orcamento em modo demonstracao. Para continuar, eu perguntaria uma informacao por vez, com consentimento LGPD antes de coletar dados.",
      next_question_key: "lgpd_consent",
      quick_replies: [
        { label: "Sim, tudo bem", value: "Sim, tudo bem" },
        { label: "Quero falar com atendente", value: "Quero falar com atendente" },
      ],
    };
  }

  if (normalized.includes("suporte") || normalized.includes("gerando") || normalized.includes("inversor")) {
    return {
      ...base,
      intent: "suporte_tecnico",
      severity: normalized.includes("queimado") || normalized.includes("faisca") ? "alta" : "media",
      response:
        "Estou em modo demonstracao porque nao consegui conectar ao servidor do Solis. As mensagens deste teste nao serao salvas no painel.\n\nNo fluxo real, eu registraria o chamado e perguntaria uma informacao por vez, comecando por: o inversor esta ligado?",
      next_question_key: "inverter_on",
    };
  }

  if (normalized.includes("atendente") || normalized.includes("humano")) {
    return {
      ...base,
      intent: "humano",
      handoff_required: true,
      response:
        "Estou em modo demonstracao porque nao consegui conectar ao servidor do Solis. As mensagens deste teste nao serao salvas no painel.\n\nNo atendimento real, eu encaminharia para um especialista da equipe Solar Solucoes sem pedir para voce repetir as informacoes.",
      next_question_key: null,
    };
  }

  return {
    ...base,
    intent: "outros",
    response:
      "Estou em modo demonstracao porque nao consegui conectar ao servidor do Solis. As mensagens deste teste nao serao salvas no painel.\n\nQuando a API voltar, o atendimento real sera registrado normalmente.",
    next_question_key: null,
  };
}

export async function login(email: string, password: string): Promise<string> {
  const response = await fetch(apiUrl("/auth/login"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw new Error("Login invalido.");
  const data = await response.json();
  return data.access_token;
}

export async function getPublicProposal(token: string): Promise<PublicProposal> {
  const response = await fetch(apiUrl(`/public/proposals/${token}`));
  if (!response.ok) throw new Error("Link de proposta invalido ou indisponivel.");
  return response.json();
}

export async function sendPublicProposalResponse(
  token: string,
  payload: {
    response_type: string;
    customer_name?: string | null;
    customer_email?: string | null;
    customer_phone?: string | null;
    message?: string | null;
  },
): Promise<{ status: string; message: string; response: ProposalCustomerResponse }> {
  const response = await fetch(apiUrl(`/public/proposals/${token}/responses`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("Nao foi possivel registrar sua resposta.");
  return response.json();
}

async function adminFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) throw new Error(`Falha ao carregar ${path}.`);
  if (response.status === 204) return undefined as T;
  return response.json();
}

async function adminUpload<T>(path: string, token: string, formData: FormData): Promise<T> {
  const response = await fetch(apiUrl(path), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
  if (!response.ok) throw new Error(`Falha ao enviar arquivo para ${path}.`);
  return response.json();
}

export const adminApi = {
  metrics: (token: string) => adminFetch<DashboardMetrics>("/dashboard/metrics", token),
  aiInsights: (token: string) => adminFetch<DashboardAIInsights>("/ai/dashboard/insights", token),
  conversations: (token: string) => adminFetch<Conversation[]>("/chat/conversations", token),
  leads: (token: string) => adminFetch<Lead[]>("/leads", token),
  tickets: (token: string) => adminFetch<Ticket[]>("/tickets", token),
  proposals: (token: string) => adminFetch<Proposal[]>("/proposals", token),
  proposalFollowups: (token: string) => adminFetch<ProposalFollowUp[]>("/proposals/followups", token),
  proposalPriceItems: (token: string) => adminFetch<ProposalPriceItem[]>("/proposal-price-items", token),
  proposalKits: (token: string) => adminFetch<ProposalKit[]>("/proposal-kits", token),
  energyBills: (token: string) => adminFetch<EnergyBillExtraction[]>("/energy-bills", token),
  companySettings: (token: string) => adminFetch<CompanySettings>("/company-settings", token),
  knowledge: (token: string) => adminFetch<KnowledgeArticle[]>("/knowledge", token),
  createProposal: (token: string, payload: Partial<Proposal>) =>
    adminFetch<Proposal>("/proposals", token, { method: "POST", body: JSON.stringify(payload) }),
  createProposalFromLead: (token: string, id: string) =>
    adminFetch<Proposal>(`/proposals/from-lead/${id}`, token, { method: "POST" }),
  getProposal: (token: string, id: string) => adminFetch<Proposal>(`/proposals/${id}`, token),
  updateProposal: (token: string, id: string, payload: Partial<Proposal>) =>
    adminFetch<Proposal>(`/proposals/${id}`, token, { method: "PUT", body: JSON.stringify(payload) }),
  updateProposalStatus: (token: string, id: string, status: string) =>
    adminFetch<Proposal>(`/proposals/${id}/status`, token, { method: "PATCH", body: JSON.stringify({ status }) }),
  addProposalItem: (token: string, id: string, payload: Record<string, unknown>) =>
    adminFetch<Proposal>(`/proposals/${id}/items`, token, { method: "POST", body: JSON.stringify(payload) }),
  updateProposalItem: (token: string, proposalId: string, itemId: string, payload: Record<string, unknown>) =>
    adminFetch<Proposal>(`/proposals/${proposalId}/items/${itemId}`, token, { method: "PUT", body: JSON.stringify(payload) }),
  deleteProposalItem: (token: string, proposalId: string, itemId: string) =>
    adminFetch<Proposal>(`/proposals/${proposalId}/items/${itemId}`, token, { method: "DELETE" }),
  generateProposalPdf: (token: string, id: string) =>
    adminFetch<Proposal>(`/proposals/${id}/generate-pdf`, token, { method: "POST" }),
  applyProposalPriceTable: (token: string, id: string) =>
    adminFetch<Proposal>(`/proposals/${id}/apply-price-table`, token, { method: "POST" }),
  createProposalShareLink: (token: string, id: string, expiresInDays = 15) =>
    adminFetch<ProposalShareLink>(`/proposals/${id}/share-link`, token, {
      method: "POST",
      body: JSON.stringify({ expires_in_days: expiresInDays }),
    }),
  revokeProposalShareLink: (token: string, id: string) =>
    adminFetch<ProposalShareLink>(`/proposals/share-links/${id}/revoke`, token, { method: "PATCH" }),
  createProposalFollowup: (token: string, id: string, payload: Partial<ProposalFollowUp>) =>
    adminFetch<ProposalFollowUp>(`/proposals/${id}/followups`, token, { method: "POST", body: JSON.stringify(payload) }),
  completeProposalFollowup: (token: string, id: string) =>
    adminFetch<ProposalFollowUp>(`/proposals/followups/${id}/complete`, token, { method: "PATCH" }),
  cancelProposalFollowup: (token: string, id: string) =>
    adminFetch<ProposalFollowUp>(`/proposals/followups/${id}/cancel`, token, { method: "PATCH" }),
  sendProposal: (token: string, id: string, payload: ProposalSendRequest) =>
    adminFetch<ProposalSendResult>(`/proposals/${id}/send`, token, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  createProposalPriceItem: (token: string, payload: Partial<ProposalPriceItem>) =>
    adminFetch<ProposalPriceItem>("/proposal-price-items", token, { method: "POST", body: JSON.stringify(payload) }),
  updateProposalPriceItem: (token: string, id: string, payload: Partial<ProposalPriceItem>) =>
    adminFetch<ProposalPriceItem>(`/proposal-price-items/${id}`, token, { method: "PUT", body: JSON.stringify(payload) }),
  updateProposalPriceItemActive: (token: string, id: string, active: boolean) =>
    adminFetch<ProposalPriceItem>(`/proposal-price-items/${id}/active`, token, {
      method: "PATCH",
      body: JSON.stringify({ active }),
    }),
  deleteProposalPriceItem: (token: string, id: string) =>
    adminFetch<void>(`/proposal-price-items/${id}`, token, { method: "DELETE" }),
  createProposalKit: (token: string, payload: Partial<ProposalKit>) =>
    adminFetch<ProposalKit>("/proposal-kits", token, { method: "POST", body: JSON.stringify(payload) }),
  updateProposalKit: (token: string, id: string, payload: Partial<ProposalKit>) =>
    adminFetch<ProposalKit>(`/proposal-kits/${id}`, token, { method: "PUT", body: JSON.stringify(payload) }),
  updateProposalKitActive: (token: string, id: string, active: boolean) =>
    adminFetch<ProposalKit>(`/proposal-kits/${id}/active`, token, {
      method: "PATCH",
      body: JSON.stringify({ active }),
    }),
  deleteProposalKit: (token: string, id: string) =>
    adminFetch<void>(`/proposal-kits/${id}`, token, { method: "DELETE" }),
  addProposalKitItem: (token: string, kitId: string, payload: Partial<ProposalKitItem>) =>
    adminFetch<ProposalKit>(`/proposal-kits/${kitId}/items`, token, { method: "POST", body: JSON.stringify(payload) }),
  updateProposalKitItem: (token: string, kitId: string, itemId: string, payload: Partial<ProposalKitItem>) =>
    adminFetch<ProposalKit>(`/proposal-kits/${kitId}/items/${itemId}`, token, { method: "PUT", body: JSON.stringify(payload) }),
  deleteProposalKitItem: (token: string, kitId: string, itemId: string) =>
    adminFetch<ProposalKit>(`/proposal-kits/${kitId}/items/${itemId}`, token, { method: "DELETE" }),
  simulateProposalKit: (token: string, payload: { average_bill?: number | null; estimated_monthly_generation_kwh?: number | null; estimated_power_kwp?: number | null }) =>
    adminFetch<ProposalKitSimulation>("/proposal-kits/simulate", token, { method: "POST", body: JSON.stringify(payload) }),
  parseEnergyBillText: (token: string, rawText: string) =>
    adminFetch<EnergyBillParsedData>("/energy-bills/parse-text", token, {
      method: "POST",
      body: JSON.stringify({ raw_text: rawText, metadata: {} }),
    }),
  uploadEnergyBill: (token: string, formData: FormData) =>
    adminUpload<EnergyBillExtraction>("/energy-bills/extract", token, formData),
  updateEnergyBill: (token: string, id: string, payload: Partial<EnergyBillExtraction>) =>
    adminFetch<EnergyBillExtraction>(`/energy-bills/${id}`, token, { method: "PUT", body: JSON.stringify(payload) }),
  confirmEnergyBill: (token: string, id: string, payload: Partial<EnergyBillExtraction> = {}) =>
    adminFetch<EnergyBillExtraction>(`/energy-bills/${id}/confirm`, token, { method: "POST", body: JSON.stringify(payload) }),
  applyEnergyBillToLead: (token: string, id: string, leadId: string) =>
    adminFetch<Lead>(`/energy-bills/${id}/apply-to-lead/${leadId}`, token, { method: "POST" }),
  generateProposalFromEnergyBill: (token: string, id: string) =>
    adminFetch<Proposal>(`/energy-bills/${id}/generate-proposal`, token, { method: "POST" }),
  discardEnergyBill: (token: string, id: string) =>
    adminFetch<EnergyBillExtraction>(`/energy-bills/${id}/discard`, token, { method: "POST" }),
  updateCompanySettings: (token: string, payload: Partial<CompanySettings>) =>
    adminFetch<CompanySettings>("/company-settings", token, { method: "PUT", body: JSON.stringify(payload) }),
  createKnowledge: (token: string, payload: Omit<KnowledgeArticle, "id" | "created_at">) =>
    adminFetch<KnowledgeArticle>("/knowledge", token, { method: "POST", body: JSON.stringify(payload) }),
  updateTicketStatus: (token: string, id: string, status: string) =>
    adminFetch<Ticket>(`/tickets/${id}/status`, token, { method: "PATCH", body: JSON.stringify({ status }) }),
  handoff: (token: string, id: string, reason: string) =>
    adminFetch<{ id: string; status: string }>(`/chat/conversations/${id}/handoff`, token, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  continueWhatsApp: (token: string, id: string) =>
    adminFetch<ContinueWhatsAppResponse>(`/chat/conversations/${id}/continue-whatsapp`, token, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  analyzeConversation: (token: string, id: string) =>
    adminFetch<AIAnalysis>(`/ai/conversations/${id}/analyze`, token, { method: "POST" }),
  getConversationAnalysis: (token: string, id: string) =>
    adminFetch<AIAnalysis>(`/ai/conversations/${id}/analysis`, token),
  analyzeLead: (token: string, id: string) =>
    adminFetch<AIAnalysis>(`/ai/leads/${id}/analyze`, token, { method: "POST" }),
  analyzeTicket: (token: string, id: string) =>
    adminFetch<AIAnalysis>(`/ai/tickets/${id}/analyze`, token, { method: "POST" }),
  suggestReply: (token: string, id: string) =>
    adminFetch<{ conversation_id: string; suggested_reply: string }>(`/ai/conversations/${id}/suggest-reply`, token, {
      method: "POST",
    }),
};
