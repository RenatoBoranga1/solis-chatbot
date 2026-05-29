from dataclasses import dataclass
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.privacy import LGPD_CONSENT_MESSAGE, encrypt_value
from app.core.security import sanitize_text
from app.models import Attachment, Conversation, Customer, Handoff, Lead, Message, Ticket, utc_now
from app.schemas import ChatMessageIn, ChatMessageOut, QuickReply
from app.services.flows import next_missing_question, summarize_collected_data
from app.services.intent import classify_intent, is_commercial_intent, is_support_intent, normalize
from app.services.rag import KnowledgeService
from app.services.severity import classify_severity, is_electrical_risk
from app.services.solis_prompt import ELECTRICAL_RISK_MESSAGE, HUMAN_HANDOFF_MESSAGE, WELCOME_MESSAGE


DEFAULT_QUICK_REPLIES = [
    QuickReply(label="Quero um orçamento", value="Quero um orçamento"),
    QuickReply(label="Preciso de suporte técnico", value="Preciso de suporte técnico"),
    QuickReply(label="Acompanhar meu projeto", value="Quero acompanhar meu projeto"),
    QuickReply(label="Dúvida sobre conta", value="Tenho dúvida sobre minha conta de energia"),
    QuickReply(label="Falar com atendente", value="Quero falar com atendente"),
]


@dataclass(frozen=True)
class PersistedBotAction:
    response: str
    handoff_required: bool = False
    created_lead_id: str | None = None
    created_ticket_id: str | None = None
    next_question_key: str | None = None


class ConversationService:
    def __init__(self, db: Session):
        self.db = db
        self.knowledge = KnowledgeService(db)

    def handle_message(self, payload: ChatMessageIn) -> ChatMessageOut:
        message_text = sanitize_text(payload.message)
        conversation = self._get_or_create_conversation(payload)
        customer = conversation.customer

        customer_message = Message(
            conversation_id=conversation.id,
            sender_type="customer",
            content=message_text,
            attachment_url=payload.attachment_url,
            provider=self._message_provider(payload),
            provider_message_id=payload.provider_message_id,
        )
        self.db.add(customer_message)
        self.db.flush()
        self._create_attachment_if_present(conversation, customer_message, payload)

        intent_result = classify_intent(message_text)
        severity_result = classify_severity(message_text, intent_result.name)
        conversation.intent = conversation.intent or intent_result.name
        conversation.severity = self._strongest_severity(conversation.severity, severity_result.level)

        collected = dict(conversation.collected_data or {})
        self._capture_answer_from_previous_question(collected, customer, message_text)
        self._merge_payload_customer(customer, payload)

        attachment_reference = payload.attachment_url or (
            f"whatsapp://media/{payload.media_id}" if payload.media_id else None
        )
        if attachment_reference:
            collected.setdefault("attachments", [])
            collected["attachments"] = [*collected["attachments"], attachment_reference]

        action = self._decide_action(conversation, customer, collected, message_text, intent_result.name)
        conversation.collected_data = collected
        conversation.summary = summarize_collected_data(collected)

        self.db.add(
            Message(
                conversation_id=conversation.id,
                sender_type="bot",
                content=action.response,
            )
        )
        self.db.commit()
        self.db.refresh(conversation)

        return ChatMessageOut(
            conversation_id=conversation.id,
            customer_id=conversation.customer_id,
            response=action.response,
            intent=conversation.intent,
            severity=conversation.severity,
            status=conversation.status,
            handoff_required=action.handoff_required,
            created_lead_id=action.created_lead_id,
            created_ticket_id=action.created_ticket_id,
            next_question_key=action.next_question_key,
            quick_replies=[] if action.next_question_key else DEFAULT_QUICK_REPLIES,
            summary=conversation.summary,
        )

    def request_handoff(self, conversation_id: str, reason: str, assigned_to: str | None = None) -> Handoff:
        conversation = self._get_conversation(conversation_id)
        handoff = Handoff(conversation_id=conversation.id, reason=reason, assigned_to=assigned_to)
        conversation.status = "handoff"
        conversation.transferred_to_human = True
        conversation.assigned_to = assigned_to
        self.db.add(handoff)
        self.db.commit()
        self.db.refresh(handoff)
        return handoff

    def assign_conversation(self, conversation_id: str, assigned_to: str | None) -> Conversation:
        conversation = self._get_conversation(conversation_id)
        conversation.assigned_to = assigned_to
        conversation.status = "human_assigned" if assigned_to else conversation.status
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    @staticmethod
    def _message_provider(payload: ChatMessageIn) -> str | None:
        if payload.provider:
            return payload.provider
        if payload.channel == "whatsapp":
            return "whatsapp"
        return payload.channel

    def _create_attachment_if_present(
        self,
        conversation: Conversation,
        message: Message,
        payload: ChatMessageIn,
    ) -> None:
        file_url = payload.attachment_url
        if not file_url and payload.media_id:
            file_url = f"whatsapp://media/{payload.media_id}"

        if not file_url:
            return

        self.db.add(
            Attachment(
                message_id=message.id,
                conversation_id=conversation.id,
                provider=self._message_provider(payload),
                provider_media_id=payload.media_id,
                file_type=payload.media_type or "unknown",
                file_url=file_url,
            )
        )

    def _decide_action(
        self,
        conversation: Conversation,
        customer: Customer | None,
        collected: dict,
        message_text: str,
        intent: str,
    ) -> PersistedBotAction:
        if normalize(message_text) in {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "menu"}:
            return PersistedBotAction(WELCOME_MESSAGE)

        if intent == "humano":
            return self._handoff(conversation, "Cliente solicitou atendimento humano.", HUMAN_HANDOFF_MESSAGE)

        if is_electrical_risk(message_text):
            ticket = self._create_ticket_if_needed(conversation, customer, collected, "Risco elétrico", "alta")
            return self._handoff(conversation, "Risco elétrico informado pelo cliente.", ELECTRICAL_RISK_MESSAGE, ticket.id)

        severity = classify_severity(message_text, intent)
        if severity.handoff_required and severity.level == "alta":
            ticket = self._create_ticket_if_needed(conversation, customer, collected, intent, "alta")
            response = (
                "Entendi. Esse caso precisa de prioridade e uma análise cuidadosa da equipe. "
                "Vou registrar as informações e encaminhar para um especialista da Solar Soluções agora."
            )
            return self._handoff(conversation, severity.reason, response, ticket.id)

        flow = collected.get("flow")
        if not flow:
            if intent == "erro_monitoramento" or intent == "wifi_inversor":
                flow = "app_monitoramento"
            elif is_commercial_intent(intent):
                flow = "orcamento"
            elif is_support_intent(intent) or intent == "reclamacao":
                flow = "suporte"
            collected["flow"] = flow

        if flow in {"orcamento", "suporte", "app_monitoramento"} and customer and not customer.lgpd_consent:
            if collected.get("lgpd_pending") and self._is_affirmative(message_text):
                customer.lgpd_consent = True
                customer.lgpd_consent_at = utc_now()
                collected.pop("lgpd_pending", None)
            elif not collected.get("lgpd_pending"):
                collected["lgpd_pending"] = True
                return PersistedBotAction(LGPD_CONSENT_MESSAGE, next_question_key="lgpd_consent")
            elif self._is_negative(message_text):
                conversation.status = "limited"
                return PersistedBotAction(
                    "Sem problemas. Posso responder dúvidas gerais, mas para abrir orçamento ou chamado "
                    "preciso de alguns dados mínimos. Quando quiser continuar, é só me avisar."
                )
            else:
                return PersistedBotAction(
                    "Para seguir com segurança e conforme a LGPD, preciso da sua confirmação. Tudo bem eu coletar "
                    "dados de contato e da instalação apenas para atendimento, orçamento ou suporte?",
                    next_question_key="lgpd_consent",
                )

        if flow == "orcamento":
            return self._continue_budget_flow(conversation, customer, collected)

        if flow == "suporte":
            return self._continue_support_flow(conversation, customer, collected, intent)

        if flow == "app_monitoramento":
            return self._continue_app_flow(conversation, customer, collected)

        knowledge_answer = self.knowledge.answer_from_base(message_text)
        if knowledge_answer.answer:
            conversation.bot_resolved = True
            return PersistedBotAction(
                f"{knowledge_answer.answer}\n\nPosso te ajudar com mais alguma informação ou prefere que eu registre um atendimento?"
            )

        self.knowledge.record_unanswered(message_text, conversation.id, intent)
        return self._handoff(
            conversation,
            "Pergunta sem resposta confiável na base de conhecimento.",
            "Essa informação precisa ser confirmada pela equipe da Solar Soluções para eu não te passar algo impreciso. "
            "Vou registrar sua pergunta e encaminhar para um especialista.",
        )

    def _continue_budget_flow(
        self, conversation: Conversation, customer: Customer | None, collected: dict
    ) -> PersistedBotAction:
        question = next_missing_question("orcamento", collected)
        if question:
            collected["last_question_key"] = question.key
            return PersistedBotAction(question.question, next_question_key=question.key)

        lead = self._create_lead(conversation, customer, collected)
        conversation.status = "commercial_triage"
        conversation.transferred_to_human = True
        name = collected.get("name") or (customer.name if customer else None) or "tudo certo"
        response = (
            f"Perfeito, {name}. Com essas informações, a equipe da Solar Soluções consegue preparar uma análise "
            "mais precisa para estimar economia, potência ideal do sistema e possibilidade de financiamento. "
            "Vou registrar sua solicitação e encaminhar para o setor comercial."
        )
        self.db.add(Handoff(conversation_id=conversation.id, reason="Lead de orçamento concluído."))
        return PersistedBotAction(response, handoff_required=True, created_lead_id=lead.id)

    def _continue_support_flow(
        self, conversation: Conversation, customer: Customer | None, collected: dict, intent: str
    ) -> PersistedBotAction:
        question = next_missing_question("suporte", collected)
        if question:
            collected["last_question_key"] = question.key
            return PersistedBotAction(question.question, next_question_key=question.key)

        severity = classify_severity(
            " ".join(str(value) for value in collected.values() if isinstance(value, str)),
            intent,
        )
        ticket = self._create_ticket_if_needed(
            conversation,
            customer,
            collected,
            collected.get("problem_type") or intent,
            severity.level,
        )
        if severity.level == "alta":
            return self._handoff(
                conversation,
                severity.reason,
                "Obrigado pelas informações. Como o caso foi classificado como alta gravidade, não recomendo mexer "
                "no equipamento. Vou encaminhar agora para a equipe técnica da Solar Soluções.",
                ticket.id,
            )
        conversation.status = "technical_triage"
        response = (
            "Obrigado pelas informações. Isso já ajuda bastante a equipe técnica. "
            f"Registrei seu chamado como gravidade {ticket.severity} e vou acompanhar o encaminhamento. "
            "Se surgir cheiro de queimado, faísca, aquecimento excessivo ou risco elétrico, não mexa no equipamento e avise imediatamente."
        )
        return PersistedBotAction(response, created_ticket_id=ticket.id)

    def _continue_app_flow(
        self, conversation: Conversation, customer: Customer | None, collected: dict
    ) -> PersistedBotAction:
        if not collected.get("app_intro_sent"):
            collected["app_intro_sent"] = True
            return PersistedBotAction(
                "Entendi. Quando o aplicativo não atualiza, muitas vezes a causa está na internet ou na conexão "
                "do inversor com o roteador. Vou checar alguns pontos simples com você.",
                next_question_key="app_intro",
            )

        question = next_missing_question("app_monitoramento", collected)
        if question:
            collected["last_question_key"] = question.key
            return PersistedBotAction(question.question, next_question_key=question.key)

        collected["problem_type"] = "Aplicativo de monitoramento sem atualizar"
        ticket = self._create_ticket_if_needed(conversation, customer, collected, collected["problem_type"], "media")
        conversation.status = "technical_triage"
        response = (
            "Obrigado. Vou abrir um chamado técnico para verificar a conexão de monitoramento. "
            "Isso nem sempre significa que o sistema parou de gerar energia, mas precisa de conferência da equipe."
        )
        return PersistedBotAction(response, created_ticket_id=ticket.id)

    def _handoff(
        self,
        conversation: Conversation,
        reason: str,
        response: str,
        created_ticket_id: str | None = None,
    ) -> PersistedBotAction:
        conversation.status = "handoff"
        conversation.transferred_to_human = True
        self.db.add(Handoff(conversation_id=conversation.id, reason=reason))
        return PersistedBotAction(
            response=response,
            handoff_required=True,
            created_ticket_id=created_ticket_id,
        )

    def _create_lead(self, conversation: Conversation, customer: Customer | None, collected: dict) -> Lead:
        if not customer:
            customer = Customer(lgpd_consent=True, lgpd_consent_at=utc_now())
            self.db.add(customer)
            self.db.flush()
            conversation.customer_id = customer.id

        existing = self.db.scalar(select(Lead).where(Lead.conversation_id == conversation.id))
        if existing:
            return existing

        lead = Lead(
            customer_id=customer.id,
            conversation_id=conversation.id,
            property_type=collected.get("property_type"),
            average_bill=self._money_to_float(collected.get("average_bill")),
            utility_company=collected.get("utility_company"),
            roof_type=collected.get("roof_type"),
            financing_interest=self._boolean_or_none(collected.get("financing_interest")),
            status="Novo orçamento",
            notes=summarize_collected_data(collected),
            extra=collected,
        )
        self.db.add(lead)
        self.db.flush()
        return lead

    def _create_ticket_if_needed(
        self,
        conversation: Conversation,
        customer: Customer | None,
        collected: dict,
        problem_type: str,
        severity: str,
    ) -> Ticket:
        if not customer:
            customer = Customer(lgpd_consent=True, lgpd_consent_at=utc_now())
            self.db.add(customer)
            self.db.flush()
            conversation.customer_id = customer.id

        existing = self.db.scalar(select(Ticket).where(Ticket.conversation_id == conversation.id))
        if existing:
            existing.severity = self._strongest_severity(existing.severity, severity)
            existing.technical_notes = summarize_collected_data(collected)
            return existing

        ticket = Ticket(
            customer_id=customer.id,
            conversation_id=conversation.id,
            problem_type=str(problem_type)[:120],
            severity=severity,
            status="Novo",
            technical_notes=summarize_collected_data(collected),
            extra=collected,
        )
        self.db.add(ticket)
        self.db.flush()
        return ticket

    def _get_or_create_conversation(self, payload: ChatMessageIn) -> Conversation:
        if payload.conversation_id:
            return self._get_conversation(payload.conversation_id)

        if payload.external_id:
            existing = self.db.scalar(
                select(Conversation).where(
                    Conversation.channel == payload.channel,
                    Conversation.external_id == payload.external_id,
                    Conversation.status.in_(["open", "limited", "technical_triage", "commercial_triage", "handoff"]),
                )
            )
            if existing:
                return existing

        customer = None
        if payload.customer_id:
            customer = self.db.get(Customer, payload.customer_id)
        if not customer:
            customer = Customer()
            self._merge_payload_customer(customer, payload)
            self.db.add(customer)
            self.db.flush()

        conversation = Conversation(
            customer_id=customer.id,
            channel=payload.channel,
            external_id=payload.external_id,
            status="open",
            collected_data={},
        )
        self.db.add(conversation)
        self.db.flush()
        return conversation

    def _get_conversation(self, conversation_id: str) -> Conversation:
        conversation = self.db.get(Conversation, conversation_id)
        if not conversation:
            raise ValueError("Conversation not found")
        return conversation

    def _merge_payload_customer(self, customer: Customer | None, payload: ChatMessageIn) -> None:
        if not customer or not payload.customer:
            return
        incoming = payload.customer
        for field in ["name", "phone", "email", "city", "state"]:
            value = getattr(incoming, field)
            if value:
                setattr(customer, field, str(value))
        if incoming.document:
            customer.document = encrypt_value(incoming.document)
        if incoming.lgpd_consent:
            customer.lgpd_consent = True
            customer.lgpd_consent_at = customer.lgpd_consent_at or utc_now()

    def _capture_answer_from_previous_question(self, collected: dict, customer: Customer | None, answer: str) -> None:
        key = collected.pop("last_question_key", None)
        if not key or key in {"lgpd_consent", "app_intro"}:
            return

        collected[key] = answer
        if customer:
            if key == "name":
                customer.name = answer
            elif key == "phone":
                customer.phone = answer
            elif key == "email" and "@" in answer:
                customer.email = answer
            elif key == "city":
                customer.city = answer
            elif key == "city_state":
                city, state = self._parse_city_state(answer)
                customer.city = city or customer.city
                customer.state = state or customer.state
            elif key == "document_or_code":
                customer.document = encrypt_value(answer)

    @staticmethod
    def _parse_city_state(value: str) -> tuple[str | None, str | None]:
        cleaned = value.strip()
        state_match = re.search(r"\b([A-Z]{2})\b", cleaned.upper())
        state = state_match.group(1) if state_match else None
        city = re.sub(r"[-/,]?\s*[A-Z]{2}\b", "", cleaned, flags=re.IGNORECASE).strip(" ,-")
        return city or None, state

    @staticmethod
    def _is_affirmative(message: str) -> bool:
        text = normalize(message)
        return text in {"sim", "ok", "claro", "pode", "tudo bem", "autorizo", "concordo"} or "sim" in text

    @staticmethod
    def _is_negative(message: str) -> bool:
        text = normalize(message)
        return text in {"nao", "não", "negativo", "nao autorizo", "prefiro nao"}

    @staticmethod
    def _money_to_float(value: str | None) -> float | None:
        if not value:
            return None
        match = re.search(r"(\d+[\d.,]*)", value)
        if not match:
            return None
        number = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(number)
        except ValueError:
            return None

    @staticmethod
    def _boolean_or_none(value: str | bool | None) -> bool | None:
        if isinstance(value, bool) or value is None:
            return value
        text = normalize(value)
        if any(term in text for term in ["sim", "quero", "tenho interesse"]):
            return True
        if any(term in text for term in ["nao", "sem interesse"]):
            return False
        return None

    @staticmethod
    def _strongest_severity(current: str | None, new: str | None) -> str | None:
        order = {"baixa": 1, "media": 2, "alta": 3}
        if not current:
            return new
        if not new:
            return current
        return current if order.get(current, 0) >= order.get(new, 0) else new
