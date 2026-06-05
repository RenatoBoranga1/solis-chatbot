import { Bot, ExternalLink, FileUp, MessageCircle, PlayCircle, RefreshCw, Send, UserRound, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { ENABLE_DEMO_FALLBACK, checkApiHealth, sendChatMessage, uploadChatAttachment } from "../api";
import type { ChatMessage, QuickReply } from "../types";

const initialMessage =
  "Olá! Eu sou o Solis, assistente virtual da Solar Soluções. Posso te ajudar com orçamento, suporte técnico, instalação, manutenção, monitoramento, dúvidas sobre energia solar ou acompanhar um chamado. Como posso ajudar hoje?";

const initialQuickReplies: QuickReply[] = [
  { label: "Quero um orçamento", value: "Quero um orçamento" },
  { label: "Suporte técnico", value: "Preciso de suporte técnico" },
  { label: "Acompanhar projeto", value: "Quero acompanhar meu projeto" },
  { label: "Dúvida na conta", value: "Tenho dúvida sobre minha conta de energia" },
  { label: "Atendente", value: "Quero falar com atendente" },
];

const PROCESSING_MIN_DELAY_MS = 1200;
const PROCESSING_MAX_ARTIFICIAL_MS = 2500;
type ApiStatus = "checking" | "online" | "offline";

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

function normalizeIntentText(text: string) {
  return text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

function processingMessageFor(message: string) {
  const normalized = normalizeIntentText(message);
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

function isUrl(value: string) {
  return /^https:\/\/\S+$/i.test(value.trim());
}

function isYoutubeUrl(value: string) {
  try {
    const host = new URL(value.trim()).hostname.toLowerCase();
    return ["youtube.com", "www.youtube.com", "youtu.be"].includes(host);
  } catch {
    return false;
  }
}

function MessageContent({ content }: { content: string }) {
  const lines = content.split("\n");
  return (
    <>
      {lines.map((line, index) => {
        const trimmed = line.trim();
        if (isUrl(trimmed) && isYoutubeUrl(trimmed)) {
          return (
            <a className="video-link-card" href={trimmed} target="_blank" rel="noreferrer" key={`${trimmed}-${index}`}>
              <PlayCircle size={18} />
              <span>Assistir vídeo</span>
              <ExternalLink size={14} />
            </a>
          );
        }
        if (isUrl(trimmed)) {
          return (
            <a className="resource-link" href={trimmed} target="_blank" rel="noreferrer" key={`${trimmed}-${index}`}>
              {trimmed}
            </a>
          );
        }
        return (
          <span className="message-line" key={`${line}-${index}`}>
            {line}
          </span>
        );
      })}
    </>
  );
}

export function ChatWidget() {
  const [open, setOpen] = useState(true);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [quickReplies, setQuickReplies] = useState(initialQuickReplies);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: "welcome", sender: "bot", content: initialMessage },
  ]);
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | undefined>();
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");
  const [apiError, setApiError] = useState("");
  const [demoMode, setDemoMode] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const refreshApiStatus = useCallback(async () => {
    setApiStatus("checking");
    try {
      await checkApiHealth();
      setApiStatus("online");
      setApiError("");
      setDemoMode(false);
    } catch (error) {
      setApiStatus("offline");
      setApiError(error instanceof Error ? error.message : "API offline");
    }
  }, []);

  useEffect(() => {
    void refreshApiStatus();
  }, [refreshApiStatus]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  function addBotNotice(content: string) {
    setMessages((current) => [...current, { id: crypto.randomUUID(), sender: "bot", content }]);
  }

  function offlineMessage() {
    return ENABLE_DEMO_FALLBACK
      ? "Estou em modo demonstracao porque nao consegui conectar ao servidor do Solis. As mensagens deste teste nao serao salvas no painel."
      : "Nao consegui conectar ao sistema da Solar Solucoes agora. Por favor, tente novamente em instantes ou entre em contato com a equipe.";
  }

  async function submitMessage(message: string, attachment?: File) {
    const trimmed = message.trim();
    if ((!trimmed && !attachment) || loading) return;
    if (apiStatus === "checking") {
      addBotNotice("Ainda estou verificando a conexao com o servidor do Solis. Tente novamente em alguns instantes.");
      return;
    }
    if (attachment && apiStatus !== "online") {
      addBotNotice("Para enviar conta de energia, o servidor precisa estar conectado. Verifique se o backend esta ativo.");
      return;
    }
    if (apiStatus === "offline" && !ENABLE_DEMO_FALLBACK) {
      addBotNotice(offlineMessage());
      return;
    }

    const startedAt = Date.now();
    const customerMessage = trimmed || `Arquivo enviado: ${attachment?.name}`;
    const processingId = `processing-${crypto.randomUUID()}`;
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), sender: "customer", content: customerMessage },
      {
        id: processingId,
        sender: "bot",
        content: processingMessageFor(customerMessage),
        processing: true,
      },
    ]);
    setInput("");
    setSelectedFile(undefined);
    setLoading(true);

    try {
      const uploadedAttachment = attachment ? await uploadChatAttachment(attachment) : undefined;
      const response = await sendChatMessage({
        message: customerMessage,
        conversationId,
        attachmentUrl: uploadedAttachment?.attachment_url,
        mediaType: uploadedAttachment?.media_type,
      });
      if (response.demo) {
        setDemoMode(true);
        setApiStatus("offline");
      } else {
        setDemoMode(false);
        setApiStatus("online");
        setApiError("");
      }
      const elapsed = Date.now() - startedAt;
      const remainingDelay = Math.min(
        PROCESSING_MAX_ARTIFICIAL_MS,
        Math.max(0, PROCESSING_MIN_DELAY_MS - elapsed),
      );
      if (remainingDelay > 0) {
        await sleep(remainingDelay);
      }
      setConversationId(response.conversation_id);
      setQuickReplies(response.quick_replies.length ? response.quick_replies : []);
      setMessages((current) =>
        current
          .filter((item) => item.id !== processingId)
          .concat({ id: crypto.randomUUID(), sender: "bot", content: response.response }),
      );
    } catch (error) {
      setMessages((current) =>
        current
          .filter((item) => item.id !== processingId)
          .concat({
            id: crypto.randomUUID(),
            sender: "bot",
            content: attachment
              ? "Para enviar conta de energia, o servidor precisa estar conectado. Verifique se o backend esta ativo."
              : offlineMessage(),
          }),
      );
      setApiStatus("offline");
      setApiError(error instanceof Error ? error.message : "Falha ao conectar com a API.");
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitMessage(input, selectedFile);
  }

  function handleFileSelect(file?: File) {
    if (!file) return;
    if (apiStatus !== "online") {
      addBotNotice("Para enviar conta de energia, o servidor precisa estar conectado. Verifique se o backend esta ativo.");
      return;
    }
    setSelectedFile(file);
    setInput((current) => current || `Estou enviando o arquivo ${file.name}`);
  }

  if (!open) {
    return (
      <button className="solis-fab" onClick={() => setOpen(true)} aria-label="Abrir chat Solis">
        <MessageCircle size={24} />
      </button>
    );
  }

  return (
    <section className="solis-widget" aria-label="Chat Solis">
      <header className="solis-widget__header">
        <div className="solis-avatar" aria-hidden="true">
          <Bot size={22} />
        </div>
        <div>
          <strong>Solis</strong>
          <span>Assistente Virtual Solar Soluções</span>
        </div>
        <button className="icon-button" onClick={() => setOpen(false)} aria-label="Fechar chat">
          <X size={18} />
        </button>
      </header>

      {(apiStatus !== "online" || demoMode) && (
        <div className={`connection-banner connection-banner--${demoMode ? "demo" : apiStatus}`}>
          <div>
            <strong>{demoMode ? "Modo demonstracao" : apiStatus === "checking" ? "Conectando" : "API offline"}</strong>
            <span>
              {apiStatus === "checking"
                ? "Verificando conexao com o servidor do Solis."
                : demoMode
                  ? "As mensagens deste teste nao serao salvas no painel."
                  : "Nao foi possivel conectar ao servidor do Solis. O atendimento real nao sera salvo enquanto a API estiver offline."}
              {apiError ? ` ${apiError}` : ""}
            </span>
          </div>
          <button type="button" onClick={() => void refreshApiStatus()} disabled={apiStatus === "checking"}>
            <RefreshCw size={14} className={apiStatus === "checking" ? "spin" : ""} />
            Tentar reconectar
          </button>
        </div>
      )}

      <div className="solis-widget__messages">
        {messages.map((message) => (
          <article
            key={message.id}
            className={`message message--${message.sender}${message.processing ? " message--processing" : ""}`}
          >
            <span className="message__icon" aria-hidden="true">
              {message.sender === "customer" ? <UserRound size={16} /> : <Bot size={16} />}
            </span>
            <p>
              <MessageContent content={message.content} />
              {message.processing && (
                <span className="typing-dots" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                </span>
              )}
            </p>
          </article>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {quickReplies.length > 0 && (
        <div className="quick-replies" aria-label="Opções rápidas">
          {quickReplies.map((reply) => (
            <button
              key={reply.value}
              type="button"
              onClick={() => submitMessage(reply.value)}
              disabled={loading || apiStatus === "checking" || (apiStatus === "offline" && !ENABLE_DEMO_FALLBACK)}
            >
              {reply.label}
            </button>
          ))}
        </div>
      )}

      {selectedFile && <div className="attachment-pill">Arquivo: {selectedFile.name}</div>}

      <form className="solis-widget__composer" onSubmit={handleSubmit}>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,.pdf"
          hidden
          onChange={(event) => handleFileSelect(event.target.files?.[0])}
        />
        <button
          type="button"
          className="icon-button"
          onClick={() => fileInputRef.current?.click()}
          aria-label="Enviar imagem ou documento"
          title={apiStatus === "online" ? "Enviar imagem ou documento" : "Servidor offline: upload bloqueado"}
          disabled={loading || apiStatus !== "online"}
        >
          <FileUp size={18} />
        </button>
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Digite sua mensagem"
          aria-label="Mensagem"
          disabled={loading || apiStatus === "checking" || (apiStatus === "offline" && !ENABLE_DEMO_FALLBACK)}
        />
        <button
          className="send-button"
          type="submit"
          aria-label="Enviar mensagem"
          disabled={loading || apiStatus === "checking" || (apiStatus === "offline" && !ENABLE_DEMO_FALLBACK)}
        >
          <Send size={18} />
        </button>
      </form>
    </section>
  );
}
