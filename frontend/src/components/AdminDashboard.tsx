import {
  AlertTriangle,
  BarChart3,
  BookOpenText,
  CheckCircle2,
  Headphones,
  LogIn,
  RefreshCw,
  ShieldCheck,
  TicketCheck,
  UsersRound,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { adminApi, login } from "../api";
import type { Conversation, DashboardMetrics, KnowledgeArticle, Lead, Ticket } from "../types";

type AdminData = {
  metrics: DashboardMetrics | null;
  conversations: Conversation[];
  leads: Lead[];
  tickets: Ticket[];
  knowledge: KnowledgeArticle[];
};

const emptyData: AdminData = {
  metrics: null,
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
        const [metrics, conversations, leads, tickets, knowledge] = await Promise.all([
          adminApi.metrics(currentToken),
          adminApi.conversations(currentToken),
          adminApi.leads(currentToken),
          adminApi.tickets(currentToken),
          adminApi.knowledge(currentToken),
        ]);
        setData({ metrics, conversations, leads, tickets, knowledge });
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

        {activeView === "dashboard" && <DashboardView metrics={data.metrics} tickets={data.tickets} />}
        {activeView === "conversas" && <ConversationsView conversations={data.conversations} token={token} refresh={loadData} />}
        {activeView === "leads" && <LeadsView leads={data.leads} />}
        {activeView === "chamados" && <TicketsView tickets={data.tickets} token={token} refresh={loadData} />}
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

function DashboardView({ metrics, tickets }: { metrics: DashboardMetrics | null; tickets: Ticket[] }) {
  const cards = [
    { label: "Atendimentos", value: metrics?.total_atendimentos ?? 0, icon: <Headphones size={18} /> },
    { label: "Leads", value: metrics?.leads_orcamento ?? 0, icon: <UsersRound size={18} /> },
    { label: "Chamados abertos", value: metrics?.chamados_abertos ?? 0, icon: <TicketCheck size={18} /> },
    { label: "Transferidos", value: metrics?.transferidos_para_humano ?? 0, icon: <ShieldCheck size={18} /> },
    { label: "Resolvidos pelo bot", value: metrics?.resolvidos_pelo_bot ?? 0, icon: <CheckCircle2 size={18} /> },
    { label: "Conversão", value: `${metrics?.taxa_conversao_orcamento ?? 0}%`, icon: <BarChart3 size={18} /> },
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
    </>
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
}: {
  conversations: Conversation[];
  token: string;
  refresh: () => Promise<void>;
}) {
  async function requestHandoff(id: string) {
    await adminApi.handoff(token, id, "Assumido manualmente pelo painel.");
    await refresh();
  }

  return (
    <section className="table-panel">
      <TableHeader columns={["Canal", "Intencao", "Gravidade", "Status", "Resumo", "Acao"]} />
      {conversations.map((conversation) => (
        <div className="table-row table-row--six" key={conversation.id}>
          <span>{conversation.channel}</span>
          <span>{conversation.intent ?? "N/I"}</span>
          <SeverityPill severity={conversation.severity} />
          <span>{conversation.status}</span>
          <span className="truncate">{conversation.summary ?? "Sem resumo"}</span>
          <button className="text-button" onClick={() => requestHandoff(conversation.id)}>
            Assumir
          </button>
        </div>
      ))}
    </section>
  );
}

function LeadsView({ leads }: { leads: Lead[] }) {
  return (
    <section className="table-panel">
      <TableHeader columns={["Tipo", "Conta media", "Distribuidora", "Financiamento", "Status", "Observacoes"]} />
      {leads.map((lead) => (
        <div className="table-row table-row--six" key={lead.id}>
          <span>{lead.property_type ?? "N/I"}</span>
          <span>{lead.average_bill ? `R$ ${lead.average_bill}` : "N/I"}</span>
          <span>{lead.utility_company ?? "N/I"}</span>
          <span>{lead.financing_interest === null ? "N/I" : lead.financing_interest ? "Sim" : "Não"}</span>
          <span>{lead.status}</span>
          <span className="truncate">{lead.notes ?? "Sem notas"}</span>
        </div>
      ))}
    </section>
  );
}

function TicketsView({ tickets, token, refresh }: { tickets: Ticket[]; token: string; refresh: () => Promise<void> }) {
  async function changeStatus(id: string, status: string) {
    await adminApi.updateTicketStatus(token, id, status);
    await refresh();
  }

  return (
    <section className="table-panel">
      <TableHeader columns={["Problema", "Gravidade", "Status", "Notas", "Criado em", "Acao"]} />
      {tickets.map((ticket) => (
        <div className="table-row table-row--six" key={ticket.id}>
          <span>{ticket.problem_type}</span>
          <SeverityPill severity={ticket.severity} />
          <span>{ticket.status}</span>
          <span className="truncate">{ticket.technical_notes ?? "Sem notas"}</span>
          <span>{new Date(ticket.created_at).toLocaleString("pt-BR")}</span>
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
        </div>
      ))}
    </section>
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
