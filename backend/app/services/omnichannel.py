from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.phone import normalize_phone
from app.models import Conversation, ConversationChannelLink, Customer, Lead, Ticket, utc_now
from app.schemas import ContinueWhatsAppIn, ContinueWhatsAppOut
from app.services.intent import normalize
from app.services.whatsapp_cloud import WhatsAppCloudService

INVITED_STATUSES = {"pending", "invited"}
CONFIRMATION_TERMS = {"sim", "ok", "confirmo", "pode ser", "pode", "claro", "vamos", "autorizo"}


class OmnichannelService:
    def __init__(self, db: Session):
        self.db = db

    def continue_on_whatsapp(
        self,
        conversation_id: str,
        payload: ContinueWhatsAppIn,
    ) -> ContinueWhatsAppOut:
        conversation = self._require_conversation(conversation_id)
        customer = self._conversation_customer(conversation)
        phone = self._conversation_phone(conversation, customer)
        if not customer:
            raise ValueError("Atendimento sem cliente vinculado.")
        if not phone:
            raise ValueError("Cliente sem telefone para continuar no WhatsApp.")
        if conversation.channel == "whatsapp":
            raise ValueError("Este atendimento já está no WhatsApp.")
        if conversation.severity == "alta" and not payload.review_confirmed:
            raise PermissionError("Este caso tem gravidade alta e precisa de revisão humana antes do convite.")

        lead = self._lead_for_conversation(conversation.id)
        ticket = self._ticket_for_conversation(conversation.id)
        link = self._existing_link(conversation.id, phone) or ConversationChannelLink(
            customer_id=customer.id,
            source_conversation_id=conversation.id,
            source_channel=conversation.channel,
            target_channel="whatsapp",
            external_id=phone,
            phone=phone,
            lead_id=lead.id if lead else None,
            ticket_id=ticket.id if ticket else None,
            status="pending",
        )
        link.lead_id = lead.id if lead else link.lead_id
        link.ticket_id = ticket.id if ticket else link.ticket_id
        self.db.add(link)
        self.db.flush()

        message = payload.custom_message or self._build_invitation_message(conversation, customer, lead, ticket)
        send_status = self._send_invitation(phone, message, payload.template_name)
        link.status = "invited" if send_status in {"sent", "simulated"} else "failed"
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)

        return ContinueWhatsAppOut(
            status=send_status,
            conversation_channel_link_id=link.id,
            phone=phone,
            message=message,
            target_conversation_id=link.target_conversation_id,
        )

    def confirm_whatsapp_response(
        self,
        phone: str | None,
        external_id: str | None,
        message: str,
        customer: Customer | None,
    ) -> Conversation | None:
        normalized_phone = normalize_phone(phone or external_id)
        if not normalized_phone or not self.is_confirmation_message(message):
            return None

        link = self.pending_link_for_phone(normalized_phone)
        if not link:
            return None

        if link.target_conversation_id:
            existing = self.db.get(Conversation, link.target_conversation_id)
            if existing:
                link.status = "confirmed"
                link.confirmed_at = link.confirmed_at or utc_now()
                self.db.add(link)
                return existing

        source = self.db.get(Conversation, link.source_conversation_id)
        if not source:
            link.status = "failed"
            self.db.add(link)
            return None

        conversation_customer_id = link.customer_id or source.customer_id or (customer.id if customer else None)
        target = Conversation(
            customer_id=conversation_customer_id,
            channel="whatsapp",
            external_id=external_id or normalized_phone,
            status="open",
            intent=source.intent,
            severity=source.severity,
            summary=source.summary,
            collected_data=self._migrated_collected_data(source),
        )
        self.db.add(target)
        self.db.flush()

        link.target_conversation_id = target.id
        link.status = "confirmed"
        link.confirmed_at = utc_now()
        self.db.add(link)
        return target

    def pending_link_for_phone(self, phone: str) -> ConversationChannelLink | None:
        return self.db.scalar(
            select(ConversationChannelLink)
            .where(
                ConversationChannelLink.phone == phone,
                ConversationChannelLink.status.in_(list(INVITED_STATUSES)),
            )
            .order_by(desc(ConversationChannelLink.created_at))
            .limit(1)
        )

    @staticmethod
    def is_confirmation_message(message: str) -> bool:
        text = normalize(message)
        return text in CONFIRMATION_TERMS or any(term in text for term in ["sim", "confirmo", "pode ser"])

    def _send_invitation(self, phone: str, message: str, template_name: str) -> str:
        whatsapp = WhatsAppCloudService()
        app_env = settings.app_env.strip().lower()
        configured = bool(settings.whatsapp_access_token and settings.whatsapp_phone_number_id)
        if app_env != "production" and not configured:
            return "simulated"

        result = (
            whatsapp.send_template_message(phone, template_name)
            if app_env == "production"
            else whatsapp.send_text_message(phone, message)
        )
        if result.get("status") in {"error", "skipped"}:
            return "error"
        return "sent"

    def _build_invitation_message(
        self,
        conversation: Conversation,
        customer: Customer,
        lead: Lead | None,
        ticket: Ticket | None,
    ) -> str:
        name = self._first_name(customer.name) or "tudo bem"
        if lead or conversation.intent in {"orcamento", "viabilidade", "financiamento", "comercial"}:
            return (
                f"Olá, {name}! Recebemos sua solicitação de orçamento pelo site da Solar Soluções. "
                "Já temos seus dados iniciais e podemos continuar seu atendimento por este WhatsApp. "
                "Para confirmar, responda SIM por aqui."
            )
        if ticket or conversation.intent in {"suporte_tecnico", "problema_inversor", "baixa_geracao", "erro_monitoramento"}:
            return (
                f"Olá, {name}! Recebemos sua solicitação de suporte pelo site da Solar Soluções. "
                "Para dar continuidade ao atendimento e facilitar o envio de fotos ou documentos, podemos continuar por este WhatsApp. "
                "Responda SIM para confirmar."
            )
        return (
            f"Olá, {name}! Recebemos seu atendimento pelo site da Solar Soluções. "
            "Podemos continuar por este WhatsApp com o contexto já registrado. Responda SIM para confirmar."
        )

    def _migrated_collected_data(self, source: Conversation) -> dict:
        collected = dict(source.collected_data or {})
        collected.update(
            {
                "migrated_from_channel": source.channel,
                "source_conversation_id": source.id,
                "whatsapp_confirmed_at": utc_now().isoformat(),
                "omnichannel_confirmed_pending_response": True,
            }
        )
        if source.summary:
            collected.setdefault("source_summary", source.summary)
        return collected

    def _conversation_customer(self, conversation: Conversation) -> Customer | None:
        if conversation.customer:
            return conversation.customer
        return self.db.get(Customer, conversation.customer_id) if conversation.customer_id else None

    def _conversation_phone(self, conversation: Conversation, customer: Customer | None) -> str | None:
        collected = conversation.collected_data or {}
        return normalize_phone(
            (customer.phone if customer else None)
            or collected.get("phone")
            or collected.get("whatsapp")
            or collected.get("telefone")
        )

    def _lead_for_conversation(self, conversation_id: str) -> Lead | None:
        return self.db.scalar(select(Lead).where(Lead.conversation_id == conversation_id).order_by(desc(Lead.created_at)).limit(1))

    def _ticket_for_conversation(self, conversation_id: str) -> Ticket | None:
        return self.db.scalar(select(Ticket).where(Ticket.conversation_id == conversation_id).order_by(desc(Ticket.created_at)).limit(1))

    def _existing_link(self, conversation_id: str, phone: str) -> ConversationChannelLink | None:
        return self.db.scalar(
            select(ConversationChannelLink)
            .where(
                ConversationChannelLink.source_conversation_id == conversation_id,
                ConversationChannelLink.phone == phone,
                ConversationChannelLink.status.in_(["pending", "invited", "failed"]),
            )
            .order_by(desc(ConversationChannelLink.created_at))
            .limit(1)
        )

    def _require_conversation(self, conversation_id: str) -> Conversation:
        conversation = self.db.get(Conversation, conversation_id)
        if not conversation:
            raise ValueError("Conversation not found")
        return conversation

    @staticmethod
    def _first_name(name: str | None) -> str | None:
        if not name:
            return None
        return name.strip().split()[0]
