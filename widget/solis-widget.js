(function () {
  const script = document.currentScript;
  const apiBase = script?.dataset.apiBase || "http://localhost:8000";
  const brandName = script?.dataset.brandName || "Solar Soluções";

  let conversationId = null;
  let open = false;
  let sending = false;
  const minProcessingDelay = 1200;
  const maxArtificialDelay = 2500;

  const quickReplies = [
    "Quero um orçamento",
    "Preciso de suporte técnico",
    "Quero acompanhar meu projeto",
    "Tenho dúvida sobre minha conta de energia",
    "Quero falar com atendente",
  ];

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  function normalizeIntentText(text) {
    return String(text || "")
      .normalize("NFD")
      .replace(/\p{Diacritic}/gu, "")
      .toLowerCase();
  }

  function processingMessageFor(text) {
    const normalized = normalizeIntentText(text);
    if (
      normalized.includes("orcamento") ||
      normalized.includes("instalar") ||
      normalized.includes("energia solar") ||
      normalized.includes("cotacao")
    ) {
      return "Solis está preparando a próxima pergunta para seu orçamento...";
    }
    if (
      normalized.includes("suporte") ||
      normalized.includes("tecnico") ||
      normalized.includes("problema") ||
      normalized.includes("inversor") ||
      normalized.includes("gerando") ||
      normalized.includes("app")
    ) {
      return "Solis está analisando o melhor encaminhamento técnico...";
    }
    if (
      normalized.includes("duvida") ||
      normalized.includes("conta") ||
      normalized.includes("credito") ||
      normalized.includes("economia")
    ) {
      return "Solis está buscando a melhor resposta...";
    }
    if (normalized.includes("atendente") || normalized.includes("humano") || normalized.includes("falar com alguem")) {
      return "Solis está registrando sua solicitação para encaminhamento...";
    }
    return "Solis está processando sua solicitação...";
  }

  const styles = document.createElement("style");
  styles.textContent = `
    .solis-embed-fab {
      position: fixed;
      right: 22px;
      bottom: 22px;
      z-index: 99990;
      width: 58px;
      height: 58px;
      border: 0;
      border-radius: 50%;
      background: #ffd34d;
      color: #10243a;
      box-shadow: 0 16px 32px rgba(0,0,0,.22);
      cursor: pointer;
      font: 700 22px system-ui, sans-serif;
    }
    .solis-embed-panel {
      position: fixed;
      right: 22px;
      bottom: 92px;
      z-index: 99991;
      display: none;
      grid-template-rows: auto 1fr auto auto;
      width: min(390px, calc(100vw - 28px));
      height: min(650px, calc(100vh - 116px));
      overflow: hidden;
      border: 1px solid #d8e1ea;
      border-radius: 8px;
      background: #fff;
      box-shadow: 0 24px 60px rgba(0,0,0,.26);
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .solis-embed-panel.is-open { display: grid; }
    .solis-embed-header {
      display: grid;
      grid-template-columns: 42px 1fr auto;
      gap: 10px;
      align-items: center;
      padding: 14px;
      background: #10243a;
      color: #fff;
    }
    .solis-embed-avatar {
      display: grid;
      place-items: center;
      width: 42px;
      height: 42px;
      border-radius: 8px;
      background: #ffd34d;
      color: #10243a;
      font-weight: 800;
    }
    .solis-embed-header strong,
    .solis-embed-header span { display: block; }
    .solis-embed-header span { color: #c9d7e6; font-size: 12px; }
    .solis-embed-close {
      border: 0;
      width: 34px;
      height: 34px;
      border-radius: 6px;
      background: transparent;
      color: #fff;
      cursor: pointer;
      font-size: 22px;
    }
    .solis-embed-messages {
      display: grid;
      align-content: start;
      gap: 10px;
      overflow-y: auto;
      padding: 14px;
      background: #f6f8fb;
    }
    .solis-embed-message {
      max-width: 90%;
      border-radius: 8px;
      padding: 10px 12px;
      color: #1b2b3d;
      background: #fff;
      line-height: 1.45;
      white-space: pre-wrap;
      box-shadow: 0 1px 0 rgba(18,32,51,.07);
    }
    .solis-embed-message.customer {
      justify-self: end;
      background: #ffd34d;
      color: #10243a;
    }
    .solis-embed-message.processing {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: #526274;
      background: #eef3f7;
    }
    .solis-embed-dots {
      display: inline-flex;
      gap: 3px;
      min-width: 22px;
    }
    .solis-embed-dots span {
      width: 5px;
      height: 5px;
      border-radius: 50%;
      background: #7b8998;
      animation: solisEmbedTypingPulse 1.1s ease-in-out infinite;
    }
    .solis-embed-dots span:nth-child(2) { animation-delay: .16s; }
    .solis-embed-dots span:nth-child(3) { animation-delay: .32s; }
    .solis-embed-quick {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      border-top: 1px solid #e7edf4;
      padding: 10px 12px;
    }
    .solis-embed-quick button {
      border: 1px solid #d4dde8;
      border-radius: 999px;
      padding: 7px 10px;
      color: #10243a;
      background: #fff;
      cursor: pointer;
      font: 500 13px inherit;
    }
    .solis-embed-quick button:disabled,
    .solis-embed-form input:disabled,
    .solis-embed-form button:disabled {
      cursor: not-allowed;
      opacity: .68;
    }
    .solis-embed-form {
      display: grid;
      grid-template-columns: 1fr 42px;
      gap: 8px;
      border-top: 1px solid #e7edf4;
      padding: 10px;
    }
    .solis-embed-form input {
      min-height: 40px;
      border: 1px solid #ccd6e2;
      border-radius: 6px;
      padding: 0 12px;
      color: #132234;
    }
    .solis-embed-form button {
      border: 0;
      border-radius: 6px;
      background: #ffd34d;
      color: #10243a;
      cursor: pointer;
      font-weight: 800;
    }
    @keyframes solisEmbedTypingPulse {
      0%, 80%, 100% { opacity: .28; transform: translateY(0); }
      40% { opacity: 1; transform: translateY(-2px); }
    }
    @media (max-width: 480px) {
      .solis-embed-panel {
        right: 10px;
        bottom: 78px;
        width: calc(100vw - 20px);
        height: min(620px, calc(100vh - 88px));
      }
      .solis-embed-fab { right: 10px; bottom: 10px; }
    }
  `;
  document.head.appendChild(styles);

  const fab = document.createElement("button");
  fab.className = "solis-embed-fab";
  fab.type = "button";
  fab.setAttribute("aria-label", "Abrir chat Solis");
  fab.textContent = "S";

  const panel = document.createElement("section");
  panel.className = "solis-embed-panel";
  panel.setAttribute("aria-label", "Chat Solis");
  panel.innerHTML = `
    <header class="solis-embed-header">
      <div class="solis-embed-avatar">S</div>
      <div><strong>Solis</strong><span>Assistente Virtual ${brandName}</span></div>
      <button class="solis-embed-close" type="button" aria-label="Fechar">x</button>
    </header>
    <div class="solis-embed-messages"></div>
    <div class="solis-embed-quick"></div>
    <form class="solis-embed-form">
      <input aria-label="Mensagem" placeholder="Digite sua mensagem" />
      <button aria-label="Enviar" type="submit">></button>
    </form>
  `;

  document.body.appendChild(panel);
  document.body.appendChild(fab);

  const messages = panel.querySelector(".solis-embed-messages");
  const quick = panel.querySelector(".solis-embed-quick");
  const form = panel.querySelector(".solis-embed-form");
  const input = form.querySelector("input");
  const submitButton = form.querySelector("button");

  function addMessage(sender, text, options = {}) {
    const message = document.createElement("div");
    message.className = `solis-embed-message ${sender}${options.processing ? " processing" : ""}`;
    message.textContent = text;
    if (options.processing) {
      const dots = document.createElement("span");
      dots.className = "solis-embed-dots";
      dots.setAttribute("aria-hidden", "true");
      dots.innerHTML = "<span></span><span></span><span></span>";
      message.appendChild(dots);
    }
    messages.appendChild(message);
    messages.scrollTop = messages.scrollHeight;
    return message;
  }

  function setSendingState(nextSending) {
    sending = nextSending;
    input.disabled = nextSending;
    submitButton.disabled = nextSending;
    quick.querySelectorAll("button").forEach((button) => {
      button.disabled = nextSending;
    });
  }

  function renderQuick(values) {
    quick.innerHTML = "";
    values.forEach((value) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = value;
      button.disabled = sending;
      button.addEventListener("click", () => send(value));
      quick.appendChild(button);
    });
  }

  async function send(text) {
    const message = String(text || input.value || "").trim();
    if (!message || sending) return;
    const startedAt = Date.now();
    setSendingState(true);
    input.value = "";
    addMessage("customer", message);
    const processingMessage = addMessage("bot", processingMessageFor(message), { processing: true });
    try {
      const response = await fetch(`${apiBase}/chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel: "site",
          conversation_id: conversationId,
          message,
        }),
      });
      if (!response.ok) throw new Error("Request failed");
      const data = await response.json();
      const elapsed = Date.now() - startedAt;
      const remainingDelay = Math.min(maxArtificialDelay, Math.max(0, minProcessingDelay - elapsed));
      if (remainingDelay > 0) {
        await sleep(remainingDelay);
      }
      processingMessage.remove();
      conversationId = data.conversation_id;
      addMessage("bot", data.response);
      renderQuick((data.quick_replies || []).map((item) => item.value));
    } catch (error) {
      processingMessage.remove();
      addMessage("bot", "Não consegui conectar ao atendimento agora. Verifique se a API local está ativa e tente novamente.");
    } finally {
      setSendingState(false);
    }
  }

  fab.addEventListener("click", () => {
    open = !open;
    panel.classList.toggle("is-open", open);
  });
  panel.querySelector(".solis-embed-close").addEventListener("click", () => {
    open = false;
    panel.classList.remove("is-open");
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    send();
  });

  addMessage(
    "bot",
    "Olá! Eu sou o Solis, assistente virtual da Solar Soluções. Posso te ajudar com orçamento, suporte técnico, instalação, manutenção, monitoramento, dúvidas sobre energia solar ou acompanhar um chamado. Como posso ajudar hoje?",
  );
  renderQuick(quickReplies);
})();
