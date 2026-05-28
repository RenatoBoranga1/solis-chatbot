import type { ChatResponse, Conversation, DashboardMetrics, KnowledgeArticle, Lead, Ticket } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const ENABLE_DEMO_FALLBACK = import.meta.env.VITE_ENABLE_DEMO_FALLBACK !== "false";

export async function sendChatMessage(input: {
  message: string;
  conversationId?: string;
  attachmentUrl?: string;
}): Promise<ChatResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/chat/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        channel: "site",
        conversation_id: input.conversationId,
        message: input.message,
        attachment_url: input.attachmentUrl,
      }),
    });
    if (!response.ok) throw new Error("Não foi possível enviar a mensagem.");
    return response.json();
  } catch (error) {
    if (!ENABLE_DEMO_FALLBACK) throw error;
    return buildDemoResponse(input.message, input.conversationId);
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
    summary: "Resposta gerada em modo demonstração porque a API local não está ativa.",
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
        "Perfeito, vou te ajudar com o orçamento. Para continuar, vou coletar algumas informações de contato e do imóvel, usadas apenas para atendimento e orçamento da Solar Soluções. Tudo bem?",
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
        "Entendi, vou te ajudar com o suporte técnico. O backend local não está ativo agora, então estou em modo demonstração. No fluxo real, eu registraria o chamado e perguntaria uma informação por vez, começando por: o inversor está ligado?",
      next_question_key: "inverter_on",
    };
  }

  if (normalized.includes("atendente") || normalized.includes("humano")) {
    return {
      ...base,
      intent: "humano",
      handoff_required: true,
      response:
        "Vou te encaminhar para um especialista da equipe Solar Soluções para garantir um atendimento mais preciso. Já registrei as informações que você enviou para que você não precise repetir tudo.",
      next_question_key: null,
    };
  }

  return {
    ...base,
    intent: "outros",
    response:
      "Entendi, vou te ajudar com isso. Estou em modo demonstração porque a API local não está ativa. Para o atendimento real, suba o backend em `http://127.0.0.1:8000` e eu registrarei a conversa no sistema.",
    next_question_key: null,
  };
}

export async function login(email: string, password: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw new Error("Login invalido.");
  const data = await response.json();
  return data.access_token;
}

async function adminFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) throw new Error(`Falha ao carregar ${path}.`);
  return response.json();
}

export const adminApi = {
  metrics: (token: string) => adminFetch<DashboardMetrics>("/dashboard/metrics", token),
  conversations: (token: string) => adminFetch<Conversation[]>("/chat/conversations", token),
  leads: (token: string) => adminFetch<Lead[]>("/leads", token),
  tickets: (token: string) => adminFetch<Ticket[]>("/tickets", token),
  knowledge: (token: string) => adminFetch<KnowledgeArticle[]>("/knowledge", token),
  createKnowledge: (token: string, payload: Omit<KnowledgeArticle, "id" | "created_at">) =>
    adminFetch<KnowledgeArticle>("/knowledge", token, { method: "POST", body: JSON.stringify(payload) }),
  updateTicketStatus: (token: string, id: string, status: string) =>
    adminFetch<Ticket>(`/tickets/${id}/status`, token, { method: "PATCH", body: JSON.stringify({ status }) }),
  handoff: (token: string, id: string, reason: string) =>
    adminFetch<{ id: string; status: string }>(`/chat/conversations/${id}/handoff`, token, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
};
