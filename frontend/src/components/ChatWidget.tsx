import { Bot, FileUp, Loader2, MessageCircle, Send, UserRound, X } from "lucide-react";
import { FormEvent, useRef, useState } from "react";

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

  async function submitMessage(message: string, attachmentUrl?: string) {
    const trimmed = message.trim();
    if (!trimmed && !attachmentUrl) return;

    const customerMessage = trimmed || `Arquivo enviado: ${attachmentUrl}`;
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), sender: "customer", content: customerMessage },
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
      setConversationId(response.conversation_id);
      setQuickReplies(response.quick_replies.length ? response.quick_replies : []);
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), sender: "bot", content: response.response },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          sender: "bot",
          content:
            "Não consegui conectar à API local agora. Verifique se o backend está rodando em http://127.0.0.1:8000.",
        },
      ]);
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
          <article key={message.id} className={`message message--${message.sender}`}>
            <span className="message__icon" aria-hidden="true">
              {message.sender === "customer" ? <UserRound size={16} /> : <Bot size={16} />}
            </span>
            <p>{message.content}</p>
          </article>
        ))}
        {loading && (
          <article className="message message--bot message--typing">
            <span className="message__icon" aria-hidden="true">
              <Loader2 size={16} className="spin" />
            </span>
            <p>Solis está digitando...</p>
          </article>
        )}
      </div>

      {quickReplies.length > 0 && (
        <div className="quick-replies" aria-label="Opções rápidas">
          {quickReplies.map((reply) => (
            <button key={reply.value} type="button" onClick={() => submitMessage(reply.value)}>
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
        >
          <FileUp size={18} />
        </button>
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Digite sua mensagem"
          aria-label="Mensagem"
        />
        <button className="send-button" type="submit" aria-label="Enviar mensagem" disabled={loading}>
          <Send size={18} />
        </button>
      </form>
    </section>
  );
}
