import {
  AlertTriangle,
  BarChart3,
  BookOpenText,
  CalendarClock,
  CheckCircle2,
  Copy,
  ExternalLink,
  FileText,
  Headphones,
  Link2,
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
  XCircle,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { adminApi, login } from "../api";
import type {
  AIAnalysis,
  CompanySettings,
  Conversation,
  DashboardAIInsights,
  DashboardMetrics,
  EnergyBillExtraction,
  EnergyBillHistory,
  EnergyBillParsedData,
  KnowledgeArticle,
  Lead,
  Proposal,
  ProposalFollowUp,
  ProposalKit,
  ProposalKitItem,
  ProposalKitSimulation,
  ProposalPriceItem,
  ProposalShareLink,
  ProposalSendRequest,
  Ticket,
} from "../types";

type AdminData = {
  metrics: DashboardMetrics | null;
  aiInsights: DashboardAIInsights | null;
  conversations: Conversation[];
  leads: Lead[];
  proposals: Proposal[];
  proposalFollowups: ProposalFollowUp[];
  proposalPriceItems: ProposalPriceItem[];
  proposalKits: ProposalKit[];
  energyBillExtractions: EnergyBillExtraction[];
  companySettings: CompanySettings | null;
  tickets: Ticket[];
  knowledge: KnowledgeArticle[];
};

const emptyData: AdminData = {
  metrics: null,
  aiInsights: null,
  conversations: [],
  leads: [],
  proposals: [],
  proposalFollowups: [],
  proposalPriceItems: [],
  proposalKits: [],
  energyBillExtractions: [],
  companySettings: null,
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
  const [energyBillLoadingKey, setEnergyBillLoadingKey] = useState<string | null>(null);
  const [energyBillPreview, setEnergyBillPreview] = useState<EnergyBillParsedData | null>(null);
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
        const [
          metrics,
          aiInsights,
          conversations,
          leads,
          proposals,
          proposalFollowups,
          proposalPriceItems,
          proposalKits,
          energyBillExtractions,
          companySettings,
          tickets,
          knowledge,
        ] = await Promise.all([
          adminApi.metrics(currentToken),
          adminApi.aiInsights(currentToken),
          adminApi.conversations(currentToken),
          adminApi.leads(currentToken),
          adminApi.proposals(currentToken),
          adminApi.proposalFollowups(currentToken),
          adminApi.proposalPriceItems(currentToken),
          adminApi.proposalKits(currentToken),
          adminApi.energyBills(currentToken),
          adminApi.companySettings(currentToken),
          adminApi.tickets(currentToken),
          adminApi.knowledge(currentToken),
        ]);
        setData({ metrics, aiInsights, conversations, leads, proposals, proposalFollowups, proposalPriceItems, proposalKits, energyBillExtractions, companySettings, tickets, knowledge });
      } catch (loadError) {
        setError("NÃ£o foi possÃ­vel carregar o painel. Verifique o login e a API.");
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
      setError("Login invÃ¡lido ou API indisponÃ­vel.");
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
      setError("NÃ£o foi possÃ­vel gerar a anÃ¡lise inteligente da conversa.");
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
      setError("NÃ£o foi possÃ­vel gerar a anÃ¡lise inteligente do lead.");
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
      setError("NÃ£o foi possÃ­vel gerar a anÃ¡lise inteligente do chamado.");
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
      setError("NÃ£o foi possÃ­vel gerar a proposta a partir do lead.");
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
        notes: "Valores e condiÃ§Ãµes devem ser revisados pela equipe da Solar SoluÃ§Ãµes antes do envio ao cliente.",
        payment_conditions: "A definir apÃ³s revisÃ£o comercial.",
        discount: 0,
      });
      setSelectedProposal(proposal);
      await loadData();
    } catch (proposalError) {
      setError("NÃ£o foi possÃ­vel criar a proposta manual.");
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
      setError("NÃ£o foi possÃ­vel abrir a proposta.");
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

  async function handleCreateProposalShareLink(id: string) {
    if (!token) return;
    setProposalLoadingKey(`share:${id}`);
    try {
      const link = await adminApi.createProposalShareLink(token, id, 15);
      await navigator.clipboard?.writeText(link.public_url ?? "");
      setError("Link seguro gerado e copiado para a area de transferencia.");
      setSelectedProposal(await adminApi.getProposal(token, id));
      await loadData();
    } finally {
      setProposalLoadingKey(null);
    }
  }

  async function handleRevokeProposalShareLink(id: string) {
    if (!token) return;
    await adminApi.revokeProposalShareLink(token, id);
    if (selectedProposal) setSelectedProposal(await adminApi.getProposal(token, selectedProposal.id));
    await loadData();
  }

  async function handleCreateProposalFollowup(id: string, channel: string, dueAt: string, note: string) {
    if (!token) return;
    await adminApi.createProposalFollowup(token, id, {
      channel,
      due_at: dueAt,
      note,
    });
    setSelectedProposal(await adminApi.getProposal(token, id));
    await loadData();
  }

  async function handleCompleteProposalFollowup(id: string) {
    if (!token) return;
    await adminApi.completeProposalFollowup(token, id);
    if (selectedProposal) setSelectedProposal(await adminApi.getProposal(token, selectedProposal.id));
    await loadData();
  }

  async function handleCancelProposalFollowup(id: string) {
    if (!token) return;
    await adminApi.cancelProposalFollowup(token, id);
    if (selectedProposal) setSelectedProposal(await adminApi.getProposal(token, selectedProposal.id));
    await loadData();
  }

  async function handleUpdateCompanySettings(payload: Partial<CompanySettings>) {
    if (!token) return;
    await adminApi.updateCompanySettings(token, payload);
    await loadData();
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

  async function handleCreateProposalKit(payload: Partial<ProposalKit>) {
    if (!token) return;
    await adminApi.createProposalKit(token, payload);
    await loadData();
  }

  async function handleUpdateProposalKit(id: string, payload: Partial<ProposalKit>) {
    if (!token) return;
    await adminApi.updateProposalKit(token, id, payload);
    await loadData();
  }

  async function handleToggleProposalKit(id: string, active: boolean) {
    if (!token) return;
    await adminApi.updateProposalKitActive(token, id, active);
    await loadData();
  }

  async function handleDeleteProposalKit(id: string) {
    if (!token) return;
    await adminApi.deleteProposalKit(token, id);
    await loadData();
  }

  async function handleAddProposalKitItem(kitId: string, payload: Partial<ProposalKitItem>) {
    if (!token) return;
    await adminApi.addProposalKitItem(token, kitId, payload);
    await loadData();
  }

  async function handleUpdateProposalKitItem(kitId: string, itemId: string, payload: Partial<ProposalKitItem>) {
    if (!token) return;
    await adminApi.updateProposalKitItem(token, kitId, itemId, payload);
    await loadData();
  }

  async function handleDeleteProposalKitItem(kitId: string, itemId: string) {
    if (!token) return;
    await adminApi.deleteProposalKitItem(token, kitId, itemId);
    await loadData();
  }

  async function handleSimulateProposalKit(payload: { average_bill?: number | null; estimated_monthly_generation_kwh?: number | null; estimated_power_kwp?: number | null }) {
    if (!token) return null;
    return adminApi.simulateProposalKit(token, payload);
  }

  async function handleParseEnergyBillText(rawText: string) {
    if (!token) return;
    setEnergyBillLoadingKey("parse-text");
    setError(null);
    try {
      setEnergyBillPreview(await adminApi.parseEnergyBillText(token, rawText));
    } catch (parseError) {
      setError("Nao foi possivel interpretar o texto da conta. Verifique o conteudo informado.");
    } finally {
      setEnergyBillLoadingKey(null);
    }
  }

  async function handleUploadEnergyBill(file: File, leadId?: string) {
    if (!token) return;
    setEnergyBillLoadingKey("upload");
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (leadId) formData.append("lead_id", leadId);
      await adminApi.uploadEnergyBill(token, formData);
      await loadData();
    } catch (uploadError) {
      setError("Nao foi possivel processar o arquivo da conta. Use PDF, imagem ou TXT dentro do limite configurado.");
    } finally {
      setEnergyBillLoadingKey(null);
    }
  }

  async function handleUpdateEnergyBill(id: string, payload: Partial<EnergyBillExtraction>) {
    if (!token) return;
    await adminApi.updateEnergyBill(token, id, payload);
    await loadData();
  }

  async function handleConfirmEnergyBill(id: string) {
    if (!token) return;
    setEnergyBillLoadingKey(`confirm:${id}`);
    try {
      await adminApi.confirmEnergyBill(token, id);
      await loadData();
    } finally {
      setEnergyBillLoadingKey(null);
    }
  }

  async function handleApplyEnergyBillToLead(id: string, leadId: string) {
    if (!token || !leadId) return;
    setEnergyBillLoadingKey(`apply:${id}`);
    setError(null);
    try {
      await adminApi.applyEnergyBillToLead(token, id, leadId);
      await loadData();
    } catch (applyError) {
      setError("Existem campos importantes pendentes. Revise e confirme a leitura antes de aplicar ao lead.");
    } finally {
      setEnergyBillLoadingKey(null);
    }
  }

  async function handleGenerateProposalFromEnergyBill(id: string) {
    if (!token) return;
    setEnergyBillLoadingKey(`proposal:${id}`);
    try {
      const proposal = await adminApi.generateProposalFromEnergyBill(token, id);
      setSelectedProposal(proposal);
      setActiveView("propostas");
      await loadData();
    } catch (proposalError) {
      setError("A conta precisa estar ligada a um lead antes de gerar a proposta.");
    } finally {
      setEnergyBillLoadingKey(null);
    }
  }

  async function handleDiscardEnergyBill(id: string) {
    if (!token) return;
    await adminApi.discardEnergyBill(token, id);
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
              <span>Painel Solar SoluÃ§Ãµes</span>
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
            <small>Solar SoluÃ§Ãµes</small>
          </div>
        </div>
        <nav>
          <NavButton id="dashboard" label="Dashboard" icon={<BarChart3 size={18} />} active={activeView} onClick={setActiveView} />
          <NavButton id="conversas" label="Atendimentos" icon={<Headphones size={18} />} active={activeView} onClick={setActiveView} />
          <NavButton id="leads" label="Leads" icon={<UsersRound size={18} />} active={activeView} onClick={setActiveView} />
          <NavButton id="contas" label="Contas" icon={<FileText size={18} />} active={activeView} onClick={setActiveView} />
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
        {activeView === "contas" && (
          <EnergyBillsView
            extractions={data.energyBillExtractions}
            leads={data.leads}
            preview={energyBillPreview}
            loadingKey={energyBillLoadingKey}
            onParseText={handleParseEnergyBillText}
            onUpload={handleUploadEnergyBill}
            onUpdate={handleUpdateEnergyBill}
            onConfirm={handleConfirmEnergyBill}
            onApplyToLead={handleApplyEnergyBillToLead}
            onGenerateProposal={handleGenerateProposalFromEnergyBill}
            onDiscard={handleDiscardEnergyBill}
          />
        )}
        {activeView === "propostas" && (
          <ProposalsView
            proposals={data.proposals}
            followups={data.proposalFollowups}
            priceItems={data.proposalPriceItems}
            kits={data.proposalKits}
            companySettings={data.companySettings}
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
            onCreateShareLink={handleCreateProposalShareLink}
            onRevokeShareLink={handleRevokeProposalShareLink}
            onCreateFollowup={handleCreateProposalFollowup}
            onCompleteFollowup={handleCompleteProposalFollowup}
            onCancelFollowup={handleCancelProposalFollowup}
            onCreatePriceItem={handleCreatePriceItem}
            onUpdatePriceItem={handleUpdatePriceItem}
            onTogglePriceItem={handleTogglePriceItem}
            onDeletePriceItem={handleDeletePriceItem}
            onCreateKit={handleCreateProposalKit}
            onUpdateKit={handleUpdateProposalKit}
            onToggleKit={handleToggleProposalKit}
            onDeleteKit={handleDeleteProposalKit}
            onAddKitItem={handleAddProposalKitItem}
            onUpdateKitItem={handleUpdateProposalKitItem}
            onDeleteKitItem={handleDeleteProposalKitItem}
            onSimulateKit={handleSimulateProposalKit}
            onUpdateCompanySettings={handleUpdateCompanySettings}
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
    leads: "Leads de orÃ§amento",
    contas: "Contas de energia",
    propostas: "Propostas",
    chamados: "Chamados tÃ©cnicos",
    base: "Base de conhecimento",
  };
  return titles[view] ?? "Painel";
}

function subtitleFor(view: string) {
  const subtitles: Record<string, string> = {
    dashboard: "Indicadores de atendimento, vendas e suporte.",
    conversas: "HistÃ³rico das conversas e transferÃªncias.",
    leads: "SolicitaÃ§Ãµes comerciais captadas pelo Solis.",
    contas: "Leitura inteligente, revisao humana e dados para propostas.",
    propostas: "CriaÃ§Ã£o, revisÃ£o, PDF e envio de propostas comerciais.",
    chamados: "Triagem tÃ©cnica com gravidade e status.",
    base: "Perguntas e respostas oficiais para IA e atendimento.",
  };
  return subtitles[view] ?? "";
}

const PROPOSAL_STATUSES = [
  { value: "draft", label: "Rascunho" },
  { value: "under_review", label: "Em revisÃ£o" },
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
  { value: "materiais_eletricos", label: "Materiais elÃ©tricos" },
  { value: "mao_de_obra", label: "MÃ£o de obra" },
  { value: "projeto", label: "Projeto" },
  { value: "homologacao", label: "HomologaÃ§Ã£o" },
  { value: "taxas_concessionaria", label: "Taxas e adequaÃ§Ãµes" },
  { value: "estrutura_fixacao", label: "Estrutura de fixaÃ§Ã£o" },
  { value: "deslocamento", label: "Deslocamento" },
  { value: "monitoramento", label: "Monitoramento" },
  { value: "outros", label: "Outros" },
];

function formatCurrency(value: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value ?? 0));
}

function formatOptionalCurrency(value: number | null | undefined, fallback = "Nao identificado") {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return fallback;
  return formatCurrency(value);
}

function formatMeasurement(value: number | null | undefined, unit: string, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "A validar";
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: digits }).format(Number(value))} ${unit}`;
}

function numberOrNull(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function numberOrZero(value: string | number | null | undefined) {
  return numberOrNull(value) ?? 0;
}

function integerOrNull(value: string | number | null | undefined) {
  const parsed = numberOrNull(value);
  return parsed === null ? null : Math.round(parsed);
}

function integerOrZero(value: string | number | null | undefined) {
  return integerOrNull(value) ?? 0;
}

function rangeLabel(min: number | null | undefined, max: number | null | undefined, unit: string, digits = 2) {
  const left = min === null || min === undefined ? "min livre" : formatMeasurement(min, unit, digits);
  const right = max === null || max === undefined ? "max livre" : formatMeasurement(max, unit, digits);
  return `${left} a ${right}`;
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return "N/I";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function latestProposalShareLink(proposal: Proposal): ProposalShareLink | null {
  return [...(proposal.share_links ?? [])].sort((a, b) => b.created_at.localeCompare(a.created_at))[0] ?? null;
}

function proposalPublicUrl(link: ProposalShareLink) {
  return link.public_url ?? `${window.location.origin}/proposta/${link.token}`;
}

function nextPendingProposalFollowup(proposal: Proposal): ProposalFollowUp | null {
  return (
    [...(proposal.followups ?? [])]
      .filter((followup) => followup.status === "pending")
      .sort((a, b) => a.due_at.localeCompare(b.due_at))[0] ?? null
  );
}

function followupEffectiveStatus(followup: ProposalFollowUp) {
  if (followup.status === "pending" && new Date(followup.due_at).getTime() < Date.now()) {
    return "overdue";
  }
  return followup.status;
}

function proposalResponseLabel(responseType: string) {
  const labels: Record<string, string> = {
    interested: "Interesse registrado",
    request_changes: "Solicitou ajuste",
    accepted: "Aceitou proposta",
    rejected: "Recusou proposta",
    talk_to_consultant: "Quer consultor",
  };
  return labels[responseType] ?? responseType;
}

function proposalEventLabel(eventType: string) {
  const labels: Record<string, string> = {
    "proposal.created": "Proposta criada",
    "proposal.updated": "Proposta atualizada",
    "proposal.pdf_generated": "PDF gerado",
    "proposal.share_link_created": "Link seguro criado",
    "proposal.share_link_revoked": "Link revogado",
    "proposal.share_link_viewed": "Link visualizado",
    "proposal.viewed": "Proposta visualizada",
    "proposal.downloaded": "PDF baixado",
    "proposal.sent": "Proposta enviada",
    "proposal.whatsapp_sent": "Enviada por WhatsApp",
    "proposal.email_sent": "Enviada por e-mail",
    "proposal.customer_interested": "Cliente interessado",
    "proposal.accepted": "Proposta aceita",
    "proposal.rejected": "Proposta recusada",
    "proposal.change_requested": "Ajuste solicitado",
    "proposal.followup_created": "Follow-up criado",
    "proposal.followup_completed": "Follow-up concluido",
    "proposal.followup_canceled": "Follow-up cancelado",
  };
  return labels[eventType] ?? eventType;
}

function nullableText(value: string | null | undefined) {
  const trimmed = (value ?? "").trim();
  return trimmed || null;
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
    { label: "ConversÃ£o", value: `${metrics?.taxa_conversao_orcamento ?? 0}%`, icon: <BarChart3 size={18} /> },
  ];
  const aiCards = [
    { label: "Leads quentes", value: aiInsights?.leads_quentes ?? 0, icon: <Sparkles size={18} /> },
    { label: "Chamados crÃ­ticos", value: aiInsights?.chamados_criticos ?? 0, icon: <AlertTriangle size={18} /> },
    { label: "Clientes irritados", value: aiInsights?.clientes_irritados ?? 0, icon: <Headphones size={18} /> },
    {
      label: "Oportunidades de financiamento",
      value: aiInsights?.oportunidades_financiamento ?? 0,
      icon: <BarChart3 size={18} />,
    },
  ];

  const proposalMetrics = metrics?.proposal_metrics;
  const proposalCards = [
    { label: "Propostas criadas", value: proposalMetrics?.created ?? 0, icon: <FileText size={18} /> },
    { label: "Pipeline comercial", value: formatCurrency(proposalMetrics?.total_pipeline_value ?? 0), icon: <BarChart3 size={18} /> },
    { label: "Propostas vistas", value: proposalMetrics?.viewed ?? 0, icon: <ExternalLink size={18} /> },
    { label: "Follow-ups pendentes", value: proposalMetrics?.pending_followups ?? 0, icon: <CalendarClock size={18} /> },
    { label: "Follow-ups vencidos", value: proposalMetrics?.overdue_followups ?? 0, icon: <AlertTriangle size={18} /> },
    { label: "Conversao de propostas", value: `${proposalMetrics?.conversion_rate ?? 0}%`, icon: <CheckCircle2 size={18} /> },
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
          <span>Priorize alta gravidade e riscos elÃ©tricos.</span>
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
      <section className="work-section">
        <div className="section-heading">
          <strong>Funil comercial de propostas</strong>
          <span>Links seguros, respostas digitais e retornos programados.</span>
        </div>
        <div className="metric-grid metric-grid--nested">
          {proposalCards.map((card) => (
            <article className="metric-card" key={card.label}>
              <span>{card.icon}</span>
              <div>
                <strong>{card.value}</strong>
                <small>{card.label}</small>
              </div>
            </article>
          ))}
        </div>
      </section>
      <section className="work-section ai-insights">
        <div className="section-heading">
          <strong>RecomendaÃ§Ãµes da IA para a gestÃ£o</strong>
          <span>Leitura estratÃ©gica dos atendimentos recentes.</span>
        </div>
        <div className="insight-grid">
          <InsightList title="Problemas recorrentes" items={aiInsights?.problemas_tecnicos_recorrentes ?? []} />
          <InsightList title="Principais motivos" items={aiInsights?.principais_motivos ?? []} />
          <InsightList title="Principais cidades" items={aiInsights?.principais_cidades ?? []} />
        </div>
        <div className="recommendation-list">
          {(aiInsights?.recomendacoes?.length
            ? aiInsights.recomendacoes
            : ["Gere mais atendimentos para a IA identificar padrÃµes de gestÃ£o."])
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
      setWhatsappNotice("NÃ£o foi possÃ­vel iniciar a continuidade pelo WhatsApp. Verifique telefone, gravidade e configuraÃ§Ã£o da API.");
    } finally {
      setWhatsappLoadingId(null);
    }
  }

  return (
    <section className="table-panel">
      {whatsappNotice && <div className="notice notice--compact">{whatsappNotice}</div>}
      <TableHeader columns={["Canal", "IntenÃ§Ã£o", "Gravidade", "Status", "Resumo", "AÃ§Ã£o"]} />
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
      <TableHeader columns={["Tipo", "Conta mÃ©dia", "Score", "Financiamento", "Status", "AÃ§Ã£o"]} />
      {leads.map((lead) => (
        <div className="table-group" key={lead.id}>
          <div className="table-row table-row--six">
            <span>{lead.property_type ?? "N/I"}</span>
            <span>{lead.average_bill ? `R$ ${lead.average_bill}` : "N/I"}</span>
            <ScoreBadge score={analyses[lead.id]?.priority_score} type="lead" />
            <span>{lead.financing_interest === null ? "N/I" : lead.financing_interest ? "Sim" : "NÃ£o"}</span>
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

function EnergyBillsView({
  extractions,
  leads,
  preview,
  loadingKey,
  onParseText,
  onUpload,
  onUpdate,
  onConfirm,
  onApplyToLead,
  onGenerateProposal,
  onDiscard,
}: {
  extractions: EnergyBillExtraction[];
  leads: Lead[];
  preview: EnergyBillParsedData | null;
  loadingKey: string | null;
  onParseText: (rawText: string) => Promise<void>;
  onUpload: (file: File, leadId?: string) => Promise<void>;
  onUpdate: (id: string, payload: Partial<EnergyBillExtraction>) => Promise<void>;
  onConfirm: (id: string) => Promise<void>;
  onApplyToLead: (id: string, leadId: string) => Promise<void>;
  onGenerateProposal: (id: string) => Promise<void>;
  onDiscard: (id: string) => Promise<void>;
}) {
  const [rawText, setRawText] = useState("");
  const [uploadLeadId, setUploadLeadId] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [leadTargets, setLeadTargets] = useState<Record<string, string>>({});

  async function submitParse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!rawText.trim()) return;
    await onParseText(rawText);
  }

  async function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) return;
    await onUpload(selectedFile, uploadLeadId || undefined);
    setSelectedFile(null);
  }

  return (
    <section className="energy-bills-layout">
      <div className="energy-bill-tools">
        <form className="energy-bill-card" onSubmit={submitUpload}>
          <div className="section-heading">
            <div>
              <strong>Enviar conta de energia</strong>
              <span>PDF, imagem ou texto para leitura estruturada.</span>
            </div>
          </div>
          <input type="file" accept=".pdf,.txt,image/*" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} />
          <select value={uploadLeadId} onChange={(event) => setUploadLeadId(event.target.value)}>
            <option value="">Vincular lead depois</option>
            {leads.map((lead) => (
              <option value={lead.id} key={lead.id}>
                {lead.property_type ?? "Lead"} - {formatCurrency(lead.average_bill)}
              </option>
            ))}
          </select>
          <button className="primary-button" type="submit" disabled={!selectedFile || loadingKey === "upload"}>
            <FileText size={16} />
            {loadingKey === "upload" ? "Processando" : "Processar conta"}
          </button>
        </form>

        <form className="energy-bill-card" onSubmit={submitParse}>
          <div className="section-heading">
            <div>
              <strong>Testar texto extraido</strong>
              <span>Use para validar parser antes de revisar no painel.</span>
            </div>
          </div>
          <textarea
            value={rawText}
            onChange={(event) => setRawText(event.target.value)}
            placeholder="Cole aqui o texto da conta de energia para simular a leitura."
          />
          <button className="secondary-button" type="submit" disabled={!rawText.trim() || loadingKey === "parse-text"}>
            <Sparkles size={16} />
            Interpretar texto
          </button>
        </form>
      </div>

      {preview && (
        <article className="energy-bill-preview">
          <strong>Previa da leitura</strong>
          <div className="kit-summary-grid">
            <span><small>Distribuidora</small><strong>{preview.distributor ?? "A revisar"}</strong></span>
            <span><small>Cliente</small><strong>{preview.customer_name ?? "A revisar"}</strong></span>
            <span><small>Cidade/UF</small><strong>{[preview.city, preview.state].filter(Boolean).join(" / ") || "A revisar"}</strong></span>
            <span><small>Unidade</small><strong>{preview.customer_unit_number ?? preview.installation_number ?? "A revisar"}</strong></span>
            <span><small>Consumo medio</small><strong>{formatMeasurement(preview.average_consumption_kwh, "kWh/mes", 0)}</strong></span>
            <span><small>Media por</small><strong>{energyBillAverageSourceLabel(preview.parsed_fields)}</strong></span>
            <span><small>Meses detectados</small><strong>{energyBillMonthsDetected(preview.parsed_fields)}</strong></span>
            <span className={!preview.current_bill_amount ? "energy-bill-value--review" : ""}><small>Conta atual</small><strong>{formatOptionalCurrency(preview.current_bill_amount)}</strong></span>
            <span><small>Potencia estimada</small><strong>{formatMeasurement(preview.estimated_system_power_kwp, "kWp", 3)}</strong></span>
            <span><small>Confianca</small><strong>{Math.round((preview.confidence_score ?? 0) * 100)}%</strong></span>
            <span><small>Revisao humana</small><strong>{preview.needs_human_review ? "Sim" : "Nao"}</strong></span>
          </div>
          {energyBillReviewReasons(preview).length > 0 && <EnergyBillReviewAlerts reasons={energyBillReviewReasons(preview)} />}
          {preview.missing_fields.length > 0 && <p>Dados faltantes: {preview.missing_fields.join(", ")}</p>}
          <EnergyBillExtractionDebug parsedFields={preview.parsed_fields} />
          <EnergyBillHistoryChart history={preview.history} />
        </article>
      )}

      <section className="table-panel">
        <TableHeader columns={["Status", "Origem", "Distribuidora", "Consumo", "Conta", "Confianca", "Lead", "Criada em", "Acao"]} />
        {extractions.map((extraction) => {
          const targetLeadId = leadTargets[extraction.id] ?? extraction.lead_id ?? "";
          const ocr = energyBillOcrInfo(extraction);
          const reviewReasons = energyBillReviewReasons(extraction);
          const requiresConfirmedReview = requiresEnergyBillConfirmation(extraction);
          return (
            <div className="table-group" key={extraction.id}>
              <div className="table-row table-row--nine">
                <EnergyBillStatusPill status={extraction.status} />
                <OriginBadge origin={extraction.origin} />
                <span>{extraction.distributor ?? "A revisar"}</span>
                <span>{formatMeasurement(extraction.average_consumption_kwh ?? extraction.current_consumption_kwh, "kWh", 0)}</span>
                <span className={!extraction.average_bill_amount && !extraction.current_bill_amount ? "energy-bill-value--review" : ""}>
                  {formatOptionalCurrency(extraction.average_bill_amount ?? extraction.current_bill_amount)}
                </span>
                <span className={Number(extraction.confidence_score ?? 0) < 0.8 ? "energy-bill-value--review" : ""}>{Math.round(Number(extraction.confidence_score ?? 0) * 100)}%</span>
                <select value={targetLeadId} onChange={(event) => setLeadTargets((current) => ({ ...current, [extraction.id]: event.target.value }))}>
                  <option value="">Selecionar lead</option>
                  {leads.map((lead) => (
                    <option value={lead.id} key={lead.id}>
                      {lead.property_type ?? "Lead"} - {formatCurrency(lead.average_bill)}
                    </option>
                  ))}
                </select>
                <span>{formatDateTime(extraction.created_at)}</span>
                <div className="row-actions">
                  <button className="text-button" onClick={() => onConfirm(extraction.id)} disabled={loadingKey === `confirm:${extraction.id}` || extraction.status === "confirmed"}>
                    <CheckCircle2 size={15} />
                    Confirmar
                  </button>
                  <button
                    className="text-button"
                    onClick={() => onApplyToLead(extraction.id, targetLeadId)}
                    disabled={!targetLeadId || loadingKey === `apply:${extraction.id}` || (requiresConfirmedReview && extraction.status !== "confirmed")}
                    title={requiresConfirmedReview && extraction.status !== "confirmed" ? "Revise e confirme a leitura antes de aplicar ao lead." : undefined}
                  >
                    Aplicar
                  </button>
                  <button className="text-button text-button--proposal" onClick={() => onGenerateProposal(extraction.id)} disabled={loadingKey === `proposal:${extraction.id}`}>
                    <FileText size={15} />
                    Proposta
                  </button>
                  <button className="text-button text-button--danger" onClick={() => onDiscard(extraction.id)} disabled={extraction.status === "discarded"}>
                    Descartar
                  </button>
                </div>
              </div>
              <div className="energy-bill-detail">
                <div className="proposal-grid">
                  <label>
                    Cliente na conta
                    <input defaultValue={extraction.customer_name ?? ""} onBlur={(event) => onUpdate(extraction.id, { customer_name: event.target.value || null })} />
                  </label>
                  <label>
                    Unidade/instalacao
                    <input defaultValue={extraction.installation_number ?? ""} onBlur={(event) => onUpdate(extraction.id, { installation_number: event.target.value || null })} />
                  </label>
                  <label>
                    Unidade/cliente CPFL
                    <input defaultValue={extraction.customer_unit_number ?? ""} onBlur={(event) => onUpdate(extraction.id, { customer_unit_number: event.target.value || null })} />
                  </label>
                  <label>
                    Endereco
                    <input defaultValue={extraction.customer_address ?? ""} onBlur={(event) => onUpdate(extraction.id, { customer_address: event.target.value || null })} />
                  </label>
                  <label>
                    Bairro
                    <input defaultValue={extraction.customer_district ?? ""} onBlur={(event) => onUpdate(extraction.id, { customer_district: event.target.value || null })} />
                  </label>
                  <label>
                    CEP
                    <input defaultValue={extraction.customer_postal_code ?? ""} onBlur={(event) => onUpdate(extraction.id, { customer_postal_code: event.target.value || null })} />
                  </label>
                  <label>
                    Cidade
                    <input defaultValue={extraction.city ?? ""} onBlur={(event) => onUpdate(extraction.id, { city: event.target.value || null })} />
                  </label>
                  <label>
                    UF
                    <input maxLength={2} defaultValue={extraction.state ?? ""} onBlur={(event) => onUpdate(extraction.id, { state: event.target.value || null })} />
                  </label>
                  <label>
                    Consumo atual kWh
                    <input type="number" defaultValue={extraction.current_consumption_kwh ?? ""} onBlur={(event) => onUpdate(extraction.id, { current_consumption_kwh: numberOrNull(event.target.value) })} />
                  </label>
                  <label>
                    Valor atual
                    <input type="number" defaultValue={extraction.current_bill_amount ?? ""} onBlur={(event) => onUpdate(extraction.id, { current_bill_amount: numberOrNull(event.target.value) })} />
                  </label>
                  <label>
                    Consumo medio kWh
                    <input type="number" defaultValue={extraction.average_consumption_kwh ?? ""} onBlur={(event) => onUpdate(extraction.id, { average_consumption_kwh: numberOrNull(event.target.value) })} />
                  </label>
                  <label>
                    Conta media
                    <input type="number" defaultValue={extraction.average_bill_amount ?? ""} onBlur={(event) => onUpdate(extraction.id, { average_bill_amount: numberOrNull(event.target.value) })} />
                  </label>
                  <label>
                    Bandeira tarifaria
                    <input defaultValue={extraction.tariff_flag ?? ""} onBlur={(event) => onUpdate(extraction.id, { tariff_flag: event.target.value || null })} />
                  </label>
                </div>
                <div className="kit-summary-grid">
                  <span><small>Potencia estimada</small><strong>{formatMeasurement(extraction.estimated_system_power_kwp, "kWp", 3)}</strong></span>
                  <span><small>Geracao estimada</small><strong>{formatMeasurement(extraction.estimated_monthly_generation_kwh, "kWh/mes", 0)}</strong></span>
                  <span><small>Economia estimada</small><strong>{formatOptionalCurrency(extraction.estimated_monthly_savings, "A validar")}</strong></span>
                  <span><small>Documento</small><strong>{extraction.customer_document_masked ?? "Nao exibido"}</strong></span>
                  <span><small>Bandeira</small><strong>{extraction.tariff_flag ?? energyBillTariffFlag(extraction.parsed_fields) ?? "Nao identificada"}</strong></span>
                  <span><small>Endereco</small><strong>{extraction.customer_address ?? "Nao identificado"}</strong></span>
                  <span><small>Bairro</small><strong>{extraction.customer_district ?? "Nao identificado"}</strong></span>
                  <span><small>CEP</small><strong>{extraction.customer_postal_code ?? "Nao identificado"}</strong></span>
                  <span><small>Media por</small><strong>{energyBillAverageSourceLabel(extraction.parsed_fields)}</strong></span>
                  <span><small>Meses detectados</small><strong>{energyBillMonthsDetected(extraction.parsed_fields)}</strong></span>
                  <span><small>Origem</small><strong>{originLabel(extraction.origin)}</strong></span>
                  <span><small>Conversa</small><strong>{extraction.conversation_id ?? "Sem vinculo"}</strong></span>
                  <span><small>Metodo</small><strong>{ocr.method}</strong></span>
                  <span><small>OCR</small><strong>{ocr.used}</strong></span>
                  <span><small>Provider OCR</small><strong>{ocr.provider}</strong></span>
                  <span><small>Paginas OCR</small><strong>{ocr.pages}</strong></span>
                </div>
                {ocr.notice && <p className={`proposal-alert proposal-alert--${ocr.noticeTone}`}>{ocr.notice}</p>}
                {reviewReasons.length > 0 && <EnergyBillReviewAlerts reasons={reviewReasons} />}
                {requiresConfirmedReview && extraction.status !== "confirmed" && (
                  <p className="proposal-alert proposal-alert--warning">Existem campos importantes pendentes. Revise e confirme a leitura antes de aplicar ao lead.</p>
                )}
                {extraction.missing_fields.length > 0 && <p className="proposal-alert proposal-alert--warning">Revisar dados faltantes: {extraction.missing_fields.join(", ")}</p>}
                {extraction.error_message && <p className="proposal-alert proposal-alert--warning">{extraction.error_message}</p>}
                <EnergyBillExtractionDebug parsedFields={extraction.parsed_fields} />
                <EnergyBillHistoryChart history={extraction.history} />
              </div>
            </div>
          );
        })}
        {!extractions.length && <p className="empty-state">Nenhuma conta de energia processada ainda.</p>}
      </section>
    </section>
  );
}

function EnergyBillReviewAlerts({ reasons }: { reasons: string[] }) {
  if (!reasons.length) return null;
  return (
    <div className="energy-bill-review-alerts">
      {reasons.map((reason) => (
        <p className="proposal-alert proposal-alert--warning" key={reason}>{reason}</p>
      ))}
    </div>
  );
}

function EnergyBillExtractionDebug({ parsedFields }: { parsedFields: Record<string, unknown> }) {
  const debugPayload = energyBillDebugPayload(parsedFields);
  if (!Object.keys(debugPayload).length) return null;
  return (
    <details className="energy-bill-debug">
      <summary>Detalhes da extracao</summary>
      <pre>{JSON.stringify(debugPayload, null, 2)}</pre>
    </details>
  );
}

function energyBillReviewReasons(extraction: EnergyBillParsedData) {
  const fields = extraction.parsed_fields ?? {};
  const configuredReasons = Array.isArray(fields.review_reasons) ? fields.review_reasons.filter((item): item is string => typeof item === "string") : [];
  const reasons = new Set(configuredReasons);
  if (!extraction.current_bill_amount && !extraction.average_bill_amount) reasons.add("Valor da conta nao encontrado.");
  if (!extraction.city || !extraction.state) reasons.add("Cidade/endereco precisa de revisao.");
  if (!extraction.installation_number && !extraction.customer_unit_number) reasons.add("Unidade consumidora nao identificada com seguranca.");
  if (Number(extraction.confidence_score ?? 0) < 0.8) reasons.add("Confianca abaixo de 80%.");
  return Array.from(reasons);
}

function requiresEnergyBillConfirmation(extraction: EnergyBillExtraction) {
  return extraction.needs_human_review || energyBillReviewReasons(extraction).length > 0 || Number(extraction.confidence_score ?? 0) < 0.8;
}

function energyBillTariffFlag(parsedFields: Record<string, unknown>) {
  return typeof parsedFields?.tariff_flag === "string" ? parsedFields.tariff_flag : null;
}

function energyBillDebugPayload(parsedFields: Record<string, unknown>) {
  const keys = [
    "parser",
    "cpfl_rules_applied",
    "tariff_flag",
    "customer_unit_number",
    "customer_block_detected",
    "customer_block_lines",
    "history_detection",
    "months_detected",
    "average_source",
    "confidence_inputs",
    "parser_confidence_inputs",
    "discarded_fields",
    "anchors",
    "source_snippets",
    "review_warnings",
    "review_reasons",
  ];
  return keys.reduce<Record<string, unknown>>((payload, key) => {
    const value = parsedFields?.[key];
    if (value !== undefined && value !== null && (!(Array.isArray(value)) || value.length > 0)) {
      payload[key] = value;
    }
    return payload;
  }, {});
}

function energyBillMonthsDetected(parsedFields: Record<string, unknown>) {
  const value = parsedFields?.months_detected;
  const fromHistory = parsedFields?.history_detection;
  const historyMonths = typeof fromHistory === "object" && fromHistory !== null && "months_detected" in fromHistory ? Number((fromHistory as Record<string, unknown>).months_detected) : NaN;
  const months = typeof value === "number" ? value : Number(value ?? historyMonths);
  return Number.isFinite(months) ? String(months) : "0";
}

function energyBillAverageSourceLabel(parsedFields: Record<string, unknown>) {
  const value = String(parsedFields?.average_source ?? (typeof parsedFields?.history_detection === "object" && parsedFields.history_detection !== null ? (parsedFields.history_detection as Record<string, unknown>).source : "") ?? "");
  const labels: Record<string, string> = {
    history_12_months: "Historico 12 meses",
    history_partial: "Historico parcial",
    historico_cpfl: "Historico CPFL",
    generic_history: "Historico",
    current_consumption_only: "Consumo atual",
    not_found: "Nao encontrado",
  };
  return labels[value] ?? (value || "Nao informado");
}

function EnergyBillStatusPill({ status }: { status: string }) {
  return <span className={`status-badge status-badge--${status}`}>{status}</span>;
}

function OriginBadge({ origin }: { origin: string }) {
  return <span className={`origin-badge origin-badge--${origin}`}>{originLabel(origin)}</span>;
}

function originLabel(origin: string) {
  const labels: Record<string, string> = {
    chatbot: "Chatbot",
    whatsapp: "WhatsApp",
    panel: "Painel",
    manual_text: "Texto manual",
    api: "API",
  };
  return labels[origin] ?? origin;
}

function energyBillOcrInfo(extraction: EnergyBillExtraction) {
  const fields = extraction.parsed_fields ?? {};
  const method = String(fields.extraction_method ?? "Nao informado");
  const provider = String(fields.ocr_provider ?? "disabled");
  const ocrUsed = fields.ocr_used === true;
  const ocrError = typeof fields.ocr_error === "string" ? fields.ocr_error : "";
  const pageCount = typeof fields.ocr_page_count === "number" ? fields.ocr_page_count : Number(fields.ocr_page_count ?? 0);
  let notice = "";
  let noticeTone: "warning" | "success" = "warning";
  if (ocrUsed && !ocrError) {
    notice = "Texto extraido por OCR local. Revise os dados antes de aplicar ao lead.";
    noticeTone = "success";
  } else if (ocrError) {
    notice =
      ocrError.includes("OCR desabilitado") || provider === "disabled"
        ? "O arquivo parece ser imagem ou PDF escaneado. Ative OCR local para leitura automatica ou revise manualmente."
        : `OCR nao conseguiu concluir a leitura: ${ocrError}`;
  }
  return {
    method: methodLabel(method),
    used: ocrUsed ? "Sim" : "Nao",
    provider: providerLabel(provider),
    pages: pageCount > 0 ? String(pageCount) : "0",
    notice,
    noticeTone,
  };
}

function methodLabel(method: string) {
  const labels: Record<string, string> = {
    pdf_text: "PDF textual",
    text_file: "Texto",
    ocr: "OCR",
    pdf_text_insufficient: "PDF escaneado",
    image_ocr_failed: "Imagem sem leitura",
    unsupported: "Nao suportado",
  };
  return labels[method] ?? method;
}

function providerLabel(provider: string) {
  const labels: Record<string, string> = {
    disabled: "Desabilitado",
    local_tesseract: "Tesseract local",
    openai_vision: "OpenAI Vision",
  };
  return labels[provider] ?? provider;
}

function EnergyBillHistoryChart({ history }: { history: EnergyBillHistory[] }) {
  if (!history?.length) return <p className="empty-state">Historico de consumo ainda nao identificado.</p>;
  const max = Math.max(...history.map((item) => Number(item.consumption_kwh || 0)), 1);
  return (
    <div className="energy-bill-history">
      {history.slice(0, 12).map((item) => (
        <div className="energy-bill-history__row" key={`${item.period}-${item.consumption_kwh}`}>
          <span>{item.period}</span>
          <div>
            <i style={{ width: `${Math.max(8, Math.round((Number(item.consumption_kwh || 0) / max) * 100))}%` }} />
          </div>
          <strong>{formatMeasurement(item.consumption_kwh, "kWh", 0)}</strong>
        </div>
      ))}
    </div>
  );
}

function ProposalsView({
  proposals,
  followups,
  priceItems,
  kits,
  companySettings,
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
  onCreateShareLink,
  onRevokeShareLink,
  onCreateFollowup,
  onCompleteFollowup,
  onCancelFollowup,
  onCreatePriceItem,
  onUpdatePriceItem,
  onTogglePriceItem,
  onDeletePriceItem,
  onCreateKit,
  onUpdateKit,
  onToggleKit,
  onDeleteKit,
  onAddKitItem,
  onUpdateKitItem,
  onDeleteKitItem,
  onSimulateKit,
  onUpdateCompanySettings,
}: {
  proposals: Proposal[];
  followups: ProposalFollowUp[];
  priceItems: ProposalPriceItem[];
  kits: ProposalKit[];
  companySettings: CompanySettings | null;
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
  onCreateShareLink: (id: string) => Promise<void>;
  onRevokeShareLink: (id: string) => Promise<void>;
  onCreateFollowup: (id: string, channel: string, dueAt: string, note: string) => Promise<void>;
  onCompleteFollowup: (id: string) => Promise<void>;
  onCancelFollowup: (id: string) => Promise<void>;
  onCreatePriceItem: (payload: Partial<ProposalPriceItem>) => Promise<void>;
  onUpdatePriceItem: (id: string, payload: Partial<ProposalPriceItem>) => Promise<void>;
  onTogglePriceItem: (id: string, active: boolean) => Promise<void>;
  onDeletePriceItem: (id: string) => Promise<void>;
  onCreateKit: (payload: Partial<ProposalKit>) => Promise<void>;
  onUpdateKit: (id: string, payload: Partial<ProposalKit>) => Promise<void>;
  onToggleKit: (id: string, active: boolean) => Promise<void>;
  onDeleteKit: (id: string) => Promise<void>;
  onAddKitItem: (kitId: string, payload: Partial<ProposalKitItem>) => Promise<void>;
  onUpdateKitItem: (kitId: string, itemId: string, payload: Partial<ProposalKitItem>) => Promise<void>;
  onDeleteKitItem: (kitId: string, itemId: string) => Promise<void>;
  onSimulateKit: (payload: { average_bill?: number | null; estimated_monthly_generation_kwh?: number | null; estimated_power_kwp?: number | null }) => Promise<ProposalKitSimulation | null>;
  onUpdateCompanySettings: (payload: Partial<CompanySettings>) => Promise<void>;
}) {
  const [filters, setFilters] = useState({ status: "", city: "", customer: "" });
  const [activeTab, setActiveTab] = useState<"proposals" | "kits" | "prices" | "followups" | "settings">("proposals");
  const [sendDraft, setSendDraft] = useState<ProposalSendRequest>({ channel: "manual", mark_as_sent: false });
  const [followupDraft, setFollowupDraft] = useState({ channel: "manual", due_at: "", note: "Retorno comercial da proposta" });
  const filtered = proposals.filter((proposal) => {
    const byStatus = !filters.status || proposal.status === filters.status;
    const byCity = !filters.city || (proposal.city ?? "").toLowerCase().includes(filters.city.toLowerCase());
    const byCustomer = !filters.customer || proposal.customer_name.toLowerCase().includes(filters.customer.toLowerCase());
    return byStatus && byCity && byCustomer;
  });
  const hasZeroValues = selectedProposal?.items.length ? selectedProposal.items.every((item) => Number(item.unit_price) === 0) : false;
  const selectedLatestLink = selectedProposal ? latestProposalShareLink(selectedProposal) : null;
  const selectedPublicUrl = selectedLatestLink ? proposalPublicUrl(selectedLatestLink) : "";
  const selectedPendingFollowup = selectedProposal ? nextPendingProposalFollowup(selectedProposal) : null;

  return (
    <section className="proposals-layout">
      <div className="proposal-tabs">
        <button className={activeTab === "proposals" ? "proposal-tab proposal-tab--active" : "proposal-tab"} onClick={() => setActiveTab("proposals")}>
          Propostas
        </button>
        <button className={activeTab === "kits" ? "proposal-tab proposal-tab--active" : "proposal-tab"} onClick={() => setActiveTab("kits")}>
          Kits fotovoltaicos
        </button>
        <button className={activeTab === "prices" ? "proposal-tab proposal-tab--active" : "proposal-tab"} onClick={() => setActiveTab("prices")}>
          Tabela de precos
        </button>
        <button className={activeTab === "followups" ? "proposal-tab proposal-tab--active" : "proposal-tab"} onClick={() => setActiveTab("followups")}>
          Follow-ups
        </button>
        <button className={activeTab === "settings" ? "proposal-tab proposal-tab--active" : "proposal-tab"} onClick={() => setActiveTab("settings")}>
          Configuracoes comerciais
        </button>
      </div>

      {activeTab === "kits" && (
        <ProposalKitsPanel
          kits={kits}
          onCreate={onCreateKit}
          onUpdate={onUpdateKit}
          onToggle={onToggleKit}
          onDelete={onDeleteKit}
          onAddItem={onAddKitItem}
          onUpdateItem={onUpdateKitItem}
          onDeleteItem={onDeleteKitItem}
          onSimulate={onSimulateKit}
        />
      )}

      {activeTab === "prices" && (
        <PriceTablePanel
          priceItems={priceItems}
          onCreate={onCreatePriceItem}
          onUpdate={onUpdatePriceItem}
          onToggle={onTogglePriceItem}
          onDelete={onDeletePriceItem}
        />
      )}

      {activeTab === "followups" && (
        <FollowupsPanel
          followups={followups}
          onComplete={onCompleteFollowup}
          onCancel={onCancelFollowup}
        />
      )}

      {activeTab === "settings" && companySettings && (
        <CompanySettingsPanel settings={companySettings} onUpdate={onUpdateCompanySettings} />
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
        <TableHeader columns={["Numero", "Cliente", "Cidade", "Tipo", "Total", "Status", "Rastreamento", "Acao"]} />
        {filtered.map((proposal) => (
          <div className="table-row table-row--eight" key={proposal.id}>
            <span>{proposal.proposal_number}</span>
            <span className="truncate">{proposal.customer_name}</span>
            <span>{proposal.city ?? "N/I"}</span>
            <span>{proposal.property_type ?? "N/I"}</span>
            <span>{formatCurrency(proposal.total_amount)}</span>
            <ProposalStatusPill status={proposal.status} />
            <ProposalTrackingSummary proposal={proposal} />
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
              <span>Valores e condiÃ§Ãµes devem ser revisados pela equipe da Solar SoluÃ§Ãµes antes do envio ao cliente.</span>
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
          {selectedProposal.recommended_kit_name && <KitRecommendationCard proposal={selectedProposal} />}

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
              Tipo de imÃ³vel
              <input defaultValue={selectedProposal.property_type ?? ""} onBlur={(event) => onUpdate(selectedProposal.id, { property_type: event.target.value })} />
            </label>
            <label>
              Conta mÃ©dia
              <input type="number" defaultValue={selectedProposal.average_bill ?? ""} onBlur={(event) => onUpdate(selectedProposal.id, { average_bill: Number(event.target.value) || null })} />
            </label>
            <label>
              PotÃªncia kWp
              <input type="number" step="0.001" defaultValue={selectedProposal.estimated_system_power_kwp ?? ""} onBlur={(event) => onUpdate(selectedProposal.id, { estimated_system_power_kwp: Number(event.target.value) || null })} />
            </label>
            <label>
              GeraÃ§Ã£o mensal kWh
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
            CondiÃ§Ãµes de pagamento
            <textarea defaultValue={selectedProposal.payment_conditions ?? ""} onBlur={(event) => onUpdate(selectedProposal.id, { payment_conditions: event.target.value })} />
          </label>
          <label className="proposal-wide-field">
            ObservaÃ§Ãµes
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

          <div className="proposal-collaboration-grid">
            <section className="proposal-side-panel">
              <div className="proposal-section-title">
                <strong>Link seguro</strong>
                <span>{selectedLatestLink ? `${selectedLatestLink.views_count} visualizacoes` : "Ainda nao gerado"}</span>
              </div>
              {selectedLatestLink ? (
                <>
                  <a className="proposal-secure-link" href={selectedPublicUrl} target="_blank" rel="noreferrer">
                    <Link2 size={15} />
                    {selectedPublicUrl}
                  </a>
                  <div className="proposal-link-meta">
                    <span>Expira em {formatDateTime(selectedLatestLink.expires_at)}</span>
                    {selectedLatestLink.revoked_at && <span>Revogado em {formatDateTime(selectedLatestLink.revoked_at)}</span>}
                    {selectedLatestLink.last_viewed_at && <span>Ultima visualizacao em {formatDateTime(selectedLatestLink.last_viewed_at)}</span>}
                  </div>
                  <div className="row-actions">
                    <button className="text-button" onClick={() => navigator.clipboard?.writeText(selectedPublicUrl)}>
                      <Copy size={15} />
                      Copiar link
                    </button>
                    {!selectedLatestLink.revoked_at && (
                      <button className="text-button text-button--danger" onClick={() => onRevokeShareLink(selectedLatestLink.id)}>
                        <XCircle size={15} />
                        Revogar
                      </button>
                    )}
                  </div>
                </>
              ) : (
                <p>Gere um link publico com token seguro para o cliente visualizar a proposta e responder digitalmente.</p>
              )}
              <button className="secondary-button" onClick={() => onCreateShareLink(selectedProposal.id)} disabled={loadingKey === `share:${selectedProposal.id}`}>
                <Link2 size={16} />
                {selectedLatestLink ? "Gerar novo link" : "Gerar link seguro"}
              </button>
            </section>

            <section className="proposal-side-panel">
              <div className="proposal-section-title">
                <strong>Follow-up comercial</strong>
                <span>{selectedPendingFollowup ? `Proximo: ${formatDateTime(selectedPendingFollowup.due_at)}` : "Sem pendencia"}</span>
              </div>
              <div className="proposal-followup-form">
                <select value={followupDraft.channel} onChange={(event) => setFollowupDraft((current) => ({ ...current, channel: event.target.value }))}>
                  <option value="manual">Manual</option>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="email">E-mail</option>
                  <option value="phone">Telefone</option>
                </select>
                <input type="datetime-local" value={followupDraft.due_at} onChange={(event) => setFollowupDraft((current) => ({ ...current, due_at: event.target.value }))} />
                <input value={followupDraft.note} onChange={(event) => setFollowupDraft((current) => ({ ...current, note: event.target.value }))} />
                <button
                  className="text-button"
                  onClick={() => {
                    if (!followupDraft.due_at) return;
                    onCreateFollowup(selectedProposal.id, followupDraft.channel, followupDraft.due_at, followupDraft.note);
                    setFollowupDraft({ channel: "manual", due_at: "", note: "Retorno comercial da proposta" });
                  }}
                >
                  <Plus size={15} />
                  Agendar
                </button>
              </div>
              <div className="proposal-mini-list">
                {(selectedProposal.followups ?? []).slice(0, 4).map((followup) => (
                  <div key={followup.id}>
                    <span>{followup.channel} - {formatDateTime(followup.due_at)}</span>
                    <strong>{followup.status}</strong>
                    {followup.status === "pending" && (
                      <button className="text-button" onClick={() => onCompleteFollowup(followup.id)}>
                        Concluir
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </section>
          </div>

          <div className="proposal-collaboration-grid">
            <ProposalResponsesPanel proposal={selectedProposal} />
            <ProposalTimeline proposal={selectedProposal} />
          </div>

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

function KitRecommendationCard({ proposal }: { proposal: Proposal }) {
  const kit = proposal.recommended_kit;
  return (
    <section className="kit-recommendation-card">
      <div className="proposal-section-title">
        <strong>Kit recomendado automaticamente</strong>
        <span>{proposal.recommended_kit_name}</span>
      </div>
      <div className="kit-summary-grid">
        <span>
          <small>Potencia sugerida</small>
          <strong>{formatMeasurement(kit?.suggested_power_kwp ?? proposal.estimated_system_power_kwp, "kWp", 3)}</strong>
        </span>
        <span>
          <small>Modulos</small>
          <strong>{kit?.module_count ? `${kit.module_count} x ${kit.module_power_wp ?? "?"} Wp` : "A validar"}</strong>
        </span>
        <span>
          <small>Inversor</small>
          <strong>{formatMeasurement(kit?.inverter_power_kw, "kW", 3)}</strong>
        </span>
        <span>
          <small>Geracao estimada</small>
          <strong>{formatMeasurement(kit?.estimated_monthly_generation_kwh ?? proposal.estimated_monthly_generation_kwh, "kWh/mes", 0)}</strong>
        </span>
      </div>
      <p>{proposal.kit_selection_reason ?? "Kit sugerido pelo sistema com base nos dados informados."}</p>
      <div className="proposal-alert proposal-alert--warning">
        Este kit foi sugerido automaticamente com base na conta media informada pelo cliente. Revise dimensionamento, telhado,
        concessionaria, padrao de entrada, sombreamento, estrutura e condicoes comerciais antes de enviar.
      </div>
    </section>
  );
}

const emptyKitDraft = {
  name: "",
  description: "",
  min_monthly_consumption_kwh: "",
  max_monthly_consumption_kwh: "",
  min_power_kwp: "",
  max_power_kwp: "",
  suggested_power_kwp: "",
  estimated_monthly_generation_kwh: "",
  module_count: "",
  module_power_wp: "",
  inverter_power_kw: "",
  base_price: "0",
  sort_order: "0",
  notes: "",
  active: true,
};

const emptyKitItemDraft = {
  category: "kit_fotovoltaico",
  description: "",
  quantity: "1",
  unit: "un",
  unit_price: "0",
  sort_order: "0",
};

function ProposalKitsPanel({
  kits,
  onCreate,
  onUpdate,
  onToggle,
  onDelete,
  onAddItem,
  onUpdateItem,
  onDeleteItem,
  onSimulate,
}: {
  kits: ProposalKit[];
  onCreate: (payload: Partial<ProposalKit>) => Promise<void>;
  onUpdate: (id: string, payload: Partial<ProposalKit>) => Promise<void>;
  onToggle: (id: string, active: boolean) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onAddItem: (kitId: string, payload: Partial<ProposalKitItem>) => Promise<void>;
  onUpdateItem: (kitId: string, itemId: string, payload: Partial<ProposalKitItem>) => Promise<void>;
  onDeleteItem: (kitId: string, itemId: string) => Promise<void>;
  onSimulate: (payload: { average_bill?: number | null; estimated_monthly_generation_kwh?: number | null; estimated_power_kwp?: number | null }) => Promise<ProposalKitSimulation | null>;
}) {
  const [draft, setDraft] = useState(emptyKitDraft);
  const [expandedKitId, setExpandedKitId] = useState<string | null>(kits[0]?.id ?? null);
  const [itemDrafts, setItemDrafts] = useState<Record<string, typeof emptyKitItemDraft>>({});
  const [simulationBill, setSimulationBill] = useState("350");
  const [simulation, setSimulation] = useState<ProposalKitSimulation | null>(null);

  async function submitKit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.name.trim() || !draft.suggested_power_kwp.trim()) return;
    await onCreate({
      name: draft.name.trim(),
      description: draft.description || null,
      min_monthly_consumption_kwh: numberOrNull(draft.min_monthly_consumption_kwh),
      max_monthly_consumption_kwh: numberOrNull(draft.max_monthly_consumption_kwh),
      min_power_kwp: numberOrNull(draft.min_power_kwp),
      max_power_kwp: numberOrNull(draft.max_power_kwp),
      suggested_power_kwp: numberOrZero(draft.suggested_power_kwp),
      estimated_monthly_generation_kwh: numberOrNull(draft.estimated_monthly_generation_kwh),
      module_count: integerOrNull(draft.module_count),
      module_power_wp: integerOrNull(draft.module_power_wp),
      inverter_power_kw: numberOrNull(draft.inverter_power_kw),
      base_price: numberOrZero(draft.base_price),
      active: draft.active,
      sort_order: integerOrZero(draft.sort_order),
      notes: draft.notes || null,
    });
    setDraft(emptyKitDraft);
  }

  async function simulate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const result = await onSimulate({ average_bill: numberOrNull(simulationBill) });
    setSimulation(result);
  }

  async function addItem(kitId: string) {
    const itemDraft = itemDrafts[kitId] ?? emptyKitItemDraft;
    if (!itemDraft.description.trim()) return;
    await onAddItem(kitId, {
      category: itemDraft.category,
      description: itemDraft.description,
      quantity: numberOrZero(itemDraft.quantity),
      unit: itemDraft.unit || "un",
      unit_price: numberOrZero(itemDraft.unit_price),
      sort_order: integerOrZero(itemDraft.sort_order),
    });
    setItemDrafts((current) => ({ ...current, [kitId]: emptyKitItemDraft }));
  }

  return (
    <div className="kit-panel">
      <form className="kit-form" onSubmit={submitKit}>
        <strong>Novo kit fotovoltaico</strong>
        <input placeholder="Nome do kit" value={draft.name} onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))} />
        <input placeholder="Descricao" value={draft.description} onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))} />
        <input placeholder="Consumo minimo kWh/mes" value={draft.min_monthly_consumption_kwh} onChange={(event) => setDraft((current) => ({ ...current, min_monthly_consumption_kwh: event.target.value }))} />
        <input placeholder="Consumo maximo kWh/mes" value={draft.max_monthly_consumption_kwh} onChange={(event) => setDraft((current) => ({ ...current, max_monthly_consumption_kwh: event.target.value }))} />
        <input placeholder="Potencia minima kWp" value={draft.min_power_kwp} onChange={(event) => setDraft((current) => ({ ...current, min_power_kwp: event.target.value }))} />
        <input placeholder="Potencia maxima kWp" value={draft.max_power_kwp} onChange={(event) => setDraft((current) => ({ ...current, max_power_kwp: event.target.value }))} />
        <input placeholder="Potencia sugerida kWp" value={draft.suggested_power_kwp} onChange={(event) => setDraft((current) => ({ ...current, suggested_power_kwp: event.target.value }))} />
        <input placeholder="Geracao mensal estimada" value={draft.estimated_monthly_generation_kwh} onChange={(event) => setDraft((current) => ({ ...current, estimated_monthly_generation_kwh: event.target.value }))} />
        <input placeholder="Quantidade de modulos" value={draft.module_count} onChange={(event) => setDraft((current) => ({ ...current, module_count: event.target.value }))} />
        <input placeholder="Potencia modulo Wp" value={draft.module_power_wp} onChange={(event) => setDraft((current) => ({ ...current, module_power_wp: event.target.value }))} />
        <input placeholder="Inversor kW" value={draft.inverter_power_kw} onChange={(event) => setDraft((current) => ({ ...current, inverter_power_kw: event.target.value }))} />
        <input placeholder="Preco base" value={draft.base_price} onChange={(event) => setDraft((current) => ({ ...current, base_price: event.target.value }))} />
        <input placeholder="Ordem" value={draft.sort_order} onChange={(event) => setDraft((current) => ({ ...current, sort_order: event.target.value }))} />
        <input placeholder="Observacoes" value={draft.notes} onChange={(event) => setDraft((current) => ({ ...current, notes: event.target.value }))} />
        <label className="proposal-checkbox">
          <input type="checkbox" checked={draft.active} onChange={(event) => setDraft((current) => ({ ...current, active: event.target.checked }))} />
          Ativo
        </label>
        <button className="primary-button" type="submit">
          <Plus size={16} />
          Criar kit
        </button>
      </form>

      <section className="kit-simulator">
        <form onSubmit={simulate}>
          <strong>Simulador de kit recomendado</strong>
          <input value={simulationBill} onChange={(event) => setSimulationBill(event.target.value)} placeholder="Conta media mensal em R$" />
          <button className="secondary-button" type="submit">
            <Sparkles size={16} />
            Simular kit recomendado
          </button>
        </form>
        {simulation && (
          <div className="kit-simulation-result">
            <span>Geracao estimada: <strong>{formatMeasurement(simulation.estimated_monthly_generation_kwh, "kWh/mes", 0)}</strong></span>
            <span>Potencia estimada: <strong>{formatMeasurement(simulation.estimated_power_kwp, "kWp", 3)}</strong></span>
            <span>Kit recomendado: <strong>{simulation.selected_kit?.name ?? "Nenhum kit ativo encontrado"}</strong></span>
            <span>Motivo: <strong>{simulation.selection_reason ?? "Sem selecao"}</strong></span>
            {simulation.selected_kit && <span>Preco base: <strong>{formatCurrency(simulation.selected_kit.base_price)}</strong></span>}
            <small>Simulacao sujeita a revisao tecnica e comercial.</small>
          </div>
        )}
      </section>

      <div className="kit-list">
        {kits.map((kit) => {
          const itemDraft = itemDrafts[kit.id] ?? emptyKitItemDraft;
          return (
            <article className="kit-card" key={kit.id}>
              <div className="kit-card__header">
                <button className="text-button" type="button" onClick={() => setExpandedKitId(expandedKitId === kit.id ? null : kit.id)}>
                  {expandedKitId === kit.id ? "Ocultar" : "Detalhar"}
                </button>
                <input defaultValue={kit.name} onBlur={(event) => onUpdate(kit.id, { name: event.target.value })} />
                <span className={kit.active ? "status-badge status-badge--open" : "status-badge"}>{kit.active ? "Ativo" : "Inativo"}</span>
                <button className="text-button" type="button" onClick={() => onToggle(kit.id, !kit.active)}>
                  {kit.active ? "Inativar" : "Ativar"}
                </button>
                <button className="icon-button" type="button" onClick={() => onDelete(kit.id)} aria-label="Excluir kit">
                  <Trash2 size={15} />
                </button>
              </div>
              <div className="kit-summary-grid">
                <span><small>Consumo</small><strong>{rangeLabel(kit.min_monthly_consumption_kwh, kit.max_monthly_consumption_kwh, "kWh/mes", 0)}</strong></span>
                <span><small>Potencia</small><strong>{rangeLabel(kit.min_power_kwp, kit.max_power_kwp, "kWp", 3)}</strong></span>
                <span><small>Sugerida</small><strong>{formatMeasurement(kit.suggested_power_kwp, "kWp", 3)}</strong></span>
                <span><small>Modulos</small><strong>{kit.module_count ? `${kit.module_count} x ${kit.module_power_wp ?? "?"} Wp` : "A validar"}</strong></span>
                <span><small>Inversor</small><strong>{formatMeasurement(kit.inverter_power_kw, "kW", 3)}</strong></span>
                <span><small>Preco base</small><strong>{formatCurrency(kit.base_price)}</strong></span>
              </div>
              {expandedKitId === kit.id && (
                <div className="kit-edit-area">
                  <div className="kit-edit-grid">
                    <input placeholder="Descricao" defaultValue={kit.description ?? ""} onBlur={(event) => onUpdate(kit.id, { description: event.target.value || null })} />
                    <input placeholder="Consumo minimo" defaultValue={kit.min_monthly_consumption_kwh ?? ""} onBlur={(event) => onUpdate(kit.id, { min_monthly_consumption_kwh: numberOrNull(event.target.value) })} />
                    <input placeholder="Consumo maximo" defaultValue={kit.max_monthly_consumption_kwh ?? ""} onBlur={(event) => onUpdate(kit.id, { max_monthly_consumption_kwh: numberOrNull(event.target.value) })} />
                    <input placeholder="Potencia minima" defaultValue={kit.min_power_kwp ?? ""} onBlur={(event) => onUpdate(kit.id, { min_power_kwp: numberOrNull(event.target.value) })} />
                    <input placeholder="Potencia maxima" defaultValue={kit.max_power_kwp ?? ""} onBlur={(event) => onUpdate(kit.id, { max_power_kwp: numberOrNull(event.target.value) })} />
                    <input placeholder="Potencia sugerida" defaultValue={kit.suggested_power_kwp} onBlur={(event) => onUpdate(kit.id, { suggested_power_kwp: numberOrZero(event.target.value) })} />
                    <input placeholder="Geracao estimada" defaultValue={kit.estimated_monthly_generation_kwh ?? ""} onBlur={(event) => onUpdate(kit.id, { estimated_monthly_generation_kwh: numberOrNull(event.target.value) })} />
                    <input placeholder="Modulos" defaultValue={kit.module_count ?? ""} onBlur={(event) => onUpdate(kit.id, { module_count: integerOrNull(event.target.value) })} />
                    <input placeholder="Modulo Wp" defaultValue={kit.module_power_wp ?? ""} onBlur={(event) => onUpdate(kit.id, { module_power_wp: integerOrNull(event.target.value) })} />
                    <input placeholder="Inversor kW" defaultValue={kit.inverter_power_kw ?? ""} onBlur={(event) => onUpdate(kit.id, { inverter_power_kw: numberOrNull(event.target.value) })} />
                    <input placeholder="Preco base" defaultValue={kit.base_price} onBlur={(event) => onUpdate(kit.id, { base_price: numberOrZero(event.target.value) })} />
                    <input placeholder="Ordem" defaultValue={kit.sort_order} onBlur={(event) => onUpdate(kit.id, { sort_order: integerOrZero(event.target.value) })} />
                    <input placeholder="Observacoes" defaultValue={kit.notes ?? ""} onBlur={(event) => onUpdate(kit.id, { notes: event.target.value || null })} />
                  </div>
                  <div className="kit-items">
                    <strong>Itens do kit</strong>
                    {kit.items.map((item) => (
                      <div className="kit-item-row" key={item.id}>
                        <select defaultValue={item.category} onBlur={(event) => onUpdateItem(kit.id, item.id, { category: event.target.value })}>
                          {PROPOSAL_ITEM_CATEGORIES.map((category) => (
                            <option key={category.value} value={category.value}>{category.label}</option>
                          ))}
                        </select>
                        <input defaultValue={item.description} onBlur={(event) => onUpdateItem(kit.id, item.id, { description: event.target.value })} />
                        <input defaultValue={item.quantity} onBlur={(event) => onUpdateItem(kit.id, item.id, { quantity: numberOrZero(event.target.value) })} />
                        <input defaultValue={item.unit} onBlur={(event) => onUpdateItem(kit.id, item.id, { unit: event.target.value })} />
                        <input defaultValue={item.unit_price} onBlur={(event) => onUpdateItem(kit.id, item.id, { unit_price: numberOrZero(event.target.value) })} />
                        <strong>{formatCurrency(item.total_price)}</strong>
                        <button className="icon-button" type="button" onClick={() => onDeleteItem(kit.id, item.id)} aria-label="Excluir item do kit">
                          <Trash2 size={15} />
                        </button>
                      </div>
                    ))}
                    <div className="kit-item-row kit-item-row--new">
                      <select value={itemDraft.category} onChange={(event) => setItemDrafts((current) => ({ ...current, [kit.id]: { ...itemDraft, category: event.target.value } }))}>
                        {PROPOSAL_ITEM_CATEGORIES.map((category) => (
                          <option key={category.value} value={category.value}>{category.label}</option>
                        ))}
                      </select>
                      <input placeholder="Descricao" value={itemDraft.description} onChange={(event) => setItemDrafts((current) => ({ ...current, [kit.id]: { ...itemDraft, description: event.target.value } }))} />
                      <input placeholder="Qtd" value={itemDraft.quantity} onChange={(event) => setItemDrafts((current) => ({ ...current, [kit.id]: { ...itemDraft, quantity: event.target.value } }))} />
                      <input placeholder="Un" value={itemDraft.unit} onChange={(event) => setItemDrafts((current) => ({ ...current, [kit.id]: { ...itemDraft, unit: event.target.value } }))} />
                      <input placeholder="Unitario" value={itemDraft.unit_price} onChange={(event) => setItemDrafts((current) => ({ ...current, [kit.id]: { ...itemDraft, unit_price: event.target.value } }))} />
                      <input placeholder="Ordem" value={itemDraft.sort_order} onChange={(event) => setItemDrafts((current) => ({ ...current, [kit.id]: { ...itemDraft, sort_order: event.target.value } }))} />
                      <button className="text-button" type="button" onClick={() => addItem(kit.id)}>
                        <Plus size={15} />
                        Item
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}

function ProposalTrackingSummary({ proposal }: { proposal: Proposal }) {
  const link = latestProposalShareLink(proposal);
  const pending = nextPendingProposalFollowup(proposal);
  const lastResponse = [...(proposal.customer_responses ?? [])].sort((a, b) => b.created_at.localeCompare(a.created_at))[0];

  return (
    <div className="proposal-tracking-cell">
      <span>{link ? `${link.views_count} visualizacoes` : "Sem link"}</span>
      <small>{pending ? `Retorno ${formatDateTime(pending.due_at)}` : "Sem follow-up"}</small>
      {lastResponse && <small>Cliente: {proposalResponseLabel(lastResponse.response_type)}</small>}
    </div>
  );
}

function ProposalResponsesPanel({ proposal }: { proposal: Proposal }) {
  const responses = [...(proposal.customer_responses ?? [])].sort((a, b) => b.created_at.localeCompare(a.created_at));
  return (
    <section className="proposal-side-panel">
      <div className="proposal-section-title">
        <strong>Respostas do cliente</strong>
        <span>{responses.length} registro(s)</span>
      </div>
      {responses.length ? (
        <div className="proposal-mini-list">
          {responses.map((response) => (
            <div key={response.id}>
              <span>{proposalResponseLabel(response.response_type)} - {formatDateTime(response.created_at)}</span>
              <strong>{response.customer_name ?? "Cliente"}</strong>
              {response.message && <p>{response.message}</p>}
            </div>
          ))}
        </div>
      ) : (
        <p>Nenhuma resposta digital registrada ainda.</p>
      )}
    </section>
  );
}

function ProposalTimeline({ proposal }: { proposal: Proposal }) {
  const events = [...(proposal.events ?? [])].sort((a, b) => b.created_at.localeCompare(a.created_at));
  return (
    <section className="proposal-side-panel">
      <div className="proposal-section-title">
        <strong>Linha do tempo</strong>
        <span>{events.length} evento(s)</span>
      </div>
      {events.length ? (
        <div className="proposal-timeline">
          {events.slice(0, 8).map((event) => (
            <div key={event.id}>
              <i />
              <div>
                <strong>{proposalEventLabel(event.event_type)}</strong>
                <span>{formatDateTime(event.created_at)}{event.channel ? ` via ${event.channel}` : ""}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p>Os eventos comerciais apareceram aqui conforme a proposta for gerada, enviada e respondida.</p>
      )}
    </section>
  );
}

function FollowupsPanel({
  followups,
  onComplete,
  onCancel,
}: {
  followups: ProposalFollowUp[];
  onComplete: (id: string) => Promise<void>;
  onCancel: (id: string) => Promise<void>;
}) {
  const sorted = [...followups].sort((a, b) => a.due_at.localeCompare(b.due_at));
  return (
    <section className="table-panel">
      <TableHeader columns={["Proposta", "Canal", "Vencimento", "Status", "Nota", "Acao"]} />
      {sorted.map((followup) => (
        <div className="table-row table-row--six" key={followup.id}>
          <span className="truncate">{followup.proposal_id}</span>
          <span>{followup.channel}</span>
          <span>{formatDateTime(followup.due_at)}</span>
          <span className={`followup-status followup-status--${followupEffectiveStatus(followup)}`}>
            {followupEffectiveStatus(followup)}
          </span>
          <span className="truncate">{followup.note ?? "Sem observacao"}</span>
          <div className="row-actions">
            {followup.status === "pending" && (
              <>
                <button className="text-button" onClick={() => onComplete(followup.id)}>
                  Concluir
                </button>
                <button className="text-button text-button--danger" onClick={() => onCancel(followup.id)}>
                  Cancelar
                </button>
              </>
            )}
          </div>
        </div>
      ))}
      {!sorted.length && <p className="empty-state">Nenhum follow-up de proposta registrado ainda.</p>}
    </section>
  );
}

function CompanySettingsPanel({
  settings,
  onUpdate,
}: {
  settings: CompanySettings;
  onUpdate: (payload: Partial<CompanySettings>) => Promise<void>;
}) {
  const [draft, setDraft] = useState({
    company_name: settings.company_name,
    company_phone: settings.company_phone ?? "",
    company_email: settings.company_email ?? "",
    company_website: settings.company_website ?? "",
    company_address: settings.company_address ?? "",
    company_logo_url: settings.company_logo_url ?? "",
    primary_color: settings.primary_color,
    secondary_color: settings.secondary_color,
    default_payment_conditions: settings.default_payment_conditions ?? "",
    default_proposal_validity_days: settings.default_proposal_validity_days,
    default_proposal_notes: settings.default_proposal_notes ?? "",
  });

  useEffect(() => {
    setDraft({
      company_name: settings.company_name,
      company_phone: settings.company_phone ?? "",
      company_email: settings.company_email ?? "",
      company_website: settings.company_website ?? "",
      company_address: settings.company_address ?? "",
      company_logo_url: settings.company_logo_url ?? "",
      primary_color: settings.primary_color,
      secondary_color: settings.secondary_color,
      default_payment_conditions: settings.default_payment_conditions ?? "",
      default_proposal_validity_days: settings.default_proposal_validity_days,
      default_proposal_notes: settings.default_proposal_notes ?? "",
    });
  }, [settings]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onUpdate({
      company_name: draft.company_name,
      company_phone: nullableText(draft.company_phone),
      company_email: nullableText(draft.company_email),
      company_website: nullableText(draft.company_website),
      company_address: nullableText(draft.company_address),
      company_logo_url: nullableText(draft.company_logo_url),
      primary_color: draft.primary_color,
      secondary_color: draft.secondary_color,
      default_payment_conditions: nullableText(draft.default_payment_conditions),
      default_proposal_validity_days: draft.default_proposal_validity_days,
      default_proposal_notes: nullableText(draft.default_proposal_notes),
    });
  }

  return (
    <form className="company-settings-form" onSubmit={submit}>
      <div className="section-heading">
        <div>
          <strong>Configuracoes comerciais</strong>
          <span>Dados usados no PDF, link publico e textos padrao da proposta.</span>
        </div>
        <button className="primary-button" type="submit">
          Salvar configuracoes
        </button>
      </div>
      <div className="company-settings-grid">
        <label>
          Nome da empresa
          <input value={draft.company_name} onChange={(event) => setDraft((current) => ({ ...current, company_name: event.target.value }))} />
        </label>
        <label>
          Telefone
          <input value={draft.company_phone} onChange={(event) => setDraft((current) => ({ ...current, company_phone: event.target.value }))} />
        </label>
        <label>
          E-mail
          <input value={draft.company_email} onChange={(event) => setDraft((current) => ({ ...current, company_email: event.target.value }))} />
        </label>
        <label>
          Site
          <input value={draft.company_website} onChange={(event) => setDraft((current) => ({ ...current, company_website: event.target.value }))} />
        </label>
        <label>
          Logo URL
          <input value={draft.company_logo_url} onChange={(event) => setDraft((current) => ({ ...current, company_logo_url: event.target.value }))} />
        </label>
        <label>
          Cor principal
          <input type="color" value={draft.primary_color} onChange={(event) => setDraft((current) => ({ ...current, primary_color: event.target.value }))} />
        </label>
        <label>
          Cor secundaria
          <input type="color" value={draft.secondary_color} onChange={(event) => setDraft((current) => ({ ...current, secondary_color: event.target.value }))} />
        </label>
        <label>
          Validade padrao
          <input type="number" min={1} max={90} value={draft.default_proposal_validity_days} onChange={(event) => setDraft((current) => ({ ...current, default_proposal_validity_days: Number(event.target.value) || 7 }))} />
        </label>
      </div>
      <label className="proposal-wide-field">
        Endereco comercial
        <textarea value={draft.company_address} onChange={(event) => setDraft((current) => ({ ...current, company_address: event.target.value }))} />
      </label>
      <label className="proposal-wide-field">
        Condicoes de pagamento padrao
        <textarea value={draft.default_payment_conditions} onChange={(event) => setDraft((current) => ({ ...current, default_payment_conditions: event.target.value }))} />
      </label>
      <label className="proposal-wide-field">
        Observacoes padrao da proposta
        <textarea value={draft.default_proposal_notes} onChange={(event) => setDraft((current) => ({ ...current, default_proposal_notes: event.target.value }))} />
      </label>
    </form>
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
      <TableHeader columns={["Problema", "Gravidade", "Risco IA", "Status", "Notas", "AÃ§Ã£o"]} />
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
                <option>Encaminhado para tÃ©cnico</option>
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
      ? "AnÃ¡lise Inteligente do lead"
      : variant === "ticket"
        ? "AnÃ¡lise Inteligente do chamado"
        : "AnÃ¡lise Inteligente do atendimento";

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
        <span>UrgÃªncia: {analysis.urgency_level}</span>
        <span>Oportunidade: {analysis.commercial_opportunity}</span>
        <span>Risco: {analysis.technical_risk}</span>
      </div>
      <div className="analysis-grid">
        <div>
          <small>Dados faltantes</small>
          <p>{analysis.missing_data.length ? analysis.missing_data.join(", ") : "Nenhum dado crÃ­tico pendente"}</p>
        </div>
        <div>
          <small>PrÃ³xima aÃ§Ã£o recomendada</small>
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
        ? "CrÃ­tico"
        : score >= 60
          ? "Alto"
          : score >= 35
            ? "MÃ©dio"
            : "Baixo"
      : score >= 75
        ? "Quente"
        : score >= 45
          ? "Morno"
          : "Frio";
  return (
    <span className={`score-badge score-badge--${label.toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "")}`}>
      {score}/100 Â· {label}
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
          <option>InstalaÃ§Ã£o</option>
          <option>HomologaÃ§Ã£o</option>
          <option>Monitoramento remoto</option>
          <option>Inversores</option>
          <option>Garantia</option>
          <option>ManutenÃ§Ã£o</option>
          <option>Limpeza das placas</option>
          <option>PÃ³s-venda</option>
          <option>SeguranÃ§a elÃ©trica</option>
        </select>
        <input
          placeholder="Palavras-chave separadas por vÃ­rgula"
          value={draft.keywords}
          onChange={(event) => setDraft({ ...draft, keywords: event.target.value })}
        />
        <div className="form-divider">VÃ­deo oficial</div>
        <input
          placeholder="TÃ­tulo do vÃ­deo"
          value={draft.videoTitle}
          onChange={(event) => setDraft({ ...draft, videoTitle: event.target.value })}
        />
        <input
          placeholder="Link do vÃ­deo do YouTube"
          value={draft.videoUrl}
          onChange={(event) => setDraft({ ...draft, videoUrl: event.target.value })}
        />
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={draft.sendVideoWithAnswer}
            onChange={(event) => setDraft({ ...draft, sendVideoWithAnswer: event.target.checked })}
          />
          Enviar vÃ­deo junto com a resposta
        </label>
        <div className="form-divider">Material de apoio</div>
        <input
          placeholder="TÃ­tulo do material de apoio"
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
              {article.video_url && <span>VÃ­deo</span>}
              {article.resource_url && <span>Material</span>}
              {article.send_video_with_answer && <span>VÃ­deo automÃ¡tico</span>}
              {article.send_resource_with_answer && <span>Material automÃ¡tico</span>}
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
    <section className="response-preview" aria-label="PrÃ©via da resposta">
      <strong>PrÃ©via para o cliente</strong>
      <p>{draft.answer || "A resposta oficial aparecerÃ¡ aqui."}</p>
      {draft.sendVideoWithAnswer && draft.videoUrl && (
        <div>
          <small>VÃ­deo recomendado:</small>
          <span>{draft.videoTitle || "VÃ­deo oficial da Solar SoluÃ§Ãµes"}</span>
          <a href={draft.videoUrl} target="_blank" rel="noreferrer">
            {draft.videoUrl}
          </a>
        </div>
      )}
      {draft.sendResourceWithAnswer && draft.resourceUrl && (
        <div>
          <small>Material de apoio:</small>
          <span>{draft.resourceTitle || "Material oficial da Solar SoluÃ§Ãµes"}</span>
          <a href={draft.resourceUrl} target="_blank" rel="noreferrer">
            {draft.resourceUrl}
          </a>
        </div>
      )}
    </section>
  );
}

function TableHeader({ columns }: { columns: string[] }) {
  const rowClass = columns.length === 8 ? "table-row--eight" : columns.length === 7 ? "table-row--seven" : "table-row--six";
  return (
    <div className={`table-header ${rowClass}`}>
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
