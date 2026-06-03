from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import AuditLog, ProposalKit, ProposalKitItem, User
from app.schemas import ProposalKitCreate, ProposalKitItemCreate, ProposalKitItemUpdate, ProposalKitUpdate


@dataclass
class KitSelectionResult:
    average_bill: float | None
    estimated_monthly_generation_kwh: float | None
    estimated_power_kwp: float | None
    selected_kit: ProposalKit | None
    selection_reason: str | None


class ProposalKitService:
    def __init__(self, db: Session, actor: User | None = None) -> None:
        self.db = db
        self.actor = actor

    def list_kits(self, active: bool | None = None) -> list[ProposalKit]:
        statement = select(ProposalKit).options(selectinload(ProposalKit.items)).order_by(ProposalKit.sort_order, ProposalKit.suggested_power_kwp)
        if active is not None:
            statement = statement.where(ProposalKit.active == active)
        return list(self.db.scalars(statement).all())

    def get_kit(self, kit_id: str) -> ProposalKit:
        kit = self.db.scalar(select(ProposalKit).where(ProposalKit.id == kit_id).options(selectinload(ProposalKit.items)))
        if not kit:
            raise ValueError("Proposal kit not found")
        return kit

    def create_kit(self, payload: ProposalKitCreate) -> ProposalKit:
        kit = ProposalKit(**payload.model_dump(exclude={"items"}))
        self.db.add(kit)
        self.db.flush()
        for index, item_payload in enumerate(payload.items):
            self._add_item_object(kit, item_payload, index)
        self._audit("proposal_kit.created", kit)
        self.db.commit()
        self.db.refresh(kit)
        return kit

    def update_kit(self, kit_id: str, payload: ProposalKitUpdate) -> ProposalKit:
        kit = self.get_kit(kit_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(kit, field, value)
        self._audit("proposal_kit.updated", kit)
        self.db.commit()
        self.db.refresh(kit)
        return kit

    def set_active(self, kit_id: str, active: bool) -> ProposalKit:
        kit = self.get_kit(kit_id)
        kit.active = active
        self._audit("proposal_kit.active_changed", kit, {"active": active})
        self.db.commit()
        self.db.refresh(kit)
        return kit

    def delete_kit(self, kit_id: str) -> None:
        kit = self.get_kit(kit_id)
        self._audit("proposal_kit.deleted", kit)
        self.db.delete(kit)
        self.db.commit()

    def create_item(self, kit_id: str, payload: ProposalKitItemCreate) -> ProposalKit:
        kit = self.get_kit(kit_id)
        self._add_item_object(kit, payload, len(kit.items or []))
        self._audit("proposal_kit.item_created", kit)
        self.db.commit()
        self.db.refresh(kit)
        return kit

    def update_item(self, kit_id: str, item_id: str, payload: ProposalKitItemUpdate) -> ProposalKit:
        kit = self.get_kit(kit_id)
        item = self._find_item(kit, item_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        item.total_price = self.line_total(item.quantity, item.unit_price)
        self._audit("proposal_kit.item_updated", kit, {"item_id": item.id})
        self.db.commit()
        self.db.refresh(kit)
        return kit

    def delete_item(self, kit_id: str, item_id: str) -> ProposalKit:
        kit = self.get_kit(kit_id)
        item = self._find_item(kit, item_id)
        self.db.delete(item)
        kit.items = [existing for existing in (kit.items or []) if existing.id != item_id]
        self._audit("proposal_kit.item_deleted", kit, {"item_id": item_id})
        self.db.commit()
        self.db.refresh(kit)
        return kit

    def simulate_selection(
        self,
        average_bill: float | None = None,
        estimated_monthly_generation_kwh: float | None = None,
        estimated_power_kwp: float | None = None,
    ) -> KitSelectionResult:
        power_kwp, generation_kwh = self.estimate_from_average_bill(average_bill)
        estimated_power_kwp = estimated_power_kwp if estimated_power_kwp is not None else power_kwp
        estimated_monthly_generation_kwh = (
            estimated_monthly_generation_kwh if estimated_monthly_generation_kwh is not None else generation_kwh
        )
        kit, reason = self.select_best_kit(
            average_bill=average_bill,
            estimated_monthly_generation_kwh=estimated_monthly_generation_kwh,
            estimated_power_kwp=estimated_power_kwp,
        )
        return KitSelectionResult(
            average_bill=average_bill,
            estimated_monthly_generation_kwh=estimated_monthly_generation_kwh,
            estimated_power_kwp=estimated_power_kwp,
            selected_kit=kit,
            selection_reason=reason,
        )

    def select_best_kit(
        self,
        average_bill: float | None = None,
        estimated_monthly_generation_kwh: float | None = None,
        estimated_power_kwp: float | None = None,
    ) -> tuple[ProposalKit | None, str | None]:
        if estimated_power_kwp is None or estimated_monthly_generation_kwh is None:
            power_kwp, generation_kwh = self.estimate_from_average_bill(average_bill)
            estimated_power_kwp = estimated_power_kwp if estimated_power_kwp is not None else power_kwp
            estimated_monthly_generation_kwh = (
                estimated_monthly_generation_kwh if estimated_monthly_generation_kwh is not None else generation_kwh
            )

        kits = self.list_kits(active=True)
        if not kits:
            return None, None

        if estimated_power_kwp is not None:
            exact_power = [kit for kit in kits if self._contains(float(estimated_power_kwp), kit.min_power_kwp, kit.max_power_kwp)]
            if exact_power:
                return self._smallest_power(exact_power), "Kit escolhido por faixa de potencia estimada."

        if estimated_monthly_generation_kwh is not None:
            exact_consumption = [
                kit
                for kit in kits
                if self._contains(
                    float(estimated_monthly_generation_kwh),
                    kit.min_monthly_consumption_kwh,
                    kit.max_monthly_consumption_kwh,
                )
            ]
            if exact_consumption:
                return self._smallest_power(exact_consumption), "Kit escolhido por faixa de geracao/consumo mensal."

        if estimated_power_kwp is not None:
            above = [kit for kit in kits if float(kit.suggested_power_kwp or 0) >= float(estimated_power_kwp)]
            if above:
                return self._smallest_power(above), "Kit imediatamente acima da potencia estimada."

        return self._largest_power(kits), "Maior kit ativo escolhido por falta de faixa exata."

    def _add_item_object(self, kit: ProposalKit, payload: ProposalKitItemCreate, fallback_order: int) -> ProposalKitItem:
        item = ProposalKitItem(
            kit_id=kit.id,
            category=payload.category,
            description=payload.description,
            quantity=payload.quantity,
            unit=payload.unit,
            unit_price=payload.unit_price,
            total_price=self.line_total(payload.quantity, payload.unit_price),
            sort_order=payload.sort_order if payload.sort_order is not None else fallback_order,
        )
        self.db.add(item)
        kit.items = [*(kit.items or []), item]
        return item

    def _find_item(self, kit: ProposalKit, item_id: str) -> ProposalKitItem:
        for item in kit.items or []:
            if item.id == item_id:
                return item
        raise ValueError("Proposal kit item not found")

    def _audit(self, action: str, kit: ProposalKit, details: dict | None = None) -> None:
        self.db.add(
            AuditLog(
                actor_user_id=self.actor.id if self.actor else None,
                action=action,
                entity_type="proposal_kit",
                entity_id=kit.id,
                details={"kit_name": kit.name, **(details or {})},
            )
        )

    @staticmethod
    def estimate_from_average_bill(average_bill: float | None) -> tuple[float | None, float | None]:
        if not average_bill:
            return None, None
        monthly_generation = max(round((float(average_bill) * 0.85) / 0.95, 2), 0)
        power_kwp = round(monthly_generation / 135, 3)
        return power_kwp, monthly_generation

    @staticmethod
    def line_total(quantity: object, unit_price: object) -> float:
        return round(max(float(quantity or 0), 0) * max(float(unit_price or 0), 0), 2)

    @staticmethod
    def _contains(value: float, minimum: object, maximum: object) -> bool:
        min_value = float(minimum) if minimum is not None else None
        max_value = float(maximum) if maximum is not None else None
        return (min_value is None or value >= min_value) and (max_value is None or value <= max_value)

    @staticmethod
    def _smallest_power(kits: list[ProposalKit]) -> ProposalKit:
        return sorted(kits, key=lambda kit: (float(kit.suggested_power_kwp or 0), kit.sort_order, kit.name))[0]

    @staticmethod
    def _largest_power(kits: list[ProposalKit]) -> ProposalKit:
        return sorted(kits, key=lambda kit: (float(kit.suggested_power_kwp or 0), kit.sort_order, kit.name))[-1]
