import uuid
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models import (
    AuditLog,
    CompanySettings,
    Conversation,
    Customer,
    Lead,
    Proposal,
    ProposalCustomerResponse,
    ProposalEvent,
    ProposalFollowUp,
    ProposalItem,
    ProposalKit,
    ProposalPriceItem,
    ProposalShareLink,
    User,
)
from app.schemas import (
    CompanySettingsIn,
    ProposalCreate,
    ProposalCustomerResponseIn,
    ProposalFollowUpCreate,
    ProposalItemCreate,
    ProposalItemUpdate,
    ProposalPriceItemCreate,
    ProposalPriceItemUpdate,
    ProposalShareLinkCreate,
    ProposalSendRequest,
    ProposalSendResult,
    ProposalUpdate,
)
from app.services.email import EmailService
from app.services.proposal_kits import ProposalKitService
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
        statement = (
            select(Proposal)
            .options(
                selectinload(Proposal.items),
                selectinload(Proposal.share_links),
                selectinload(Proposal.events),
                selectinload(Proposal.followups),
                selectinload(Proposal.customer_responses),
                selectinload(Proposal.recommended_kit),
            )
            .order_by(desc(Proposal.created_at))
            .limit(300)
        )
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
        self._record_event(proposal, "proposal.created")
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
        average_consumption_kwh = self._float_or_none(
            collected.get("average_consumption_kwh") or collected.get("current_consumption_kwh")
        )
        if average_consumption_kwh:
            generation_kwh = round(average_consumption_kwh, 2)
            power_kwp = round(generation_kwh / 135, 3)
        else:
            power_kwp, generation_kwh = self._estimate_system(average_bill)
        missing = self._missing_lead_data(lead, customer, collected)
        active_price_items = self._active_price_items()
        kit_selection = ProposalKitService(self.db).simulate_selection(
            average_bill=average_bill,
            estimated_monthly_generation_kwh=generation_kwh,
            estimated_power_kwp=power_kwp,
        )
        selected_kit = kit_selection.selected_kit
        proposal_power_kwp = float(selected_kit.suggested_power_kwp) if selected_kit else power_kwp
        proposal_generation_kwh = (
            float(selected_kit.estimated_monthly_generation_kwh)
            if selected_kit and selected_kit.estimated_monthly_generation_kwh is not None
            else generation_kwh
        )
        company_settings = self.get_company_settings()
        internal_notes = DEFAULT_PROPOSAL_NOTICE
        if missing:
            internal_notes += f" Dados faltantes: {', '.join(missing)}."
        if selected_kit:
            internal_notes += (
                " Kit recomendado automaticamente com base na conta media, consumo informado ou leitura da conta de energia. "
                "Revise dimensionamento, telhado, concessionaria, padrao de entrada, sombreamento, estrutura e condicoes comerciais antes de enviar."
            )
            if kit_selection.selection_reason:
                internal_notes += f" Motivo da selecao: {kit_selection.selection_reason}"
        if average_consumption_kwh:
            internal_notes += f" Consumo medio usado no pre-dimensionamento: {average_consumption_kwh:.0f} kWh/mes."
            average_source = str(collected.get("average_source") or "")
            history_months = self._float_or_none(collected.get("history_months_detected"))
            if average_source in {"history_12_months", "history_partial"}:
                months_text = f" com {int(history_months)} meses detectados" if history_months else ""
                internal_notes += f" Pre-dimensionamento baseado no historico extraido da conta de energia{months_text}; validar no projeto tecnico final."
            elif average_source == "current_consumption_only":
                internal_notes += " Historico nao foi identificado; consumo medio veio do consumo atual da fatura e deve ser revisado."
        elif active_price_items:
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
            estimated_system_power_kwp=proposal_power_kwp,
            estimated_monthly_generation_kwh=proposal_generation_kwh,
            estimated_savings_percentage=85 if average_bill else None,
            recommended_kit_id=selected_kit.id if selected_kit else None,
            recommended_kit_name=selected_kit.name if selected_kit else None,
            kit_selection_reason=kit_selection.selection_reason if selected_kit else None,
            validity_days=company_settings.default_proposal_validity_days,
            notes=company_settings.default_proposal_notes or DEFAULT_PROPOSAL_NOTICE,
            internal_notes=internal_notes,
            discount=0,
            payment_conditions=company_settings.default_payment_conditions or "A definir apos revisao comercial.",
        )
        self.db.add(proposal)
        self.db.flush()
        if selected_kit:
            self._apply_kit_to_proposal(proposal, selected_kit)
            self._apply_optional_price_items_to_proposal(proposal, active_price_items)
        elif active_price_items:
            self._apply_price_items_to_proposal(proposal, active_price_items)
        else:
            for index, (category, description) in enumerate(DEFAULT_ITEMS):
                self._add_item_object(
                    proposal,
                    ProposalItemCreate(
                        category=category,
                        description=description,
                        quantity=1,
                        unit="servico" if category in {"mao_de_obra", "projeto", "homologacao"} else "un",
                        unit_price=0,
                        sort_order=index,
                    ),
                    index,
                )
        self.recalculate(proposal)
        audit_details = {"origin": "lead", "lead_id": lead.id}
        if selected_kit:
            audit_details.update({"recommended_kit_id": selected_kit.id, "recommended_kit_name": selected_kit.name})
        self._audit("proposal.created", proposal, audit_details)
        self._record_event(proposal, "proposal.created", details=audit_details)
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def get_proposal(self, proposal_id: str) -> Proposal:
        proposal = self.db.scalar(
            select(Proposal)
            .where(Proposal.id == proposal_id)
            .options(
                selectinload(Proposal.items),
                selectinload(Proposal.share_links),
                selectinload(Proposal.events),
                selectinload(Proposal.followups),
                selectinload(Proposal.customer_responses),
                selectinload(Proposal.recommended_kit),
            )
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
        self._record_event(proposal, "proposal.updated")
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def update_status(self, proposal_id: str, status: str) -> Proposal:
        proposal = self.get_proposal(proposal_id)
        proposal.status = status
        self._audit("proposal.status_changed", proposal, {"status": status})
        self._record_event(proposal, "proposal.updated", details={"status": status})
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
        proposal.pdf_url = self.pdf_service.generate(proposal, self.get_company_settings())
        if proposal.status in {"draft", "under_review", "approved"}:
            proposal.status = "ready_to_send"
        self._audit("proposal.pdf_generated", proposal, {"pdf_url": proposal.pdf_url})
        self._record_event(proposal, "proposal.pdf_generated")
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def send(self, proposal_id: str, payload: ProposalSendRequest) -> ProposalSendResult:
        proposal = self.get_proposal(proposal_id)
        if not proposal.pdf_url:
            proposal.pdf_url = self.pdf_service.generate(proposal, self.get_company_settings())
        if proposal.status in {"draft", "under_review", "approved"}:
            proposal.status = "ready_to_send"

        if payload.channel == "manual":
            if payload.mark_as_sent:
                proposal.status = "sent"
                self._audit("proposal.sent", proposal, {"channel": payload.channel, "manual_confirmation": True})
                self._record_event(proposal, "proposal.sent", channel=payload.channel, details={"manual_confirmation": True})
                self._create_default_followups(proposal, payload.channel)
            else:
                self._audit("proposal.send_requested", proposal, {"channel": payload.channel})
                self._record_event(proposal, "proposal.send_requested", channel=payload.channel)
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
            link = self._ensure_share_link(proposal)
            public_url = self.public_url_for_share_link(link)
            self._audit("proposal.secure_link_generated", proposal, {"channel": payload.channel})
            self._record_event(proposal, "proposal.secure_link_generated", channel=payload.channel, details={"share_link_id": link.id})
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

    def create_share_link(self, proposal_id: str, payload: ProposalShareLinkCreate | None = None) -> ProposalShareLink:
        proposal = self.get_proposal(proposal_id)
        payload = payload or ProposalShareLinkCreate()
        link = ProposalShareLink(
            proposal_id=proposal.id,
            token=self._secure_token(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days),
            views_count=0,
            created_by=self.actor.id if self.actor else None,
        )
        self.db.add(link)
        self.db.flush()
        self._audit("proposal.share_link_created", proposal, {"share_link_id": link.id})
        self._record_event(proposal, "proposal.share_link_created", details={"share_link_id": link.id})
        self.db.commit()
        self.db.refresh(link)
        return link

    def list_share_links(self, proposal_id: str) -> list[ProposalShareLink]:
        self._require(Proposal, proposal_id, "Proposal not found")
        statement = (
            select(ProposalShareLink)
            .where(ProposalShareLink.proposal_id == proposal_id)
            .order_by(desc(ProposalShareLink.created_at))
        )
        return list(self.db.scalars(statement).all())

    def revoke_share_link(self, link_id: str) -> ProposalShareLink:
        link = self._require(ProposalShareLink, link_id, "Proposal share link not found")
        if not link.revoked_at:
            link.revoked_at = datetime.now(timezone.utc)
            proposal = self._require(Proposal, link.proposal_id, "Proposal not found")
            self._audit("proposal.share_link_revoked", proposal, {"share_link_id": link.id})
            self._record_event(proposal, "proposal.share_link_revoked", details={"share_link_id": link.id})
        self.db.commit()
        self.db.refresh(link)
        return link

    def get_public_proposal(self, token: str) -> tuple[Proposal, ProposalShareLink, CompanySettings]:
        link = self._valid_share_link(token)
        proposal = self.get_proposal(link.proposal_id)
        now = datetime.now(timezone.utc)
        link.views_count = int(link.views_count or 0) + 1
        link.last_viewed_at = now
        self._record_event(proposal, "proposal.share_link_viewed", details={"share_link_id": link.id})
        self._record_event(proposal, "proposal.viewed", details={"share_link_id": link.id})
        self.db.commit()
        self.db.refresh(link)
        return proposal, link, self.get_company_settings()

    def register_pdf_download(self, token: str) -> Proposal:
        link = self._valid_share_link(token)
        proposal = self.get_proposal(link.proposal_id)
        if not proposal.pdf_url:
            proposal.pdf_url = self.pdf_service.generate(proposal, self.get_company_settings())
        self._record_event(proposal, "proposal.downloaded", details={"share_link_id": link.id})
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def register_customer_response(
        self,
        token: str,
        payload: ProposalCustomerResponseIn,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ProposalCustomerResponse:
        link = self._valid_share_link(token)
        proposal = self.get_proposal(link.proposal_id)
        response = ProposalCustomerResponse(
            proposal_id=proposal.id,
            share_link_id=link.id,
            response_type=payload.response_type,
            customer_name=payload.customer_name,
            customer_email=str(payload.customer_email) if payload.customer_email else None,
            customer_phone=payload.customer_phone,
            message=payload.message,
            ip_address=ip_address,
            user_agent=(user_agent or "")[:500] or None,
        )
        self.db.add(response)
        if payload.response_type == "accepted":
            proposal.status = "accepted"
            event_type = "proposal.accepted"
            message = "Obrigado! A equipe da Solar Solucoes recebeu sua confirmacao e entrara em contato para os proximos passos."
        elif payload.response_type == "rejected":
            proposal.status = "rejected"
            event_type = "proposal.rejected"
            message = "Obrigado pelo retorno. A equipe da Solar Solucoes registrou sua resposta."
        elif payload.response_type == "request_changes":
            if proposal.status == "sent":
                proposal.status = "under_review"
            event_type = "proposal.change_requested"
            message = "Recebemos sua solicitacao de ajuste. A equipe comercial vai revisar a proposta."
        elif payload.response_type == "talk_to_consultant":
            event_type = "proposal.customer_interested"
            message = "Recebemos seu pedido para falar com um consultor. A equipe vai entrar em contato."
        else:
            event_type = "proposal.customer_interested"
            message = "Obrigado pelo interesse. A equipe da Solar Solucoes recebeu sua resposta."
        self._record_event(
            proposal,
            event_type,
            details={"share_link_id": link.id, "response_type": payload.response_type},
        )
        self._audit(event_type, proposal, {"share_link_id": link.id, "response_type": payload.response_type})
        self.db.commit()
        self.db.refresh(response)
        response.confirmation_message = message  # type: ignore[attr-defined]
        return response

    def list_followups(self, status: str | None = None) -> list[ProposalFollowUp]:
        statement = select(ProposalFollowUp).order_by(ProposalFollowUp.due_at)
        if status:
            statement = statement.where(ProposalFollowUp.status == status)
        return list(self.db.scalars(statement).all())

    def create_followup(self, proposal_id: str, payload: ProposalFollowUpCreate) -> ProposalFollowUp:
        proposal = self.get_proposal(proposal_id)
        followup = ProposalFollowUp(
            proposal_id=proposal.id,
            due_at=payload.due_at,
            status="pending",
            channel=payload.channel,
            note=payload.note,
            assigned_to=payload.assigned_to,
        )
        self.db.add(followup)
        self.db.flush()
        self._record_event(proposal, "proposal.followup_created", channel=payload.channel, details={"followup_id": followup.id})
        self._audit("proposal.followup_created", proposal, {"followup_id": followup.id, "channel": payload.channel})
        self.db.commit()
        self.db.refresh(followup)
        return followup

    def complete_followup(self, followup_id: str) -> ProposalFollowUp:
        followup = self._require(ProposalFollowUp, followup_id, "Proposal follow-up not found")
        followup.status = "completed"
        followup.completed_at = datetime.now(timezone.utc)
        proposal = self._require(Proposal, followup.proposal_id, "Proposal not found")
        self._record_event(proposal, "proposal.followup_completed", channel=followup.channel, details={"followup_id": followup.id})
        self.db.commit()
        self.db.refresh(followup)
        return followup

    def cancel_followup(self, followup_id: str) -> ProposalFollowUp:
        followup = self._require(ProposalFollowUp, followup_id, "Proposal follow-up not found")
        followup.status = "canceled"
        proposal = self._require(Proposal, followup.proposal_id, "Proposal not found")
        self._record_event(proposal, "proposal.followup_canceled", channel=followup.channel, details={"followup_id": followup.id})
        self.db.commit()
        self.db.refresh(followup)
        return followup

    def get_company_settings(self) -> CompanySettings:
        company = self.db.scalar(select(CompanySettings).order_by(CompanySettings.created_at).limit(1))
        if company:
            return company
        company = CompanySettings(
            company_name=settings.company_name,
            company_phone=settings.company_phone,
            company_email=settings.company_email,
            company_website=str(settings.company_website) if settings.company_website else None,
            company_address=settings.company_address,
            company_logo_url=settings.company_logo_path,
            primary_color=settings.company_primary_color,
            secondary_color=settings.company_secondary_color,
            default_payment_conditions="A definir apos revisao comercial.",
            default_proposal_validity_days=7,
            default_proposal_notes=DEFAULT_PROPOSAL_NOTICE,
        )
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        return company

    def update_company_settings(self, payload: CompanySettingsIn) -> CompanySettings:
        company = self.get_company_settings()
        for field, value in payload.model_dump().items():
            setattr(company, field, value)
        self.db.add(
            AuditLog(
                actor_user_id=self.actor.id if self.actor else None,
                action="company_settings.updated",
                entity_type="company_settings",
                entity_id=company.id,
                details={},
            )
        )
        self.db.commit()
        self.db.refresh(company)
        return company

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

    def _apply_kit_to_proposal(self, proposal: Proposal, kit: ProposalKit) -> None:
        kit_items = list(kit.items or [])
        if kit_items:
            for index, kit_item in enumerate(kit_items):
                self._add_item_object(
                    proposal,
                    ProposalItemCreate(
                        category=kit_item.category,
                        description=kit_item.description,
                        quantity=float(kit_item.quantity or 0),
                        unit=kit_item.unit,
                        unit_price=float(kit_item.unit_price or 0),
                        sort_order=kit_item.sort_order if kit_item.sort_order is not None else index,
                    ),
                    index,
                )
            return

        description = kit.name
        if kit.description:
            description = f"{kit.name} - {kit.description}"
        self._add_item_object(
            proposal,
            ProposalItemCreate(
                category="kit_fotovoltaico",
                description=description,
                quantity=1,
                unit="kit",
                unit_price=float(kit.base_price or 0),
                sort_order=0,
            ),
            0,
        )

    def _apply_optional_price_items_to_proposal(self, proposal: Proposal, price_items: list[ProposalPriceItem]) -> None:
        optional_categories = {"projeto", "homologacao", "mao_de_obra", "deslocamento", "monitoramento"}
        existing_categories = {item.category for item in (proposal.items or [])}
        start_index = len(proposal.items or [])
        for price_item in price_items:
            if price_item.category not in optional_categories or price_item.category in existing_categories:
                continue
            self._add_item_object(
                proposal,
                ProposalItemCreate(
                    category=price_item.category,
                    description=price_item.description,
                    quantity=float(price_item.default_quantity or 0),
                    unit=price_item.default_unit,
                    unit_price=float(price_item.default_unit_price or 0),
                    sort_order=start_index,
                ),
                start_index,
            )
            existing_categories.add(price_item.category)
            start_index += 1

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

    def _record_event(
        self,
        proposal: Proposal,
        event_type: str,
        channel: str | None = None,
        details: dict | None = None,
    ) -> None:
        self.db.add(
            ProposalEvent(
                proposal_id=proposal.id,
                event_type=event_type,
                channel=channel,
                details=details or {},
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

    def _valid_share_link(self, token: str) -> ProposalShareLink:
        link = self.db.scalar(select(ProposalShareLink).where(ProposalShareLink.token == token))
        if not link:
            raise ValueError("Proposal link not found")
        now = datetime.now(timezone.utc)
        expires_at = self._as_aware(link.expires_at)
        if link.revoked_at:
            raise ValueError("Proposal link revoked")
        if expires_at < now:
            raise ValueError("Proposal link expired")
        return link

    def _active_share_link(self, proposal: Proposal) -> ProposalShareLink | None:
        now = datetime.now(timezone.utc)
        statement = (
            select(ProposalShareLink)
            .where(
                ProposalShareLink.proposal_id == proposal.id,
                ProposalShareLink.revoked_at.is_(None),
                ProposalShareLink.expires_at > now,
            )
            .order_by(desc(ProposalShareLink.created_at))
        )
        return self.db.scalar(statement)

    def _ensure_share_link(self, proposal: Proposal) -> ProposalShareLink:
        link = self._active_share_link(proposal)
        if link:
            return link
        link = ProposalShareLink(
            proposal_id=proposal.id,
            token=self._secure_token(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=15),
            views_count=0,
            created_by=self.actor.id if self.actor else None,
        )
        self.db.add(link)
        self.db.flush()
        self._record_event(proposal, "proposal.share_link_created", details={"share_link_id": link.id, "auto": True})
        self._audit("proposal.share_link_created", proposal, {"share_link_id": link.id, "auto": True})
        return link

    def _create_default_followups(self, proposal: Proposal, channel: str) -> None:
        existing_pending = [
            followup
            for followup in (proposal.followups or [])
            if followup.status == "pending" and followup.channel == channel
        ]
        if existing_pending:
            return
        now = datetime.now(timezone.utc)
        for days, label in [(1, "Retorno comercial em 24h"), (3, "Segundo retorno comercial em 3 dias")]:
            followup = ProposalFollowUp(
                proposal_id=proposal.id,
                due_at=now + timedelta(days=days),
                status="pending",
                channel=channel,
                note=label,
                assigned_to=self.actor.id if self.actor else None,
            )
            self.db.add(followup)
            self.db.flush()
            self._record_event(proposal, "proposal.followup_created", channel=channel, details={"followup_id": followup.id})

    def public_url_for_share_link(self, link: ProposalShareLink) -> str:
        base = str(settings.frontend_origins[0] if settings.frontend_origins else settings.api_base_url).rstrip("/")
        return f"{base}/proposta/{link.token}"

    @staticmethod
    def _secure_token() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def _as_aware(value: datetime) -> datetime:
        if value.tzinfo:
            return value
        return value.replace(tzinfo=timezone.utc)

    def _send_whatsapp(self, proposal: Proposal, payload: ProposalSendRequest) -> ProposalSendResult:
        link = self._ensure_share_link(proposal)
        public_url = self.public_url_for_share_link(link)

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
            self._record_event(proposal, "proposal.whatsapp_sent", channel=payload.channel, details={"simulated": True, "share_link_id": link.id})
            self._record_event(proposal, "proposal.sent", channel=payload.channel, details={"simulated": True, "share_link_id": link.id})
            self._create_default_followups(proposal, payload.channel)
            proposal.status = "sent"
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
        self._audit("proposal.whatsapp_sent", proposal, {"channel": payload.channel, "share_link_id": link.id})
        self._audit("proposal.sent", proposal, {"channel": payload.channel, "share_link_id": link.id})
        self._record_event(proposal, "proposal.whatsapp_sent", channel=payload.channel, details={"share_link_id": link.id})
        self._record_event(proposal, "proposal.sent", channel=payload.channel, details={"share_link_id": link.id})
        self._create_default_followups(proposal, payload.channel)
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

        link = self._ensure_share_link(proposal)
        public_url = self.public_url_for_share_link(link)
        body = payload.message or self._default_proposal_email_body(proposal, public_url)
        if settings.app_env.strip().lower() != "production":
            self._audit("proposal.email_sent", proposal, {"channel": payload.channel, "simulated": True})
            self._record_event(proposal, "proposal.email_sent", channel=payload.channel, details={"simulated": True, "share_link_id": link.id})
            self._record_event(proposal, "proposal.sent", channel=payload.channel, details={"simulated": True, "share_link_id": link.id})
            self._create_default_followups(proposal, payload.channel)
            proposal.status = "sent"
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
        self._audit("proposal.email_sent", proposal, {"channel": payload.channel, "share_link_id": link.id})
        self._audit("proposal.sent", proposal, {"channel": payload.channel, "share_link_id": link.id})
        self._record_event(proposal, "proposal.email_sent", channel=payload.channel, details={"share_link_id": link.id})
        self._record_event(proposal, "proposal.sent", channel=payload.channel, details={"share_link_id": link.id})
        self._create_default_followups(proposal, payload.channel)
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
