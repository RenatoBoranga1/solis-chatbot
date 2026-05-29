import { Bot, FileUp, MessageCircle, Send, UserRound, X } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";

import { sendChatMessage } from "../api";
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

export function ChatWidget() {
  const [open, setOpen] = useState(true);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [quickReplies, setQuickReplies] = useState(initialQuickReplies);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: "welcome", sender: "bot", content: initialMessage },
  ]);
  const [loading, setLoading] = useState(false);
  const [attachmentName, setAttachmentName] = useState<string | undefined>();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  async function submitMessage(message: string, attachmentUrl?: string) {
    const trimmed = message.trim();
    if ((!trimmed && !attachmentUrl) || loading) return;

    const startedAt = Date.now();
    const customerMessage = trimmed || `Arquivo enviado: ${attachmentUrl}`;
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
    setAttachmentName(undefined);
    setLoading(true);

    try {
      const response = await sendChatMessage({
        message: customerMessage,
        conversationId,
        attachmentUrl,
      });
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
            content: "Não consegui conectar ao atendimento agora. Verifique se a API local está ativa e tente novamente.",
          }),
      );
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitMessage(input, attachmentName);
  }

  function handleFileSelect(file?: File) {
    if (!file) return;
    setAttachmentName(file.name);
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
              {message.content}
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
            <button key={reply.value} type="button" onClick={() => submitMessage(reply.value)} disabled={loading}>
              {reply.label}
            </button>
          ))}
        </div>
      )}

      {attachmentName && <div className="attachment-pill">Arquivo: {attachmentName}</div>}

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
          title="Enviar imagem ou documento"
          disabled={loading}
        >
          <FileUp size={18} />
        </button>
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Digite sua mensagem"
          aria-label="Mensagem"
          disabled={loading}
        />
        <button className="send-button" type="submit" aria-label="Enviar mensagem" disabled={loading}>
          <Send size={18} />
        </button>
      </form>
    </section>
  );
}
