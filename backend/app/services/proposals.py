import uuid
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.models import AuditLog, Conversation, Customer, Lead, Proposal, ProposalItem, User
from app.schemas import (
    ProposalCreate,
    ProposalItemCreate,
    ProposalItemUpdate,
    ProposalSendRequest,
    ProposalSendResult,
    ProposalUpdate,
)
from app.services.proposal_pdf import ProposalPdfService

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
        internal_notes = DEFAULT_PROPOSAL_NOTICE
        if missing:
            internal_notes += f" Dados faltantes: {', '.join(missing)}."

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
        self._audit("proposal.pdf_generated", proposal, {"pdf_url": proposal.pdf_url})
        self.db.commit()
        self.db.refresh(proposal)
        return proposal

    def send(self, proposal_id: str, payload: ProposalSendRequest) -> ProposalSendResult:
        proposal = self.get_proposal(proposal_id)
        if not proposal.pdf_url:
            proposal.pdf_url = self.pdf_service.generate(proposal)
        proposal.status = "sent"
        self._audit("proposal.sent", proposal, {"channel": payload.channel})
        self.db.commit()
        return ProposalSendResult(
            status="simulated",
            message="Envio simulado. PDF gerado e pronto para envio.",
            pdf_url=proposal.pdf_url,
        )

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
