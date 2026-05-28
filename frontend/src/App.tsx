import { MonitorSmartphone, PanelRightOpen } from "lucide-react";
import { useState } from "react";

import { AdminDashboard } from "./components/AdminDashboard";
import { ChatWidget } from "./components/ChatWidget";

export function App() {
  const [mode, setMode] = useState<"admin" | "widget">("admin");

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
