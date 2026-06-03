import { MonitorSmartphone, PanelRightOpen } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { getPublicProposal, sendPublicProposalResponse } from "./api";
import { AdminDashboard } from "./components/AdminDashboard";
import { ChatWidget } from "./components/ChatWidget";
import type { PublicProposal } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export function App() {
  const publicProposalToken = getPublicProposalToken();
  const [mode, setMode] = useState<"admin" | "widget">("admin");

  if (publicProposalToken) {
    return <PublicProposalPage token={publicProposalToken} />;
  }

  return (
    <div className="app-shell">
      <div className="mode-switch" role="tablist" aria-label="Modo de visualizacao">
        <button className={mode === "admin" ? "active" : ""} onClick={() => setMode("admin")}>
          <PanelRightOpen size={17} />
          Painel
        </button>
        <button className={mode === "widget" ? "active" : ""} onClick={() => setMode("widget")}>
          <MonitorSmartphone size={17} />
          Widget
        </button>
      </div>

      {mode === "admin" ? (
        <AdminDashboard />
      ) : (
        <main className="widget-demo">
          <section className="site-preview">
            <div>
              <span className="preview-kicker">Solar Soluções</span>
              <h1>Energia solar com acompanhamento especializado</h1>
              <p>
                Projetos fotovoltaicos residenciais, comerciais, industriais e rurais com suporte consultivo do primeiro
                contato ao pós-venda.
              </p>
            </div>
          </section>
          <ChatWidget />
        </main>
      )}
    </div>
  );
}

function getPublicProposalToken() {
  const match = window.location.pathname.match(/^\/proposta\/([^/]+)$/);
  return match?.[1] ?? null;
}

function PublicProposalPage({ token }: { token: string }) {
  const [data, setData] = useState<PublicProposal | null>(null);
  const [error, setError] = useState("");
  const [responseMessage, setResponseMessage] = useState("");
  const [changeMessage, setChangeMessage] = useState("");
  const pdfUrl = useMemo(() => (data ? `${API_BASE_URL}${data.pdf_download_url}` : "#"), [data]);

  useEffect(() => {
    getPublicProposal(token)
      .then(setData)
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Link indisponivel."));
  }, [token]);

  async function respond(responseType: string, message?: string) {
    try {
      const result = await sendPublicProposalResponse(token, {
        response_type: responseType,
        customer_name: data?.proposal.customer_name,
        customer_email: data?.proposal.customer_email,
        customer_phone: data?.proposal.customer_phone,
        message: message || null,
      });
      setResponseMessage(result.message);
    } catch (responseError) {
      setResponseMessage("Nao foi possivel registrar sua resposta agora. Fale com a equipe Solar Solucoes.");
    }
  }

  if (error) {
    return (
      <main className="public-proposal public-proposal--center">
        <section className="public-proposal__empty">
          <strong>Proposta indisponivel</strong>
          <p>{error}</p>
        </section>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="public-proposal public-proposal--center">
        <section className="public-proposal__empty">
          <strong>Carregando proposta...</strong>
        </section>
      </main>
    );
  }

  const { proposal, company } = data;

  return (
    <main className="public-proposal">
      <section className="public-proposal__hero">
        <div>
          <span>{company.company_name}</span>
          <h1>Proposta {proposal.proposal_number}</h1>
          <p>Proposta comercial de sistema solar fotovoltaico para avaliacao do cliente.</p>
        </div>
        <a className="public-proposal__download" href={pdfUrl} target="_blank" rel="noreferrer">
          Baixar PDF
        </a>
      </section>

      <section className="public-proposal__grid">
        <InfoCard label="Cliente" value={proposal.customer_name} />
        <InfoCard label="Cidade/UF" value={[proposal.city, proposal.state].filter(Boolean).join(" / ") || "A validar"} />
        <InfoCard label="Tipo de imovel" value={proposal.property_type ?? "A validar"} />
        <InfoCard label="Potencia estimada" value={proposal.estimated_system_power_kwp ? `${proposal.estimated_system_power_kwp} kWp` : "A validar"} />
        <InfoCard label="Geracao mensal" value={proposal.estimated_monthly_generation_kwh ? `${proposal.estimated_monthly_generation_kwh} kWh` : "A validar"} />
        <InfoCard label="Economia estimada" value={proposal.estimated_savings_percentage ? `${proposal.estimated_savings_percentage}%` : "A validar"} />
      </section>

      <section className="public-proposal__section">
        <h2>Itens da proposta</h2>
        {proposal.items.map((item) => (
          <div className="public-proposal__item" key={item.id}>
            <span>{item.category}</span>
            <strong>{item.description}</strong>
            <small>
              {item.quantity} {item.unit} x {formatCurrency(item.unit_price)}
            </small>
            <b>{formatCurrency(item.total_price)}</b>
          </div>
        ))}
      </section>

      <section className="public-proposal__financial">
        <span>Subtotal: <strong>{formatCurrency(proposal.subtotal)}</strong></span>
        <span>Desconto: <strong>{formatCurrency(proposal.discount)}</strong></span>
        <span>Total: <strong>{formatCurrency(proposal.total_amount)}</strong></span>
      </section>

      <section className="public-proposal__section">
        <h2>Condicoes e observacoes</h2>
        <p>{proposal.payment_conditions ?? "Condicoes a confirmar com a equipe comercial."}</p>
        <p>{proposal.notes ?? "Valores, prazos e economia estimada dependem de validacao tecnica e comercial."}</p>
      </section>

      <section className="public-proposal__actions">
        <button onClick={() => respond("interested")}>Tenho interesse</button>
        <button onClick={() => respond("accepted")}>Aceitar proposta</button>
        <button onClick={() => respond("talk_to_consultant")}>Falar com consultor</button>
        <button className="danger" onClick={() => respond("rejected", changeMessage)}>Recusar proposta</button>
      </section>

      <section className="public-proposal__section">
        <h2>Solicitar ajuste</h2>
        <textarea value={changeMessage} onChange={(event) => setChangeMessage(event.target.value)} placeholder="Descreva o ajuste desejado." />
        <button onClick={() => respond("request_changes", changeMessage)}>Enviar solicitacao de ajuste</button>
      </section>

      {responseMessage && <p className="public-proposal__confirmation">{responseMessage}</p>}
    </main>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <article className="public-proposal__card">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function formatCurrency(value: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value ?? 0));
}
