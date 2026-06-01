import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models import AuditLog, Conversation, Customer, Lead, Proposal, ProposalItem, ProposalPriceItem, User
from app.schemas import (
    ProposalCreate,
    ProposalItemCreate,
    ProposalItemUpdate,
    ProposalPriceItemCreate,
    ProposalPriceItemUpdate,
    ProposalSendRequest,
    ProposalSendResult,
    ProposalUpdate,
)
from app.services.email import EmailService
from app.services.proposal_pdf import ProposalPdfService
from app.services.whatsapp_cloud import WhatsAppCloudService

DEFAULT_PROPOSAL_NOTICE = (
    "Esta proposta foi gerada como rascunho com base nos dados coletados pelo Solis. "
    "Revise valores, condições técnicas e comerciais antes de enviar ao cliente."
)

DEFAULT_ITEMS = [
    (
        "kit_fotovoltaico",
        "Módulos solares, inversor, conectores e componentes principais do sistema.",
    ),
    (
        "materiais_eletricos",
        "Cabos, eletrodutos, disjuntores, DPS, conectores, string box e demais materiais necessários.",
    ),
    (
        "mao_de_obra",
        "Instalação técnica do sistema fotovoltaico por equipe especializada.",
    ),
    ("projeto", "Elaboração do projeto elétrico/fotovoltaico."),
    (
        "homologacao",
        "Processo de solicitação, documentação e acompanhamento da homologação junto à concessionária local.",
    ),
    (
        "estrutura_fixacao",
        "Estruturas, suportes e materiais de fixação dos módulos solares.",
    ),
    (
        "taxas_concessionaria",
        "Custos eventuais com taxas, adequações elétricas ou estruturais, se aplicável.",
    ),
]


class ProposalService:
    def __init__(self, db: Session, actor: User | None = None) -> None:
        self.db = db
        self.actor = actor
        self.pdf_service = ProposalPdfService()
        self.email_service = EmailService()
        self.whatsapp_service = WhatsAppCloudService()

    def list_proposals(self, status: str | None = None, city: str | None = None, customer: str | None = None) -> list[Proposal]:
        statement = select(Proposal).options(selectinload(Proposal.items)).order_by(desc(Proposal.created_at)).limit(300)
        if status:
            statement = statement.where(Proposal.status == status)
        if city:
            statement = statement.where(Proposal.city.ilike(f"%{city}%"))
        if customer:
            statement = statement.where(Proposal.customer_name.ilike(f"%{customer}%"))
        return list(self.db.scalars(statement).all())

    def create_proposal(self, payload: ProposalCreate) -> Proposal:
        data = payload.model_dump(exclude={"items"})
        data["proposal_number"] = data.get("proposal_number") or self._proposal_number()
        proposal = Proposal(**data)
        self.db.add(proposal)
        self.db.flush()
        for index, item_payload in enumerate(payload.items):
            self._add_item_object(proposal, item_payload, index)
        self.recalculate(proposal)
        self._audit("proposal.created", proposal)
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def create_from_lead(self, lead_id: str) -> Proposal:
        lead = self._require(Lead, lead_id, "Lead not found")
        customer = self.db.get(Customer, lead.customer_id) if lead.customer_id else None
        conversation = self.db.get(Conversation, lead.conversation_id) if lead.conversation_id else None
        collected = dict((conversation.collected_data if conversation else {}) or {})
        collected.update(lead.extra or {})
        city, state = self._city_state(customer, collected)
        average_bill = self._float_or_none(lead.average_bill or collected.get("average_bill"))
        power_kwp, generation_kwh = self._estimate_system(average_bill)
        missing = self._missing_lead_data(lead, customer, collected)
        active_price_items = self._active_price_items()
        internal_notes = DEFAULT_PROPOSAL_NOTICE
        if missing:
            internal_notes += f" Dados faltantes: {', '.join(missing)}."
        if active_price_items:
            internal_notes += " Valores carregados da tabela de precos configuravel. Revise antes de enviar."
        else:
            internal_notes += (
                " Nao ha tabela de precos configurada. Os itens foram criados com valores zerados para revisao manual."
            )

        proposal = Proposal(
            customer_id=lead.customer_id,
            lead_id=lead.id,
            conversation_id=lead.conversation_id,
            proposal_number=self._proposal_number(),
            status="draft",
            customer_name=(customer.name if customer else None) or collected.get("name") or "Cliente Solar Soluções",
            customer_phone=(customer.phone if customer else None) or collected.get("phone"),
            customer_email=(customer.email if customer else None) or collected.get("email"),
            city=city,
            state=state,
            property_type=lead.property_type or collected.get("property_type"),
            average_bill=average_bill,
            estimated_system_power_kwp=power_kwp,
            estimated_monthly_generation_kwh=generation_kwh,
            estimated_savings_percentage=85 if average_bill else None,
            validity_days=7,
            notes=DEFAULT_PROPOSAL_NOTICE,
            internal_notes=internal_notes,
            discount=0,
            payment_conditions="A definir após revisão comercial.",
        )
        self.db.add(proposal)
        self.db.flush()
        if active_price_items:
            self._apply_price_items_to_proposal(proposal, active_price_items)
        else:
            for index, (category, description) in enumerate(DEFAULT_ITEMS):
                self._add_item_object(
                    proposal,
                    ProposalItemCreate(
                        category=category,
                        description=description,
                        quantity=1,
                    unit="serviço" if category in {"mao_de_obra", "projeto", "homologacao"} else "un",
                        unit_price=0,
                        sort_order=index,
                    ),
                    index,
                )
        self.recalculate(proposal)
        self._audit("proposal.created", proposal, {"origin": "lead", "lead_id": lead.id})
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def get_proposal(self, proposal_id: str) -> Proposal:
        proposal = self.db.scalar(
            select(Proposal).where(Proposal.id == proposal_id).options(selectinload(Proposal.items))
        )
        if not proposal:
            raise ValueError("Proposal not found")
        return proposal

    def update_proposal(self, proposal_id: str, payload: ProposalUpdate) -> Proposal:
        proposal = self.get_proposal(proposal_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(proposal, field, value)
        self.recalculate(proposal)
        self._audit("proposal.updated", proposal)
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def update_status(self, proposal_id: str, status: str) -> Proposal:
        proposal = self.get_proposal(proposal_id)
        proposal.status = status
        self._audit("proposal.status_changed", proposal, {"status": status})
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def add_item(self, proposal_id: str, payload: ProposalItemCreate) -> Proposal:
        proposal = self.get_proposal(proposal_id)
        self._add_item_object(proposal, payload, len(proposal.items or []))
        self.recalculate(proposal)
        self._audit("proposal.updated", proposal, {"item_added": payload.category})
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def update_item(self, proposal_id: str, item_id: str, payload: ProposalItemUpdate) -> Proposal:
        proposal = self.get_proposal(proposal_id)
        item = self._find_item(proposal, item_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        item.total_price = self._line_total(item.quantity, item.unit_price)
        self.recalculate(proposal)
        self._audit("proposal.updated", proposal, {"item_updated": item.id})
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def delete_item(self, proposal_id: str, item_id: str) -> Proposal:
        proposal = self.get_proposal(proposal_id)
        item = self._find_item(proposal, item_id)
        self.db.delete(item)
        proposal.items = [proposal_item for proposal_item in proposal.items if proposal_item.id != item_id]
        self.recalculate(proposal)
        self._audit("proposal.updated", proposal, {"item_deleted": item_id})
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def generate_pdf(self, proposal_id: str) -> Proposal:
        proposal = self.get_proposal(proposal_id)
        self.recalculate(proposal)
        proposal.pdf_url = self.pdf_service.generate(proposal)
        if proposal.status in {"draft", "under_review", "approved"}:
            proposal.status = "ready_to_send"
        self._audit("proposal.pdf_generated", proposal, {"pdf_url": proposal.pdf_url})
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def send(self, proposal_id: str, payload: ProposalSendRequest) -> ProposalSendResult:
        proposal = self.get_proposal(proposal_id)
        if not proposal.pdf_url:
            proposal.pdf_url = self.pdf_service.generate(proposal)
        if proposal.status in {"draft", "under_review", "approved"}:
            proposal.status = "ready_to_send"

        if payload.channel == "manual":
            if payload.mark_as_sent:
                proposal.status = "sent"
                self._audit("proposal.sent", proposal, {"channel": payload.channel, "manual_confirmation": True})
            else:
                self._audit("proposal.send_requested", proposal, {"channel": payload.channel})
            self.db.commit()
            return ProposalSendResult(
                status="sent" if payload.mark_as_sent else "ready",
                channel=payload.channel,
                message=(
                    "PDF gerado e proposta marcada como enviada manualmente."
                    if payload.mark_as_sent
                    else "PDF gerado e pronto para envio manual. A proposta nao foi marcada como enviada."
                ),
                pdf_url=proposal.pdf_url,
                sent_at=datetime.now(timezone.utc) if payload.mark_as_sent else None,
            )

        if payload.channel == "secure_link":
            public_url = self._public_pdf_url(proposal)
            if not public_url:
                self._audit("proposal.send_failed", proposal, {"channel": payload.channel, "reason": "missing_public_pdf_url"})
                self.db.commit()
                return ProposalSendResult(
                    status="error",
                    channel=payload.channel,
                    message="PDF gerado, mas nao ha URL publica segura configurada para envio.",
                    pdf_url=proposal.pdf_url,
                )
            self._audit("proposal.secure_link_generated", proposal, {"channel": payload.channel})
            self.db.commit()
            return ProposalSendResult(
                status="ready",
                channel=payload.channel,
                message="Link seguro da proposta gerado para revisao e compartilhamento humano.",
                pdf_url=public_url,
                delivery_reference=public_url,
            )

        if payload.channel == "whatsapp":
            return self._send_whatsapp(proposal, payload)
        if payload.channel == "email":
            return self._send_email(proposal, payload)
        raise ValueError("Unsupported proposal send channel")

    def apply_price_table(self, proposal_id: str) -> Proposal:
        proposal = self.get_proposal(proposal_id)
        active_price_items = self._active_price_items()
        if not active_price_items:
            raise ValueError("No active price table items configured")
        for item in list(proposal.items or []):
            self.db.delete(item)
        proposal.items = []
        self._apply_price_items_to_proposal(proposal, active_price_items)
        proposal.internal_notes = self._append_note(
            proposal.internal_notes,
            "Tabela de precos aplicada. Revise valores e condicoes comerciais antes de enviar.",
        )
        self.recalculate(proposal)
        self._audit("proposal.price_table_applied", proposal, {"items": len(active_price_items)})
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def list_price_items(self, active: bool | None = None) -> list[ProposalPriceItem]:
        statement = select(ProposalPriceItem).order_by(ProposalPriceItem.sort_order, ProposalPriceItem.category)
        if active is not None:
            statement = statement.where(ProposalPriceItem.active == active)
        return list(self.db.scalars(statement).all())

    def create_price_item(self, payload: ProposalPriceItemCreate) -> ProposalPriceItem:
        item = ProposalPriceItem(**payload.model_dump())
        self.db.add(item)
        self.db.flush()
        self._audit_price_item("proposal_price_item.created", item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_price_item(self, item_id: str, payload: ProposalPriceItemUpdate) -> ProposalPriceItem:
        item = self._require(ProposalPriceItem, item_id, "Proposal price item not found")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        self._audit_price_item("proposal_price_item.updated", item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def set_price_item_active(self, item_id: str, active: bool) -> ProposalPriceItem:
        item = self._require(ProposalPriceItem, item_id, "Proposal price item not found")
        item.active = active
        self._audit_price_item("proposal_price_item.active_changed", item, {"active": active})
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_price_item(self, item_id: str) -> None:
        item = self._require(ProposalPriceItem, item_id, "Proposal price item not found")
        self._audit_price_item("proposal_price_item.deleted", item)
        self.db.delete(item)
        self.db.commit()

    def recalculate(self, proposal: Proposal) -> None:
        subtotal = 0.0
        for index, item in enumerate(proposal.items or []):
            item.sort_order = item.sort_order if item.sort_order is not None else index
            item.total_price = self._line_total(item.quantity, item.unit_price)
            subtotal += float(item.total_price or 0)
        proposal.subtotal = round(subtotal, 2)
        proposal.discount = max(float(proposal.discount or 0), 0)
        proposal.total_amount = max(round(proposal.subtotal - proposal.discount, 2), 0)

    def _add_item_object(self, proposal: Proposal, payload: ProposalItemCreate, fallback_order: int) -> ProposalItem:
        item = ProposalItem(
            proposal_id=proposal.id,
            category=payload.category,
            description=payload.description,
            quantity=payload.quantity,
            unit=payload.unit,
            unit_price=payload.unit_price,
            total_price=self._line_total(payload.quantity, payload.unit_price),
            editable=payload.editable,
            sort_order=payload.sort_order if payload.sort_order is not None else fallback_order,
        )
        self.db.add(item)
        proposal.items = [*(proposal.items or []), item]
        return item

    def _apply_price_items_to_proposal(self, proposal: Proposal, price_items: list[ProposalPriceItem]) -> None:
        for index, price_item in enumerate(price_items):
            self._add_item_object(
                proposal,
                ProposalItemCreate(
                    category=price_item.category,
                    description=price_item.description,
                    quantity=float(price_item.default_quantity or 0),
                    unit=price_item.default_unit,
                    unit_price=float(price_item.default_unit_price or 0),
                    sort_order=price_item.sort_order if price_item.sort_order is not None else index,
                ),
                index,
            )

    def _audit(self, action: str, proposal: Proposal, details: dict | None = None) -> None:
        self.db.add(
            AuditLog(
                actor_user_id=self.actor.id if self.actor else None,
                action=action,
                entity_type="proposal",
                entity_id=proposal.id,
                details={"proposal_number": proposal.proposal_number, **(details or {})},
            )
        )

    def _audit_price_item(self, action: str, item: ProposalPriceItem, details: dict | None = None) -> None:
        self.db.add(
            AuditLog(
                actor_user_id=self.actor.id if self.actor else None,
                action=action,
                entity_type="proposal_price_item",
                entity_id=item.id,
                details={"category": item.category, **(details or {})},
            )
        )

    def _send_whatsapp(self, proposal: Proposal, payload: ProposalSendRequest) -> ProposalSendResult:
        public_url = self._public_pdf_url(proposal)
        if settings.app_env.strip().lower() == "production" and not public_url:
            self._audit("proposal.send_failed", proposal, {"channel": payload.channel, "reason": "missing_public_pdf_url"})
            self.db.commit()
            return ProposalSendResult(
                status="error",
                channel=payload.channel,
                message="PDF gerado, mas nao ha URL publica segura configurada para envio.",
                pdf_url=proposal.pdf_url,
            )

        recipient = payload.recipient_phone or proposal.customer_phone
        if not recipient:
            self._audit("proposal.send_failed", proposal, {"channel": payload.channel, "reason": "missing_recipient_phone"})
            self.db.commit()
            return ProposalSendResult(
                status="error",
                channel=payload.channel,
                message="Informe um telefone do destinatario para enviar por WhatsApp.",
                pdf_url=proposal.pdf_url,
            )

        message = payload.message or self._default_proposal_message(proposal, public_url)
        if settings.app_env.strip().lower() != "production":
            self._audit("proposal.whatsapp_sent", proposal, {"channel": payload.channel, "simulated": True})
            self.db.commit()
            return ProposalSendResult(
                status="simulated",
                channel=payload.channel,
                message="Envio por WhatsApp simulado em development. Em producao, use template aprovado quando necessario.",
                pdf_url=public_url or proposal.pdf_url,
                delivery_reference="development-simulation",
            )

        if payload.use_template and payload.template_name:
            result = self.whatsapp_service.send_template_message(recipient, payload.template_name)
        else:
            result = self.whatsapp_service.send_text_message(recipient, message)
        if result.get("status") in {"error", "skipped"}:
            self._audit("proposal.send_failed", proposal, {"channel": payload.channel, "reason": result.get("reason", "send_failed")})
            self.db.commit()
            return ProposalSendResult(
                status="error",
                channel=payload.channel,
                message="Nao foi possivel enviar a proposta pelo WhatsApp. Verifique as configuracoes oficiais da Meta.",
                pdf_url=public_url or proposal.pdf_url,
            )

        proposal.status = "sent"
        self._audit("proposal.whatsapp_sent", proposal, {"channel": payload.channel})
        self._audit("proposal.sent", proposal, {"channel": payload.channel})
        self.db.commit()
        return ProposalSendResult(
            status="sent",
            channel=payload.channel,
            message="Proposta enviada pelo WhatsApp.",
            pdf_url=public_url or proposal.pdf_url,
            delivery_reference=str(result.get("messages", result.get("id", "whatsapp"))),
            sent_at=datetime.now(timezone.utc),
        )

    def _send_email(self, proposal: Proposal, payload: ProposalSendRequest) -> ProposalSendResult:
        recipient = payload.recipient_email or proposal.customer_email
        if not recipient:
            self._audit("proposal.send_failed", proposal, {"channel": payload.channel, "reason": "missing_recipient_email"})
            self.db.commit()
            return ProposalSendResult(
                status="error",
                channel=payload.channel,
                message="Informe um e-mail do destinatario para enviar a proposta.",
                pdf_url=proposal.pdf_url,
            )

        public_url = self._public_pdf_url(proposal)
        body = payload.message or self._default_proposal_email_body(proposal, public_url)
        if settings.app_env.strip().lower() != "production":
            self._audit("proposal.email_sent", proposal, {"channel": payload.channel, "simulated": True})
            self.db.commit()
            return ProposalSendResult(
                status="simulated",
                channel=payload.channel,
                message="Envio por e-mail simulado em development. Configure SMTP para envio real em producao.",
                pdf_url=public_url or proposal.pdf_url,
                delivery_reference="development-simulation",
            )

        result = self.email_service.send_proposal(
            recipient_email=str(recipient),
            subject=f"Proposta Solar Solucoes - {proposal.proposal_number}",
            body=body,
            attachment_path=proposal.pdf_url if proposal.pdf_url and Path(proposal.pdf_url).exists() else None,
        )
        if result.get("status") in {"error", "skipped"}:
            self._audit("proposal.send_failed", proposal, {"channel": payload.channel, "reason": result.get("reason", "send_failed")})
            self.db.commit()
            return ProposalSendResult(
                status="error",
                channel=payload.channel,
                message="Nao foi possivel enviar a proposta por e-mail. Verifique as configuracoes SMTP.",
                pdf_url=public_url or proposal.pdf_url,
            )

        proposal.status = "sent"
        self._audit("proposal.email_sent", proposal, {"channel": payload.channel})
        self._audit("proposal.sent", proposal, {"channel": payload.channel})
        self.db.commit()
        return ProposalSendResult(
            status="sent",
            channel=payload.channel,
            message="Proposta enviada por e-mail.",
            pdf_url=public_url or proposal.pdf_url,
            delivery_reference=result.get("reference"),
            sent_at=datetime.now(timezone.utc),
        )

    def _public_pdf_url(self, proposal: Proposal) -> str | None:
        if not proposal.pdf_url or not settings.proposal_public_base_url:
            return None
        return f"{str(settings.proposal_public_base_url).rstrip('/')}/{Path(proposal.pdf_url).name}"

    def _active_price_items(self) -> list[ProposalPriceItem]:
        statement = (
            select(ProposalPriceItem)
            .where(ProposalPriceItem.active == True)  # noqa: E712
            .order_by(ProposalPriceItem.sort_order, ProposalPriceItem.category)
        )
        return list(self.db.scalars(statement).all())

    @staticmethod
    def _append_note(current: str | None, note: str) -> str:
        if not current:
            return note
        return f"{current}\n{note}"

    @staticmethod
    def _default_proposal_message(proposal: Proposal, public_url: str | None) -> str:
        link_text = f"\n\nLink seguro: {public_url}" if public_url else ""
        return (
            f"Ola, {proposal.customer_name}. A equipe da Solar Solucoes preparou a proposta "
            f"{proposal.proposal_number} para sua avaliacao.{link_text}\n\n"
            "Os valores e condicoes estao sujeitos a validacao tecnica e comercial."
        )

    @staticmethod
    def _default_proposal_email_body(proposal: Proposal, public_url: str | None) -> str:
        link_text = f"\n\nLink seguro da proposta: {public_url}" if public_url else ""
        return (
            f"Ola, {proposal.customer_name}.\n\n"
            f"Segue a proposta {proposal.proposal_number} da Solar Solucoes para avaliacao."
            f"{link_text}\n\n"
            "Os valores, prazos, economia estimada e condicoes dependem de validacao tecnica e comercial.\n\n"
            "Atenciosamente,\nSolar Solucoes"
        )

    def _find_item(self, proposal: Proposal, item_id: str) -> ProposalItem:
        for item in proposal.items or []:
            if item.id == item_id:
                return item
        raise ValueError("Proposal item not found")

    @staticmethod
    def _proposal_number() -> str:
        now = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"SOL-{now}-{uuid.uuid4().hex[:6].upper()}"

    @staticmethod
    def _line_total(quantity: object, unit_price: object) -> float:
        return round(max(float(quantity or 0), 0) * max(float(unit_price or 0), 0), 2)

    @staticmethod
    def _estimate_system(average_bill: float | None) -> tuple[float | None, float | None]:
        if not average_bill:
            return None, None
        monthly_generation = max(round((average_bill * 0.85) / 0.95, 2), 0)
        power_kwp = round(monthly_generation / 135, 3)
        return power_kwp, monthly_generation

    @staticmethod
    def _float_or_none(value: object) -> float | None:
        if value is None or value == "":
            return None
        if isinstance(value, str):
            import re

            match = re.search(r"(\d+[\d.,]*)", value)
            if not match:
                return None
            value = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _city_state(customer: Customer | None, collected: dict) -> tuple[str | None, str | None]:
        city = customer.city if customer else None
        state = customer.state if customer else None
        raw = collected.get("city_state") or collected.get("city")
        if raw and not city:
            text = str(raw).strip()
            parts = text.rsplit(" ", 1)
            city = parts[0] if parts else text
            if len(parts) == 2 and len(parts[1]) == 2:
                state = state or parts[1].upper()
        return city or collected.get("city"), state or collected.get("state")

    @staticmethod
    def _missing_lead_data(lead: Lead, customer: Customer | None, collected: dict) -> list[str]:
        missing = []
        if not (customer and customer.name) and not collected.get("name"):
            missing.append("nome do cliente")
        if not (customer and customer.phone) and not collected.get("phone"):
            missing.append("telefone")
        if not lead.average_bill and not collected.get("average_bill"):
            missing.append("conta média")
        if not lead.property_type and not collected.get("property_type"):
            missing.append("tipo de imóvel")
        if not lead.utility_company and not collected.get("utility_company"):
            missing.append("distribuidora")
        return missing

    def _require(self, model, item_id: str, message: str):
        item = self.db.get(model, item_id)
        if not item:
            raise ValueError(message)
        return item
