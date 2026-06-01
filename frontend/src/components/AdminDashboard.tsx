import {
  AlertTriangle,
  BarChart3,
  BookOpenText,
  CheckCircle2,
  Copy,
  FileText,
  Headphones,
  LogIn,
  MessageCircle,
  Plus,
  RefreshCw,
  Send,
  ShieldCheck,
  Sparkles,
  TicketCheck,
  Trash2,
  UsersRound,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { adminApi, login } from "../api";
import type {
  AIAnalysis,
  Conversation,
  DashboardAIInsights,
  DashboardMetrics,
  KnowledgeArticle,
  Lead,
  Proposal,
  ProposalPriceItem,
  ProposalSendRequest,
  Ticket,
} from "../types";

type AdminData = {
  metrics: DashboardMetrics | null;
  aiInsights: DashboardAIInsights | null;
  conversations: Conversation[];
  leads: Lead[];
  proposals: Proposal[];
  proposalPriceItems: ProposalPriceItem[];
  tickets: Ticket[];
  knowledge: KnowledgeArticle[];
};

const emptyData: AdminData = {
  metrics: null,
  aiInsights: null,
  conversations: [],
  leads: [],
  proposals: [],
  proposalPriceItems: [],
  tickets: [],
  knowledge: [],
};

export function AdminDashboard() {
  const [token, setToken] = useState(() => localStorage.getItem("solis_admin_token") ?? "");
  const [email, setEmail] = useState("admin@solarsolucoes.com.br");
  const [password, setPassword] = useState("");
  const [activeView, setActiveView] = useState("dashboard");
  const [data, setData] = useState<AdminData>(emptyData);
  const [loading, setLoading] = useState(false);
  const [analysisLoadingKey, setAnalysisLoadingKey] = useState<string | null>(null);
  const [conversationAnalyses, setConversationAnalyses] = useState<Record<string, AIAnalysis>>({});
  const [leadAnalyses, setLeadAnalyses] = useState<Record<string, AIAnalysis>>({});
  const [ticketAnalyses, setTicketAnalyses] = useState<Record<string, AIAnalysis>>({});
  const [selectedProposal, setSelectedProposal] = useState<Proposal | null>(null);
  const [proposalLoadingKey, setProposalLoadingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [articleDraft, setArticleDraft] = useState({
    title: "",
    question: "",
    answer: "",
    category: "Energia solar fotovoltaica",
    keywords: "",
    videoTitle: "",
    videoUrl: "",
    sendVideoWithAnswer: false,
    resourceTitle: "",
    resourceUrl: "",
    resourceType: "youtube",
    sendResourceWithAnswer: false,
  });

  const criticalTickets = useMemo(
    () => data.tickets.filter((ticket) => ticket.severity === "alta" && ticket.status !== "Resolvido"),
    [data.tickets],
  );

  const loadData = useCallback(
    async (currentToken = token) => {
      if (!currentToken) return;
      setLoading(true);
      setError(null);
      try {
        const [metrics, aiInsights, conversations, leads, proposals, proposalPriceItems, tickets, knowledge] = await Promise.all([
          adminApi.metrics(currentToken),
          adminApi.aiInsights(currentToken),
          adminApi.conversations(currentToken),
          adminApi.leads(currentToken),
          adminApi.proposals(currentToken),
          adminApi.proposalPriceItems(currentToken),
          adminApi.tickets(currentToken),
          adminApi.knowledge(currentToken),
        ]);
        setData({ metrics, aiInsights, conversations, leads, proposals, proposalPriceItems, tickets, knowledge });
      } catch (loadError) {
        setError("Não foi possível carregar o painel. Verifique o login e a API.");
      } finally {
        setLoading(false);
      }
    },
    [token],
  );

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const nextToken = await login(email, password);
      localStorage.setItem("solis_admin_token", nextToken);
      setToken(nextToken);
      await loadData(nextToken);
    } catch (loginError) {
      setError("Login inválido ou API indisponível.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateArticle(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    await adminApi.createKnowledge(token, {
      title: articleDraft.title,
      question: articleDraft.question,
      answer: articleDraft.answer,
      category: articleDraft.category,
      keywords: articleDraft.keywords
        .split(",")
        .map((keyword) => keyword.trim())
        .filter(Boolean),
      video_title: articleDraft.videoTitle || null,
      video_url: articleDraft.videoUrl || null,
      send_video_with_answer: articleDraft.sendVideoWithAnswer,
      resource_title: articleDraft.resourceTitle || null,
      resource_url: articleDraft.resourceUrl || null,
      resource_type: articleDraft.resourceType || null,
      send_resource_with_answer: articleDraft.sendResourceWithAnswer,
      active: true,
      use_for_ai: true,
    });
    setArticleDraft({
      title: "",
      question: "",
      answer: "",
      category: "Energia solar fotovoltaica",
      keywords: "",
      videoTitle: "",
      videoUrl: "",
      sendVideoWithAnswer: false,
      resourceTitle: "",
      resourceUrl: "",
      resourceType: "youtube",
      sendResourceWithAnswer: false,
    });
    await loadData();
  }

  async function handleAnalyzeConversation(id: string) {
    if (!token) return;
    setAnalysisLoadingKey(`conversation:${id}`);
    setError(null);
    try {
      const analysis = await adminApi.analyzeConversation(token, id);
      setConversationAnalyses((current) => ({ ...current, [id]: analysis }));
    } catch (analysisError) {
      setError("Não foi possível gerar a análise inteligente da conversa.");
    } finally {
      setAnalysisLoadingKey(null);
    }
  }

  async function handleAnalyzeLead(id: string) {
    if (!token) return;
    setAnalysisLoadingKey(`lead:${id}`);
    setError(null);
    try {
      const analysis = await adminApi.analyzeLead(token, id);
      setLeadAnalyses((current) => ({ ...current, [id]: analysis }));
    } catch (analysisError) {
      setError("Não foi possível gerar a análise inteligente do lead.");
    } finally {
      setAnalysisLoadingKey(null);
    }
  }

  async function handleAnalyzeTicket(id: string) {
    if (!token) return;
    setAnalysisLoadingKey(`ticket:${id}`);
    setError(null);
    try {
      const analysis = await adminApi.analyzeTicket(token, id);
      setTicketAnalyses((current) => ({ ...current, [id]: analysis }));
    } catch (analysisError) {
      setError("Não foi possível gerar a análise inteligente do chamado.");
    } finally {
      setAnalysisLoadingKey(null);
    }
  }

  async function handleCreateProposalFromLead(id: string) {
    if (!token) return;
    setProposalLoadingKey(`lead:${id}`);
    setError(null);
    try {
      const proposal = await adminApi.createProposalFromLead(token, id);
      setSelectedProposal(proposal);
      setActiveView("propostas");
      await loadData();
    } catch (proposalError) {
      setError("Não foi possível gerar a proposta a partir do lead.");
    } finally {
      setProposalLoadingKey(null);
    }
  }

  async function handleCreateManualProposal() {
    if (!token) return;
    setProposalLoadingKey("manual");
    setError(null);
    try {
      const proposal = await adminApi.createProposal(token, {
        customer_name: "Novo cliente",
        status: "draft",
        validity_days: 7,
        notes: "Valores e condições devem ser revisados pela equipe da Solar Soluções antes do envio ao cliente.",
        payment_conditions: "A definir após revisão comercial.",
        discount: 0,
      });
      setSelectedProposal(proposal);
      await loadData();
    } catch (proposalError) {
      setError("Não foi possível criar a proposta manual.");
    } finally {
      setProposalLoadingKey(null);
    }
  }

  async function handleOpenProposal(id: string) {
    if (!token) return;
    setProposalLoadingKey(`open:${id}`);
    setError(null);
    try {
      setSelectedProposal(await adminApi.getProposal(token, id));
    } catch (proposalError) {
      setError("Não foi possível abrir a proposta.");
    } finally {
      setProposalLoadingKey(null);
    }
  }

  async function handleUpdateProposal(id: string, payload: Partial<Proposal>) {
    if (!token) return;
    const updated = await adminApi.updateProposal(token, id, payload);
    setSelectedProposal(updated);
    await loadData();
  }

  async function handleUpdateProposalStatus(id: string, status: string) {
    if (!token) return;
    const updated = await adminApi.updateProposalStatus(token, id, status);
    setSelectedProposal(updated);
    await loadData();
  }

  async function handleAddProposalItem(id: string) {
    if (!token) return;
    const updated = await adminApi.addProposalItem(token, id, {
      category: "outros",
      description: "Novo item da proposta",
      quantity: 1,
      unit: "un",
      unit_price: 0,
      editable: true,
      sort_order: selectedProposal?.items.length ?? 0,
    });
    setSelectedProposal(updated);
    await loadData();
  }

  async function handleUpdateProposalItem(proposalId: string, itemId: string, payload: Record<string, unknown>) {
    if (!token) return;
    const updated = await adminApi.updateProposalItem(token, proposalId, itemId, payload);
    setSelectedProposal(updated);
    await loadData();
  }

  async function handleDeleteProposalItem(proposalId: string, itemId: string) {
    if (!token) return;
    const updated = await adminApi.deleteProposalItem(token, proposalId, itemId);
    setSelectedProposal(updated);
    await loadData();
  }

  async function handleGenerateProposalPdf(id: string) {
    if (!token) return;
    setProposalLoadingKey(`pdf:${id}`);
    try {
      const updated = await adminApi.generateProposalPdf(token, id);
      setSelectedProposal(updated);
      await loadData();
    } finally {
      setProposalLoadingKey(null);
    }
  }

  async function handleApplyProposalPriceTable(id: string) {
    if (!token) return;
    setProposalLoadingKey(`price-table:${id}`);
    try {
      const updated = await adminApi.applyProposalPriceTable(token, id);
      setSelectedProposal(updated);
      await loadData();
    } catch (priceTableError) {
      setError("Nao foi possivel aplicar a tabela de precos. Verifique se existem itens ativos configurados.");
    } finally {
      setProposalLoadingKey(null);
    }
  }

  async function handleSendProposal(id: string, payload: ProposalSendRequest) {
    if (!token) return;
    setProposalLoadingKey(`send:${id}`);
    try {
      const result = await adminApi.sendProposal(token, id, payload);
      setError(result.message);
      const updated = await adminApi.getProposal(token, id);
      setSelectedProposal(updated);
      await loadData();
    } finally {
      setProposalLoadingKey(null);
    }
  }

  async function handleCreatePriceItem(payload: Partial<ProposalPriceItem>) {
    if (!token) return;
    await adminApi.createProposalPriceItem(token, payload);
    await loadData();
  }

  async function handleUpdatePriceItem(id: string, payload: Partial<ProposalPriceItem>) {
    if (!token) return;
    await adminApi.updateProposalPriceItem(token, id, payload);
    await loadData();
  }

  async function handleTogglePriceItem(id: string, active: boolean) {
    if (!token) return;
    await adminApi.updateProposalPriceItemActive(token, id, active);
    await loadData();
  }

  async function handleDeletePriceItem(id: string) {
    if (!token) return;
    await adminApi.deleteProposalPriceItem(token, id);
    await loadData();
  }

  function copySuggestedReply(text: string) {
    void navigator.clipboard?.writeText(text);
  }

  useEffect(() => {
    if (token) void loadData(token);
  }, [loadData, token]);

  if (!token) {
    return (
      <section className="admin-shell admin-shell--login">
        <form className="login-panel" onSubmit={handleLogin}>
          <div className="login-panel__brand">
            <ShieldCheck size={28} />
            <div>
              <strong>Solis Admin</strong>
              <span>Painel Solar Soluções</span>
            </div>
          </div>
          <label>
            E-mail
            <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" />
          </label>
          <label>
            Senha
            <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" />
          </label>
          {error && <p className="form-error">{error}</p>}
          <button className="primary-button" type="submit" disabled={loading}>
            <LogIn size={18} />
            Entrar
          </button>
        </form>
      </section>
    );
  }

  return (
    <section className="admin-shell">
      <aside className="admin-sidebar">
        <div className="admin-brand">
          <span className="brand-mark">S</span>
          <div>
            <strong>Solis Admin</strong>
            <small>Solar Soluções</small>
          </div>
        </div>
        <nav>
          <NavButton id="dashboard" label="Dashboard" icon={<BarChart3 size={18} />} active={activeView} onClick={setActiveView} />
          <NavButton id="conversas" label="Atendimentos" icon={<Headphones size={18} />} active={activeView} onClick={setActiveView} />
          <NavButton id="leads" label="Leads" icon={<UsersRound size={18} />} active={activeView} onClick={setActiveView} />
          <NavButton id="propostas" label="Propostas" icon={<FileText size={18} />} active={activeView} onClick={setActiveView} />
          <NavButton id="chamados" label="Chamados" icon={<TicketCheck size={18} />} active={activeView} onClick={setActiveView} />
          <NavButton id="base" label="Base" icon={<BookOpenText size={18} />} active={activeView} onClick={setActiveView} />
        </nav>
      </aside>

      <main className="admin-main">
        <header className="admin-topbar">
          <div>
            <strong>{titleFor(activeView)}</strong>
            <span>{subtitleFor(activeView)}</span>
          </div>
          <div className="topbar-actions">
            {criticalTickets.length > 0 && (
              <span className="critical-chip">
                <AlertTriangle size={16} />
                {criticalTickets.length} alta prioridade
              </span>
            )}
            <button className="secondary-button" onClick={() => loadData()} disabled={loading}>
              <RefreshCw size={16} className={loading ? "spin" : ""} />
              Atualizar
            </button>
          </div>
        </header>

        {error && <div className="notice notice--error">{error}</div>}

        {activeView === "dashboard" && (
          <DashboardView metrics={data.metrics} tickets={data.tickets} aiInsights={data.aiInsights} />
        )}
        {activeView === "conversas" && (
          <ConversationsView
            conversations={data.conversations}
            token={token}
            refresh={loadData}
            analyses={conversationAnalyses}
            loadingKey={analysisLoadingKey}
            onAnalyze={handleAnalyzeConversation}
            onCopy={copySuggestedReply}
          />
        )}
        {activeView === "leads" && (
          <LeadsView
            leads={data.leads}
            analyses={leadAnalyses}
            loadingKey={analysisLoadingKey}
            onAnalyze={handleAnalyzeLead}
            onCopy={copySuggestedReply}
            onCreateProposal={handleCreateProposalFromLead}
            proposalLoadingKey={proposalLoadingKey}
          />
        )}
        {activeView === "propostas" && (
          <ProposalsView
            proposals={data.proposals}
            priceItems={data.proposalPriceItems}
            selectedProposal={selectedProposal}
            loadingKey={proposalLoadingKey}
            onCreateManual={handleCreateManualProposal}
            onOpen={handleOpenProposal}
            onUpdate={handleUpdateProposal}
            onUpdateStatus={handleUpdateProposalStatus}
            onAddItem={handleAddProposalItem}
            onUpdateItem={handleUpdateProposalItem}
            onDeleteItem={handleDeleteProposalItem}
            onGeneratePdf={handleGenerateProposalPdf}
            onApplyPriceTable={handleApplyProposalPriceTable}
            onSend={handleSendProposal}
            onCreatePriceItem={handleCreatePriceItem}
            onUpdatePriceItem={handleUpdatePriceItem}
            onTogglePriceItem={handleTogglePriceItem}
            onDeletePriceItem={handleDeletePriceItem}
          />
        )}
        {activeView === "chamados" && (
          <TicketsView
            tickets={data.tickets}
            token={token}
            refresh={loadData}
            analyses={ticketAnalyses}
            loadingKey={analysisLoadingKey}
            onAnalyze={handleAnalyzeTicket}
            onCopy={copySuggestedReply}
          />
        )}
        {activeView === "base" && (
          <KnowledgeView
            articles={data.knowledge}
            draft={articleDraft}
            setDraft={setArticleDraft}
            onSubmit={handleCreateArticle}
          />
        )}
      </main>
    </section>
  );
}

function NavButton(props: {
  id: string;
  label: string;
  icon: React.ReactNode;
  active: string;
  onClick: (id: string) => void;
}) {
  return (
    <button className={props.active === props.id ? "nav-button nav-button--active" : "nav-button"} onClick={() => props.onClick(props.id)}>
      {props.icon}
      {props.label}
    </button>
  );
}

function titleFor(view: string) {
  const titles: Record<string, string> = {
    dashboard: "Dashboard",
    conversas: "Atendimentos",
    leads: "Leads de orçamento",
    propostas: "Propostas",
    chamados: "Chamados técnicos",
    base: "Base de conhecimento",
  };
  return titles[view] ?? "Painel";
}

function subtitleFor(view: string) {
  const subtitles: Record<string, string> = {
    dashboard: "Indicadores de atendimento, vendas e suporte.",
    conversas: "Histórico das conversas e transferências.",
    leads: "Solicitações comerciais captadas pelo Solis.",
    propostas: "Criação, revisão, PDF e envio de propostas comerciais.",
    chamados: "Triagem técnica com gravidade e status.",
    base: "Perguntas e respostas oficiais para IA e atendimento.",
  };
  return subtitles[view] ?? "";
}

const PROPOSAL_STATUSES = [
  { value: "draft", label: "Rascunho" },
  { value: "under_review", label: "Em revisão" },
  { value: "approved", label: "Aprovada" },
  { value: "ready_to_send", label: "Pronta para envio" },
  { value: "sent", label: "Enviada" },
  { value: "accepted", label: "Aceita" },
  { value: "rejected", label: "Rejeitada" },
  { value: "expired", label: "Expirada" },
  { value: "canceled", label: "Cancelada" },
];

const PROPOSAL_ITEM_CATEGORIES = [
  { value: "kit_fotovoltaico", label: "Kit fotovoltaico" },
  { value: "materiais_eletricos", label: "Materiais elétricos" },
  { value: "mao_de_obra", label: "Mão de obra" },
  { value: "projeto", label: "Projeto" },
  { value: "homologacao", label: "Homologação" },
  { value: "taxas_concessionaria", label: "Taxas e adequações" },
  { value: "estrutura_fixacao", label: "Estrutura de fixação" },
  { value: "deslocamento", label: "Deslocamento" },
  { value: "monitoramento", label: "Monitoramento" },
  { value: "outros", label: "Outros" },
];

function formatCurrency(value: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value ?? 0));
}

function ProposalStatusPill({ status }: { status: string }) {
  const label = PROPOSAL_STATUSES.find((item) => item.value === status)?.label ?? status;
  return <span className={`proposal-status proposal-status--${status}`}>{label}</span>;
}

function DashboardView({
  metrics,
  tickets,
  aiInsights,
}: {
  metrics: DashboardMetrics | null;
  tickets: Ticket[];
  aiInsights: DashboardAIInsights | null;
}) {
  const cards = [
    { label: "Atendimentos", value: metrics?.total_atendimentos ?? 0, icon: <Headphones size={18} /> },
    { label: "Leads", value: metrics?.leads_orcamento ?? 0, icon: <UsersRound size={18} /> },
    { label: "Chamados abertos", value: metrics?.chamados_abertos ?? 0, icon: <TicketCheck size={18} /> },
    { label: "Transferidos", value: metrics?.transferidos_para_humano ?? 0, icon: <ShieldCheck size={18} /> },
    { label: "Resolvidos pelo bot", value: metrics?.resolvidos_pelo_bot ?? 0, icon: <CheckCircle2 size={18} /> },
    { label: "Conversão", value: `${metrics?.taxa_conversao_orcamento ?? 0}%`, icon: <BarChart3 size={18} /> },
  ];
  const aiCards = [
    { label: "Leads quentes", value: aiInsights?.leads_quentes ?? 0, icon: <Sparkles size={18} /> },
    { label: "Chamados críticos", value: aiInsights?.chamados_criticos ?? 0, icon: <AlertTriangle size={18} /> },
    { label: "Clientes irritados", value: aiInsights?.clientes_irritados ?? 0, icon: <Headphones size={18} /> },
    {
      label: "Oportunidades de financiamento",
      value: aiInsights?.oportunidades_financiamento ?? 0,
      icon: <BarChart3 size={18} />,
    },
  ];

  return (
    <>
      <section className="metric-grid">
        {cards.map((card) => (
          <article className="metric-card" key={card.label}>
            <span>{card.icon}</span>
            <div>
              <strong>{card.value}</strong>
              <small>{card.label}</small>
            </div>
          </article>
        ))}
      </section>
      <section className="work-section">
        <div className="section-heading">
          <strong>Chamados por gravidade</strong>
          <span>Priorize alta gravidade e riscos elétricos.</span>
        </div>
        <div className="severity-bars">
          <SeverityBar label="Baixa" value={metrics?.baixa_gravidade ?? 0} tone="low" total={tickets.length} />
          <SeverityBar label="Media" value={metrics?.media_gravidade ?? 0} tone="medium" total={tickets.length} />
          <SeverityBar label="Alta" value={metrics?.alta_gravidade ?? 0} tone="high" total={tickets.length} />
        </div>
      </section>
      <section className="metric-grid">
        {aiCards.map((card) => (
          <article className="metric-card metric-card--ai" key={card.label}>
            <span>{card.icon}</span>
            <div>
              <strong>{card.value}</strong>
              <small>{card.label}</small>
            </div>
          </article>
        ))}
      </section>
      <section className="work-section ai-insights">
        <div className="section-heading">
          <strong>Recomendações da IA para a gestão</strong>
          <span>Leitura estratégica dos atendimentos recentes.</span>
        </div>
        <div className="insight-grid">
          <InsightList title="Problemas recorrentes" items={aiInsights?.problemas_tecnicos_recorrentes ?? []} />
          <InsightList title="Principais motivos" items={aiInsights?.principais_motivos ?? []} />
          <InsightList title="Principais cidades" items={aiInsights?.principais_cidades ?? []} />
        </div>
        <div className="recommendation-list">
          {(aiInsights?.recomendacoes?.length
            ? aiInsights.recomendacoes
            : ["Gere mais atendimentos para a IA identificar padrões de gestão."])
            .map((recommendation) => (
              <p key={recommendation}>{recommendation}</p>
            ))}
        </div>
      </section>
    </>
  );
}

function InsightList({ title, items }: { title: string; items: string[] }) {
  return (
    <article className="insight-list">
      <strong>{title}</strong>
      {items.length ? (
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <span>Sem dados suficientes</span>
      )}
    </article>
  );
}

function SeverityBar({ label, value, tone, total }: { label: string; value: number; tone: string; total: number }) {
  const width = total ? Math.max(8, Math.round((value / total) * 100)) : 0;
  return (
    <div className="severity-row">
      <span>{label}</span>
      <div className="severity-track">
        <i className={`severity-fill severity-fill--${tone}`} style={{ width: `${width}%` }} />
      </div>
      <strong>{value}</strong>
    </div>
  );
}

function ConversationsView({
  conversations,
  token,
  refresh,
  analyses,
  loadingKey,
  onAnalyze,
  onCopy,
}: {
  conversations: Conversation[];
  token: string;
  refresh: () => Promise<void>;
  analyses: Record<string, AIAnalysis>;
  loadingKey: string | null;
  onAnalyze: (id: string) => Promise<void>;
  onCopy: (text: string) => void;
}) {
  const [whatsappLoadingId, setWhatsappLoadingId] = useState<string | null>(null);
  const [whatsappNotice, setWhatsappNotice] = useState<string | null>(null);

  async function requestHandoff(id: string) {
    await adminApi.handoff(token, id, "Assumido manualmente pelo painel.");
    await refresh();
  }

  async function continueOnWhatsApp(conversation: Conversation) {
    if (conversation.severity === "alta") {
      setWhatsappNotice("Este caso tem gravidade alta. Revise antes de enviar o convite pelo WhatsApp.");
      return;
    }
    setWhatsappLoadingId(conversation.id);
    setWhatsappNotice(null);
    try {
      const result = await adminApi.continueWhatsApp(token, conversation.id);
      const label = result.status === "simulated" ? "simulado em desenvolvimento" : "enviado";
      setWhatsappNotice(`Convite WhatsApp ${label}. O cliente deve responder SIM para confirmar.`);
      await refresh();
    } catch (continueError) {
      setWhatsappNotice("Não foi possível iniciar a continuidade pelo WhatsApp. Verifique telefone, gravidade e configuração da API.");
    } finally {
      setWhatsappLoadingId(null);
    }
  }

  return (
    <section className="table-panel">
      {whatsappNotice && <div className="notice notice--compact">{whatsappNotice}</div>}
      <TableHeader columns={["Canal", "Intenção", "Gravidade", "Status", "Resumo", "Ação"]} />
      {conversations.map((conversation) => (
        <div className="table-group" key={conversation.id}>
          <div className="table-row table-row--six">
            <span className="channel-cell">
              {conversation.channel}
              <WhatsAppLinkBadge conversation={conversation} />
            </span>
            <span>{conversation.intent ?? "N/I"}</span>
            <SeverityPill severity={conversation.severity} />
            <span>{conversation.status}</span>
            <span className="truncate">{conversation.summary ?? "Sem resumo"}</span>
            <div className="row-actions">
              <button className="text-button" onClick={() => requestHandoff(conversation.id)}>
                Assumir
              </button>
              <button
                className="text-button text-button--ai"
                onClick={() => onAnalyze(conversation.id)}
                disabled={loadingKey === `conversation:${conversation.id}`}
              >
                <Sparkles size={15} />
                {analyses[conversation.id] ? "Regenerar" : "Gerar IA"}
              </button>
              {canContinueOnWhatsApp(conversation) && (
                <button
                  className="text-button text-button--whatsapp"
                  onClick={() => continueOnWhatsApp(conversation)}
                  disabled={whatsappLoadingId === conversation.id}
                  title={conversation.severity === "alta" ? "Revise caso de alta gravidade antes do convite" : undefined}
                >
                  <MessageCircle size={15} />
                  {whatsappLoadingId === conversation.id ? "Enviando" : "WhatsApp"}
                </button>
              )}
            </div>
          </div>
          {analyses[conversation.id] && (
            <AnalysisPanel analysis={analyses[conversation.id]} onCopy={onCopy} variant="conversation" />
          )}
        </div>
      ))}
    </section>
  );
}

function canContinueOnWhatsApp(conversation: Conversation) {
  if (conversation.channel === "whatsapp") return false;
  const link = latestWhatsAppLink(conversation);
  if (link?.status === "confirmed") return false;
  return ["commercial_triage", "technical_triage", "handoff", "human_assigned"].includes(conversation.status);
}

function latestWhatsAppLink(conversation: Conversation) {
  return [...(conversation.outbound_channel_links ?? [])]
    .filter((link) => link.target_channel === "whatsapp")
    .sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
}

function WhatsAppLinkBadge({ conversation }: { conversation: Conversation }) {
  const link = latestWhatsAppLink(conversation);
  if (!link) return null;
  const label: Record<string, string> = {
    pending: "WhatsApp pendente",
    invited: "WhatsApp enviado",
    confirmed: "WhatsApp confirmado",
    failed: "WhatsApp falhou",
    expired: "WhatsApp expirado",
  };
  return <small className={`channel-badge channel-badge--${link.status}`}>{label[link.status] ?? link.status}</small>;
}

function LeadsView({
  leads,
  analyses,
  loadingKey,
  onAnalyze,
  onCopy,
  onCreateProposal,
  proposalLoadingKey,
}: {
  leads: Lead[];
  analyses: Record<string, AIAnalysis>;
  loadingKey: string | null;
  onAnalyze: (id: string) => Promise<void>;
  onCopy: (text: string) => void;
  onCreateProposal: (id: string) => Promise<void>;
  proposalLoadingKey: string | null;
}) {
  return (
    <section className="table-panel">
      <TableHeader columns={["Tipo", "Conta média", "Score", "Financiamento", "Status", "Ação"]} />
      {leads.map((lead) => (
        <div className="table-group" key={lead.id}>
          <div className="table-row table-row--six">
            <span>{lead.property_type ?? "N/I"}</span>
            <span>{lead.average_bill ? `R$ ${lead.average_bill}` : "N/I"}</span>
            <ScoreBadge score={analyses[lead.id]?.priority_score} type="lead" />
            <span>{lead.financing_interest === null ? "N/I" : lead.financing_interest ? "Sim" : "Não"}</span>
            <span>{lead.status}</span>
            <div className="row-actions">
              <button
                className="text-button text-button--ai"
                onClick={() => onAnalyze(lead.id)}
                disabled={loadingKey === `lead:${lead.id}`}
              >
                <Sparkles size={15} />
                {analyses[lead.id] ? "Regenerar" : "Analisar"}
              </button>
              {analyses[lead.id] && (
                <button className="text-button" onClick={() => onCopy(analyses[lead.id].suggested_reply)}>
                  <Copy size={15} />
                  Copiar
                </button>
              )}
              <button
                className="text-button text-button--proposal"
                onClick={() => onCreateProposal(lead.id)}
                disabled={proposalLoadingKey === `lead:${lead.id}`}
              >
                <FileText size={15} />
                {proposalLoadingKey === `lead:${lead.id}` ? "Gerando" : "Gerar proposta"}
              </button>
            </div>
          </div>
          {analyses[lead.id] && <AnalysisPanel analysis={analyses[lead.id]} onCopy={onCopy} variant="lead" />}
        </div>
      ))}
    </section>
  );
}

function ProposalsView({
  proposals,
  priceItems,
  selectedProposal,
  loadingKey,
  onCreateManual,
  onOpen,
  onUpdate,
  onUpdateStatus,
  onAddItem,
  onUpdateItem,
  onDeleteItem,
  onGeneratePdf,
  onApplyPriceTable,
  onSend,
  onCreatePriceItem,
  onUpdatePriceItem,
  onTogglePriceItem,
  onDeletePriceItem,
}: {
  proposals: Proposal[];
  priceItems: ProposalPriceItem[];
  selectedProposal: Proposal | null;
  loadingKey: string | null;
  onCreateManual: () => Promise<void>;
  onOpen: (id: string) => Promise<void>;
  onUpdate: (id: string, payload: Partial<Proposal>) => Promise<void>;
  onUpdateStatus: (id: string, status: string) => Promise<void>;
  onAddItem: (id: string) => Promise<void>;
  onUpdateItem: (proposalId: string, itemId: string, payload: Record<string, unknown>) => Promise<void>;
  onDeleteItem: (proposalId: string, itemId: string) => Promise<void>;
  onGeneratePdf: (id: string) => Promise<void>;
  onApplyPriceTable: (id: string) => Promise<void>;
  onSend: (id: string, payload: ProposalSendRequest) => Promise<void>;
  onCreatePriceItem: (payload: Partial<ProposalPriceItem>) => Promise<void>;
  onUpdatePriceItem: (id: string, payload: Partial<ProposalPriceItem>) => Promise<void>;
  onTogglePriceItem: (id: string, active: boolean) => Promise<void>;
  onDeletePriceItem: (id: string) => Promise<void>;
}) {
  const [filters, setFilters] = useState({ status: "", city: "", customer: "" });
  const [activeTab, setActiveTab] = useState<"proposals" | "prices">("proposals");
  const [sendDraft, setSendDraft] = useState<ProposalSendRequest>({ channel: "manual", mark_as_sent: false });
  const filtered = proposals.filter((proposal) => {
    const byStatus = !filters.status || proposal.status === filters.status;
    const byCity = !filters.city || (proposal.city ?? "").toLowerCase().includes(filters.city.toLowerCase());
    const byCustomer = !filters.customer || proposal.customer_name.toLowerCase().includes(filters.customer.toLowerCase());
    return byStatus && byCity && byCustomer;
  });
  const hasZeroValues = selectedProposal?.items.length ? selectedProposal.items.every((item) => Number(item.unit_price) === 0) : false;

  return (
    <section className="proposals-layout">
      <div className="proposal-tabs">
        <button className={activeTab === "proposals" ? "proposal-tab proposal-tab--active" : "proposal-tab"} onClick={() => setActiveTab("proposals")}>
          Propostas
        </button>
        <button className={activeTab === "prices" ? "proposal-tab proposal-tab--active" : "proposal-tab"} onClick={() => setActiveTab("prices")}>
          Tabela de precos
        </button>
      </div>

      {activeTab === "prices" && (
        <PriceTablePanel
          priceItems={priceItems}
          onCreate={onCreatePriceItem}
          onUpdate={onUpdatePriceItem}
          onToggle={onTogglePriceItem}
          onDelete={onDeletePriceItem}
        />
      )}

      {activeTab === "proposals" && (
        <>
      <div className="table-panel proposal-list">
        <div className="proposal-toolbar">
          <div className="proposal-filters">
            <select value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}>
              <option value="">Todos os status</option>
              {PROPOSAL_STATUSES.map((status) => (
                <option value={status.value} key={status.value}>
                  {status.label}
                </option>
              ))}
            </select>
            <input placeholder="Cidade" value={filters.city} onChange={(event) => setFilters((current) => ({ ...current, city: event.target.value }))} />
            <input placeholder="Cliente" value={filters.customer} onChange={(event) => setFilters((current) => ({ ...current, customer: event.target.value }))} />
          </div>
          <button className="primary-button" onClick={onCreateManual} disabled={loadingKey === "manual"}>
            <Plus size={16} />
            Nova proposta
          </button>
        </div>
        <TableHeader columns={["Número", "Cliente", "Cidade", "Tipo", "Total", "Status", "Ação"]} />
        {filtered.map((proposal) => (
          <div className="table-row table-row--seven" key={proposal.id}>
            <span>{proposal.proposal_number}</span>
            <span className="truncate">{proposal.customer_name}</span>
            <span>{proposal.city ?? "N/I"}</span>
            <span>{proposal.property_type ?? "N/I"}</span>
            <span>{formatCurrency(proposal.total_amount)}</span>
            <ProposalStatusPill status={proposal.status} />
            <div className="row-actions">
              <button className="text-button" onClick={() => onOpen(proposal.id)} disabled={loadingKey === `open:${proposal.id}`}>
                Abrir
              </button>
              <button className="text-button" onClick={() => onGeneratePdf(proposal.id)} disabled={loadingKey === `pdf:${proposal.id}`}>
                <FileText size={15} />
                {proposal.pdf_url ? "PDF gerado" : "PDF"}
              </button>
            </div>
          </div>
        ))}
      </div>

      {selectedProposal && (
        <article className="proposal-detail">
          <div className="proposal-detail__header">
            <div>
              <strong>{selectedProposal.proposal_number}</strong>
              <span>Valores e condições devem ser revisados pela equipe da Solar Soluções antes do envio ao cliente.</span>
            </div>
            <ProposalStatusPill status={selectedProposal.status} />
          </div>

          <div className="proposal-alert proposal-alert--info">
            Esta proposta e um rascunho comercial. Revise todos os valores, prazos, economia estimada e condicoes antes de enviar.
          </div>
          {hasZeroValues && (
            <div className="proposal-alert proposal-alert--warning">
              Os valores ainda nao foram preenchidos. Configure a tabela de precos ou edite os itens manualmente.
            </div>
          )}

          <div className="proposal-grid">
            <label>
              Cliente
              <input defaultValue={selectedProposal.customer_name} onBlur={(event) => onUpdate(selectedProposal.id, { customer_name: event.target.value })} />
            </label>
            <label>
              Telefone
              <input defaultValue={selectedProposal.customer_phone ?? ""} onBlur={(event) => onUpdate(selectedProposal.id, { customer_phone: event.target.value })} />
            </label>
            <label>
              E-mail
              <input defaultValue={selectedProposal.customer_email ?? ""} onBlur={(event) => onUpdate(selectedProposal.id, { customer_email: event.target.value })} />
            </label>
            <label>
              Cidade
              <input defaultValue={selectedProposal.city ?? ""} onBlur={(event) => onUpdate(selectedProposal.id, { city: event.target.value })} />
            </label>
            <label>
              UF
              <input defaultValue={selectedProposal.state ?? ""} maxLength={2} onBlur={(event) => onUpdate(selectedProposal.id, { state: event.target.value })} />
            </label>
            <label>
              Tipo de imóvel
              <input defaultValue={selectedProposal.property_type ?? ""} onBlur={(event) => onUpdate(selectedProposal.id, { property_type: event.target.value })} />
            </label>
            <label>
              Conta média
              <input type="number" defaultValue={selectedProposal.average_bill ?? ""} onBlur={(event) => onUpdate(selectedProposal.id, { average_bill: Number(event.target.value) || null })} />
            </label>
            <label>
              Potência kWp
              <input type="number" step="0.001" defaultValue={selectedProposal.estimated_system_power_kwp ?? ""} onBlur={(event) => onUpdate(selectedProposal.id, { estimated_system_power_kwp: Number(event.target.value) || null })} />
            </label>
            <label>
              Geração mensal kWh
              <input type="number" defaultValue={selectedProposal.estimated_monthly_generation_kwh ?? ""} onBlur={(event) => onUpdate(selectedProposal.id, { estimated_monthly_generation_kwh: Number(event.target.value) || null })} />
            </label>
            <label>
              Economia estimada %
              <input type="number" defaultValue={selectedProposal.estimated_savings_percentage ?? ""} onBlur={(event) => onUpdate(selectedProposal.id, { estimated_savings_percentage: Number(event.target.value) || null })} />
            </label>
          </div>

          <div className="proposal-items">
            <div className="proposal-section-title">
              <strong>Itens da proposta</strong>
              <div className="proposal-section-actions">
                <button className="text-button" onClick={() => onApplyPriceTable(selectedProposal.id)} disabled={loadingKey === `price-table:${selectedProposal.id}`}>
                  <RefreshCw size={15} />
                  Aplicar tabela de precos
                </button>
                <button className="text-button" onClick={() => onAddItem(selectedProposal.id)}>
                  <Plus size={15} />
                  Item
                </button>
              </div>
            </div>
            {selectedProposal.items.map((item) => (
              <div className="proposal-item-row" key={item.id}>
                <select defaultValue={item.category} onBlur={(event) => onUpdateItem(selectedProposal.id, item.id, { category: event.target.value })}>
                  {PROPOSAL_ITEM_CATEGORIES.map((category) => (
                    <option key={category.value} value={category.value}>
                      {category.label}
                    </option>
                  ))}
                </select>
                <input defaultValue={item.description} onBlur={(event) => onUpdateItem(selectedProposal.id, item.id, { description: event.target.value })} />
                <input type="number" step="0.001" defaultValue={item.quantity} onBlur={(event) => onUpdateItem(selectedProposal.id, item.id, { quantity: Number(event.target.value) || 0 })} />
                <input defaultValue={item.unit} onBlur={(event) => onUpdateItem(selectedProposal.id, item.id, { unit: event.target.value })} />
                <input type="number" step="0.01" defaultValue={item.unit_price} onBlur={(event) => onUpdateItem(selectedProposal.id, item.id, { unit_price: Number(event.target.value) || 0 })} />
                <strong>{formatCurrency(item.total_price)}</strong>
                <button className="icon-button" onClick={() => onDeleteItem(selectedProposal.id, item.id)} aria-label="Remover item">
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
          </div>

          <div className="proposal-financial">
            <span>Subtotal: <strong>{formatCurrency(selectedProposal.subtotal)}</strong></span>
            <label>
              Desconto
              <input type="number" step="0.01" defaultValue={selectedProposal.discount} onBlur={(event) => onUpdate(selectedProposal.id, { discount: Number(event.target.value) || 0 })} />
            </label>
            <span>Total: <strong>{formatCurrency(selectedProposal.total_amount)}</strong></span>
            <label>
              Validade
              <input type="number" defaultValue={selectedProposal.validity_days} onBlur={(event) => onUpdate(selectedProposal.id, { validity_days: Number(event.target.value) || 7 })} />
            </label>
          </div>

          <label className="proposal-wide-field">
            Condições de pagamento
            <textarea defaultValue={selectedProposal.payment_conditions ?? ""} onBlur={(event) => onUpdate(selectedProposal.id, { payment_conditions: event.target.value })} />
          </label>
          <label className="proposal-wide-field">
            Observações
            <textarea defaultValue={selectedProposal.notes ?? ""} onBlur={(event) => onUpdate(selectedProposal.id, { notes: event.target.value })} />
          </label>

          <div className="proposal-actions">
            <select value={selectedProposal.status} onChange={(event) => onUpdateStatus(selectedProposal.id, event.target.value)}>
              {PROPOSAL_STATUSES.map((status) => (
                <option value={status.value} key={status.value}>
                  {status.label}
                </option>
              ))}
            </select>
            <button className="secondary-button" onClick={() => onGeneratePdf(selectedProposal.id)}>
              <FileText size={16} />
              {selectedProposal.pdf_url ? "Gerar novo PDF" : "Gerar PDF"}
            </button>
          </div>
          {selectedProposal.pdf_url && <p className="proposal-pdf-path">PDF: {selectedProposal.pdf_url}</p>}

          <div className="proposal-send-panel">
            <div className="proposal-section-title">
              <strong>Enviar proposta</strong>
              <span>Escolha o canal antes de solicitar envio.</span>
            </div>
            <div className="proposal-send-grid">
              <label>
                Canal
                <select
                  value={sendDraft.channel}
                  onChange={(event) => setSendDraft((current) => ({ ...current, channel: event.target.value as ProposalSendRequest["channel"] }))}
                >
                  <option value="manual">Manual</option>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="email">E-mail</option>
                  <option value="secure_link">Link seguro</option>
                </select>
              </label>
              <label>
                Telefone
                <input
                  value={sendDraft.recipient_phone ?? selectedProposal.customer_phone ?? ""}
                  onChange={(event) => setSendDraft((current) => ({ ...current, recipient_phone: event.target.value }))}
                />
              </label>
              <label>
                E-mail
                <input
                  value={sendDraft.recipient_email ?? selectedProposal.customer_email ?? ""}
                  onChange={(event) => setSendDraft((current) => ({ ...current, recipient_email: event.target.value }))}
                />
              </label>
              <label className="proposal-checkbox">
                <input
                  type="checkbox"
                  checked={Boolean(sendDraft.mark_as_sent)}
                  onChange={(event) => setSendDraft((current) => ({ ...current, mark_as_sent: event.target.checked }))}
                />
                Marcar manual como enviada
              </label>
            </div>
            <label className="proposal-wide-field">
              Mensagem opcional
              <textarea
                value={sendDraft.message ?? ""}
                onChange={(event) => setSendDraft((current) => ({ ...current, message: event.target.value }))}
                placeholder="Mensagem curta para o cliente. Deixe em branco para usar o texto padrao."
              />
            </label>
            <button className="primary-button" onClick={() => onSend(selectedProposal.id, sendDraft)} disabled={loadingKey === `send:${selectedProposal.id}`}>
              <Send size={16} />
              {loadingKey === `send:${selectedProposal.id}` ? "Enviando" : "Solicitar envio"}
            </button>
          </div>
        </article>
      )}
        </>
      )}
    </section>
  );
}

function PriceTablePanel({
  priceItems,
  onCreate,
  onUpdate,
  onToggle,
  onDelete,
}: {
  priceItems: ProposalPriceItem[];
  onCreate: (payload: Partial<ProposalPriceItem>) => Promise<void>;
  onUpdate: (id: string, payload: Partial<ProposalPriceItem>) => Promise<void>;
  onToggle: (id: string, active: boolean) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const [draft, setDraft] = useState({
    category: "kit_fotovoltaico",
    description: "",
    default_unit: "un",
    default_quantity: 1,
    default_unit_price: 0,
    sort_order: 0,
    notes: "",
  });

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.description.trim()) return;
    await onCreate({ ...draft, active: true, notes: draft.notes || null });
    setDraft({ category: "kit_fotovoltaico", description: "", default_unit: "un", default_quantity: 1, default_unit_price: 0, sort_order: 0, notes: "" });
  }

  return (
    <div className="price-table-layout">
      <form className="price-item-form" onSubmit={submit}>
        <strong>Novo item da tabela</strong>
        <select value={draft.category} onChange={(event) => setDraft((current) => ({ ...current, category: event.target.value }))}>
          {PROPOSAL_ITEM_CATEGORIES.map((category) => (
            <option key={category.value} value={category.value}>
              {category.label}
            </option>
          ))}
        </select>
        <input placeholder="Descricao" value={draft.description} onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))} />
        <input placeholder="Unidade" value={draft.default_unit} onChange={(event) => setDraft((current) => ({ ...current, default_unit: event.target.value }))} />
        <input type="number" step="0.001" value={draft.default_quantity} onChange={(event) => setDraft((current) => ({ ...current, default_quantity: Number(event.target.value) || 0 }))} />
        <input type="number" step="0.01" value={draft.default_unit_price} onChange={(event) => setDraft((current) => ({ ...current, default_unit_price: Number(event.target.value) || 0 }))} />
        <input type="number" value={draft.sort_order} onChange={(event) => setDraft((current) => ({ ...current, sort_order: Number(event.target.value) || 0 }))} />
        <input placeholder="Observacoes internas" value={draft.notes} onChange={(event) => setDraft((current) => ({ ...current, notes: event.target.value }))} />
        <button className="primary-button" type="submit">
          <Plus size={16} />
          Adicionar item
        </button>
      </form>

      <div className="table-panel">
        <TableHeader columns={["Categoria", "Descricao", "Qtd", "Un", "Unitario", "Status", "Acoes"]} />
        {priceItems.map((item) => (
          <div className="price-item-row" key={item.id}>
            <select defaultValue={item.category} onBlur={(event) => onUpdate(item.id, { category: event.target.value })}>
              {PROPOSAL_ITEM_CATEGORIES.map((category) => (
                <option key={category.value} value={category.value}>
                  {category.label}
                </option>
              ))}
            </select>
            <input defaultValue={item.description} onBlur={(event) => onUpdate(item.id, { description: event.target.value })} />
            <input type="number" step="0.001" defaultValue={item.default_quantity} onBlur={(event) => onUpdate(item.id, { default_quantity: Number(event.target.value) || 0 })} />
            <input defaultValue={item.default_unit} onBlur={(event) => onUpdate(item.id, { default_unit: event.target.value })} />
            <input type="number" step="0.01" defaultValue={item.default_unit_price} onBlur={(event) => onUpdate(item.id, { default_unit_price: Number(event.target.value) || 0 })} />
            <span className={item.active ? "status-badge status-badge--open" : "status-badge"}>{item.active ? "Ativo" : "Inativo"}</span>
            <div className="row-actions">
              <button className="text-button" onClick={() => onToggle(item.id, !item.active)}>
                {item.active ? "Inativar" : "Ativar"}
              </button>
              <button className="icon-button" onClick={() => onDelete(item.id)} aria-label="Excluir item de preco">
                <Trash2 size={15} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TicketsView({
  tickets,
  token,
  refresh,
  analyses,
  loadingKey,
  onAnalyze,
  onCopy,
}: {
  tickets: Ticket[];
  token: string;
  refresh: () => Promise<void>;
  analyses: Record<string, AIAnalysis>;
  loadingKey: string | null;
  onAnalyze: (id: string) => Promise<void>;
  onCopy: (text: string) => void;
}) {
  async function changeStatus(id: string, status: string) {
    await adminApi.updateTicketStatus(token, id, status);
    await refresh();
  }

  return (
    <section className="table-panel">
      <TableHeader columns={["Problema", "Gravidade", "Risco IA", "Status", "Notas", "Ação"]} />
      {tickets.map((ticket) => (
        <div className="table-group" key={ticket.id}>
          <div className="table-row table-row--six">
            <span>{ticket.problem_type}</span>
            <SeverityPill severity={ticket.severity} />
            <ScoreBadge score={analyses[ticket.id]?.priority_score} type="ticket" />
            <span>{ticket.status}</span>
            <span className="truncate">{ticket.technical_notes ?? "Sem notas"}</span>
            <div className="row-actions">
              <select value={ticket.status} onChange={(event) => changeStatus(ticket.id, event.target.value)}>
                <option>Novo</option>
                <option>Em triagem</option>
                <option>Aguardando cliente</option>
                <option>Encaminhado para técnico</option>
                <option>Em atendimento</option>
                <option>Resolvido</option>
                <option>Cancelado</option>
                <option>Escalado para gestor</option>
              </select>
              <button
                className="text-button text-button--ai"
                onClick={() => onAnalyze(ticket.id)}
                disabled={loadingKey === `ticket:${ticket.id}`}
              >
                <Sparkles size={15} />
                {analyses[ticket.id] ? "Regenerar" : "Analisar"}
              </button>
            </div>
          </div>
          {analyses[ticket.id] && <AnalysisPanel analysis={analyses[ticket.id]} onCopy={onCopy} variant="ticket" />}
        </div>
      ))}
    </section>
  );
}

function AnalysisPanel({
  analysis,
  onCopy,
  variant,
}: {
  analysis: AIAnalysis;
  onCopy: (text: string) => void;
  variant: "conversation" | "lead" | "ticket";
}) {
  const title =
    variant === "lead"
      ? "Análise Inteligente do lead"
      : variant === "ticket"
        ? "Análise Inteligente do chamado"
        : "Análise Inteligente do atendimento";

  return (
    <article className="analysis-panel">
      <div className="analysis-panel__header">
        <div>
          <strong>{title}</strong>
          <span>{analysis.executive_summary}</span>
        </div>
        <ScoreBadge score={analysis.priority_score} type={variant === "ticket" ? "ticket" : "lead"} />
      </div>
      <div className="analysis-chips">
        <span>Sentimento: {analysis.customer_sentiment}</span>
        <span>Urgência: {analysis.urgency_level}</span>
        <span>Oportunidade: {analysis.commercial_opportunity}</span>
        <span>Risco: {analysis.technical_risk}</span>
      </div>
      <div className="analysis-grid">
        <div>
          <small>Dados faltantes</small>
          <p>{analysis.missing_data.length ? analysis.missing_data.join(", ") : "Nenhum dado crítico pendente"}</p>
        </div>
        <div>
          <small>Próxima ação recomendada</small>
          <p>{analysis.recommended_next_action}</p>
        </div>
      </div>
      <div className="suggested-reply">
        <small>Resposta sugerida ao cliente</small>
        <p>{analysis.suggested_reply}</p>
        <button className="text-button" onClick={() => onCopy(analysis.suggested_reply)}>
          <Copy size={15} />
          Copiar resposta
        </button>
      </div>
    </article>
  );
}

function ScoreBadge({ score, type }: { score?: number; type: "lead" | "ticket" | "conversation" }) {
  if (typeof score !== "number") {
    return <span className="score-badge score-badge--empty">Sem IA</span>;
  }
  const label =
    type === "ticket"
      ? score >= 85
        ? "Crítico"
        : score >= 60
          ? "Alto"
          : score >= 35
            ? "Médio"
            : "Baixo"
      : score >= 75
        ? "Quente"
        : score >= 45
          ? "Morno"
          : "Frio";
  return (
    <span className={`score-badge score-badge--${label.toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "")}`}>
      {score}/100 · {label}
    </span>
  );
}

type KnowledgeDraft = {
  title: string;
  question: string;
  answer: string;
  category: string;
  keywords: string;
  videoTitle: string;
  videoUrl: string;
  sendVideoWithAnswer: boolean;
  resourceTitle: string;
  resourceUrl: string;
  resourceType: string;
  sendResourceWithAnswer: boolean;
};

function KnowledgeView({
  articles,
  draft,
  setDraft,
  onSubmit,
}: {
  articles: KnowledgeArticle[];
  draft: KnowledgeDraft;
  setDraft: (draft: KnowledgeDraft) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <div className="knowledge-layout">
      <form className="article-form" onSubmit={onSubmit}>
        <strong>Novo artigo</strong>
        <input
          placeholder="Titulo"
          value={draft.title}
          onChange={(event) => setDraft({ ...draft, title: event.target.value })}
          required
        />
        <input
          placeholder="Pergunta"
          value={draft.question}
          onChange={(event) => setDraft({ ...draft, question: event.target.value })}
          required
        />
        <textarea
          placeholder="Resposta oficial"
          value={draft.answer}
          onChange={(event) => setDraft({ ...draft, answer: event.target.value })}
          required
        />
        <select value={draft.category} onChange={(event) => setDraft({ ...draft, category: event.target.value })}>
          <option>Energia solar fotovoltaica</option>
          <option>Economia na conta de luz</option>
          <option>Creditos de energia</option>
          <option>Financiamento</option>
          <option>Instalação</option>
          <option>Homologação</option>
          <option>Monitoramento remoto</option>
          <option>Inversores</option>
          <option>Garantia</option>
          <option>Manutenção</option>
          <option>Limpeza das placas</option>
          <option>Pós-venda</option>
          <option>Segurança elétrica</option>
        </select>
        <input
          placeholder="Palavras-chave separadas por vírgula"
          value={draft.keywords}
          onChange={(event) => setDraft({ ...draft, keywords: event.target.value })}
        />
        <div className="form-divider">Vídeo oficial</div>
        <input
          placeholder="Título do vídeo"
          value={draft.videoTitle}
          onChange={(event) => setDraft({ ...draft, videoTitle: event.target.value })}
        />
        <input
          placeholder="Link do vídeo do YouTube"
          value={draft.videoUrl}
          onChange={(event) => setDraft({ ...draft, videoUrl: event.target.value })}
        />
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={draft.sendVideoWithAnswer}
            onChange={(event) => setDraft({ ...draft, sendVideoWithAnswer: event.target.checked })}
          />
          Enviar vídeo junto com a resposta
        </label>
        <div className="form-divider">Material de apoio</div>
        <input
          placeholder="Título do material de apoio"
          value={draft.resourceTitle}
          onChange={(event) => setDraft({ ...draft, resourceTitle: event.target.value })}
        />
        <input
          placeholder="Link do material de apoio"
          value={draft.resourceUrl}
          onChange={(event) => setDraft({ ...draft, resourceUrl: event.target.value })}
        />
        <select value={draft.resourceType} onChange={(event) => setDraft({ ...draft, resourceType: event.target.value })}>
          <option value="youtube">YouTube</option>
          <option value="pdf">PDF</option>
          <option value="manual">Manual</option>
          <option value="artigo">Artigo</option>
          <option value="site">Site</option>
          <option value="outro">Outro</option>
        </select>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={draft.sendResourceWithAnswer}
            onChange={(event) => setDraft({ ...draft, sendResourceWithAnswer: event.target.checked })}
          />
          Enviar material junto com a resposta
        </label>
        <ResponsePreview draft={draft} />
        <button className="primary-button" type="submit">
          <BookOpenText size={18} />
          Salvar artigo
        </button>
      </form>

      <section className="article-list">
        {articles.map((article) => (
          <article className="article-item" key={article.id}>
            <div>
              <strong>{article.title}</strong>
              <span>{article.category}</span>
            </div>
            <div className="article-badges">
              {article.video_url && <span>Vídeo</span>}
              {article.resource_url && <span>Material</span>}
              {article.send_video_with_answer && <span>Vídeo automático</span>}
              {article.send_resource_with_answer && <span>Material automático</span>}
            </div>
            <p>{article.question}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

function ResponsePreview({ draft }: { draft: KnowledgeDraft }) {
  return (
    <section className="response-preview" aria-label="Prévia da resposta">
      <strong>Prévia para o cliente</strong>
      <p>{draft.answer || "A resposta oficial aparecerá aqui."}</p>
      {draft.sendVideoWithAnswer && draft.videoUrl && (
        <div>
          <small>Vídeo recomendado:</small>
          <span>{draft.videoTitle || "Vídeo oficial da Solar Soluções"}</span>
          <a href={draft.videoUrl} target="_blank" rel="noreferrer">
            {draft.videoUrl}
          </a>
        </div>
      )}
      {draft.sendResourceWithAnswer && draft.resourceUrl && (
        <div>
          <small>Material de apoio:</small>
          <span>{draft.resourceTitle || "Material oficial da Solar Soluções"}</span>
          <a href={draft.resourceUrl} target="_blank" rel="noreferrer">
            {draft.resourceUrl}
          </a>
        </div>
      )}
    </section>
  );
}

function TableHeader({ columns }: { columns: string[] }) {
  return (
    <div className="table-header table-row--six">
      {columns.map((column) => (
        <strong key={column}>{column}</strong>
      ))}
    </div>
  );
}

function SeverityPill({ severity }: { severity: string | null }) {
  const normalized = severity ?? "baixa";
  return <span className={`severity-pill severity-pill--${normalized}`}>{severity ?? "N/I"}</span>;
}
