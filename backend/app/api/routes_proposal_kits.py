from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import ProposalKit, User
from app.schemas import (
    ProposalKitActivePatch,
    ProposalKitCreate,
    ProposalKitItemCreate,
    ProposalKitItemUpdate,
    ProposalKitOut,
    ProposalKitSimulationIn,
    ProposalKitSimulationOut,
    ProposalKitUpdate,
)
from app.services.proposal_kits import ProposalKitService

router = APIRouter(prefix="/proposal-kits", tags=["Kits fotovoltaicos"])

VIEW_ROLES = ("admin", "comercial", "gestor", "suporte", "tecnico")
MANAGE_ROLES = ("admin", "comercial", "gestor")


@router.get("", response_model=list[ProposalKitOut])
def list_proposal_kits(
    active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*VIEW_ROLES)),
) -> list[ProposalKit]:
    return ProposalKitService(db).list_kits(active=active)


@router.post("", response_model=ProposalKitOut)
def create_proposal_kit(
    payload: ProposalKitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> ProposalKit:
    return ProposalKitService(db, current_user).create_kit(payload)


@router.post("/simulate", response_model=ProposalKitSimulationOut)
def simulate_proposal_kit(
    payload: ProposalKitSimulationIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*VIEW_ROLES)),
) -> ProposalKitSimulationOut:
    result = ProposalKitService(db).simulate_selection(
        average_bill=payload.average_bill,
        estimated_monthly_generation_kwh=payload.estimated_monthly_generation_kwh,
        estimated_power_kwp=payload.estimated_power_kwp,
    )
    return ProposalKitSimulationOut(
        average_bill=result.average_bill,
        estimated_monthly_generation_kwh=result.estimated_monthly_generation_kwh,
        estimated_power_kwp=result.estimated_power_kwp,
        selected_kit=result.selected_kit,
        selection_reason=result.selection_reason,
    )


@router.get("/{kit_id}", response_model=ProposalKitOut)
def get_proposal_kit(
    kit_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*VIEW_ROLES)),
) -> ProposalKit:
    try:
        return ProposalKitService(db).get_kit(kit_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{kit_id}", response_model=ProposalKitOut)
def update_proposal_kit(
    kit_id: str,
    payload: ProposalKitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> ProposalKit:
    try:
        return ProposalKitService(db, current_user).update_kit(kit_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{kit_id}/active", response_model=ProposalKitOut)
def update_proposal_kit_active(
    kit_id: str,
    payload: ProposalKitActivePatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> ProposalKit:
    try:
        return ProposalKitService(db, current_user).set_active(kit_id, payload.active)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{kit_id}", status_code=204)
def delete_proposal_kit(
    kit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> None:
    try:
        ProposalKitService(db, current_user).delete_kit(kit_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{kit_id}/items", response_model=ProposalKitOut)
def create_proposal_kit_item(
    kit_id: str,
    payload: ProposalKitItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> ProposalKit:
    try:
        return ProposalKitService(db, current_user).create_item(kit_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{kit_id}/items/{item_id}", response_model=ProposalKitOut)
def update_proposal_kit_item(
    kit_id: str,
    item_id: str,
    payload: ProposalKitItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> ProposalKit:
    try:
        return ProposalKitService(db, current_user).update_item(kit_id, item_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{kit_id}/items/{item_id}", response_model=ProposalKitOut)
def delete_proposal_kit_item(
    kit_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> ProposalKit:
    try:
        return ProposalKitService(db, current_user).delete_item(kit_id, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
