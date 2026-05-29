import {
  AlertTriangle,
  BarChart3,
  BookOpenText,
  CheckCircle2,
  Copy,
  Headphones,
  LogIn,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TicketCheck,
  UsersRound,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { adminApi, login } from "../api";
import type { AIAnalysis, Conversation, DashboardAIInsights, DashboardMetrics, KnowledgeArticle, Lead, Ticket } from "../types";

type AdminData = {
  metrics: DashboardMetrics | null;
  aiInsights: DashboardAIInsights | null;
  conversations: Conversation[];
  leads: Lead[];
  tickets: Ticket[];
  knowledge: KnowledgeArticle[];
};

const emptyData: AdminData = {
  metrics: null,
  aiInsights: null,
  conversations: [],
  leads: [],
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
  const [error, setError] = useState<string | null>(null);
  const [articleDraft, setArticleDraft] = useState({
    title: "",
    question: "",
    answer: "",
    category: "Energia solar fotovoltaica",
    keywords: "",
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
        const [metrics, aiInsights, conversations, leads, tickets, knowledge] = await Promise.all([
          adminApi.metrics(currentToken),
          adminApi.aiInsights(currentToken),
          adminApi.conversations(currentToken),
          adminApi.leads(currentToken),
          adminApi.tickets(currentToken),
          adminApi.knowledge(currentToken),
        ]);
        setData({ metrics, aiInsights, conversations, leads, tickets, knowledge });
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
      active: true,
      use_for_ai: true,
    });
    setArticleDraft({
      title: "",
      question: "",
      answer: "",
      category: "Energia solar fotovoltaica",
      keywords: "",
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
    chamados: "Triagem técnica com gravidade e status.",
    base: "Perguntas e respostas oficiais para IA e atendimento.",
  };
  return subtitles[view] ?? "";
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
  async function requestHandoff(id: string) {
    await adminApi.handoff(token, id, "Assumido manualmente pelo painel.");
    await refresh();
  }

  return (
    <section className="table-panel">
      <TableHeader columns={["Canal", "Intenção", "Gravidade", "Status", "Resumo", "Ação"]} />
      {conversations.map((conversation) => (
        <div className="table-group" key={conversation.id}>
          <div className="table-row table-row--six">
            <span>{conversation.channel}</span>
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

function LeadsView({
  leads,
  analyses,
  loadingKey,
  onAnalyze,
  onCopy,
}: {
  leads: Lead[];
  analyses: Record<string, AIAnalysis>;
  loadingKey: string | null;
  onAnalyze: (id: string) => Promise<void>;
  onCopy: (text: string) => void;
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
            </div>
          </div>
          {analyses[lead.id] && <AnalysisPanel analysis={analyses[lead.id]} onCopy={onCopy} variant="lead" />}
        </div>
      ))}
    </section>
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

function KnowledgeView({
  articles,
  draft,
  setDraft,
  onSubmit,
}: {
  articles: KnowledgeArticle[];
  draft: { title: string; question: string; answer: string; category: string; keywords: string };
  setDraft: (draft: { title: string; question: string; answer: string; category: string; keywords: string }) => void;
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
            <p>{article.question}</p>
          </article>
        ))}
      </section>
    </div>
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
