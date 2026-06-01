from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import Proposal, User
from app.schemas import (
    ProposalCreate,
    ProposalItemCreate,
    ProposalItemUpdate,
    ProposalOut,
    ProposalSendRequest,
    ProposalSendResult,
    ProposalStatusUpdate,
    ProposalUpdate,
)
from app.services.proposals import ProposalService

router = APIRouter(prefix="/proposals", tags=["Propostas"])

VIEW_ROLES = ("admin", "comercial", "gestor", "suporte", "tecnico")
MANAGE_ROLES = ("admin", "comercial", "gestor")


@router.get("", response_model=list[ProposalOut])
def list_proposals(
    status: str | None = Query(default=None),
    city: str | None = Query(default=None),
    customer: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*VIEW_ROLES)),
) -> list[Proposal]:
    return ProposalService(db).list_proposals(status=status, city=city, customer=customer)


@router.post("", response_model=ProposalOut)
def create_proposal(
    payload: ProposalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> Proposal:
    return ProposalService(db, current_user).create_proposal(payload)


@router.post("/from-lead/{lead_id}", response_model=ProposalOut)
def create_proposal_from_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> Proposal:
    try:
        return ProposalService(db, current_user).create_from_lead(lead_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{proposal_id}", response_model=ProposalOut)
def get_proposal(
    proposal_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*VIEW_ROLES)),
) -> Proposal:
    try:
        return ProposalService(db).get_proposal(proposal_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{proposal_id}", response_model=ProposalOut)
def update_proposal(
    proposal_id: str,
    payload: ProposalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> Proposal:
    try:
        return ProposalService(db, current_user).update_proposal(proposal_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{proposal_id}/status", response_model=ProposalOut)
def update_proposal_status(
    proposal_id: str,
    payload: ProposalStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> Proposal:
    try:
        return ProposalService(db, current_user).update_status(proposal_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{proposal_id}/items", response_model=ProposalOut)
def add_proposal_item(
    proposal_id: str,
    payload: ProposalItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> Proposal:
    try:
        return ProposalService(db, current_user).add_item(proposal_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{proposal_id}/items/{item_id}", response_model=ProposalOut)
def update_proposal_item(
    proposal_id: str,
    item_id: str,
    payload: ProposalItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> Proposal:
    try:
        return ProposalService(db, current_user).update_item(proposal_id, item_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{proposal_id}/items/{item_id}", response_model=ProposalOut)
def delete_proposal_item(
    proposal_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> Proposal:
    try:
        return ProposalService(db, current_user).delete_item(proposal_id, item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{proposal_id}/generate-pdf", response_model=ProposalOut)
def generate_proposal_pdf(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> Proposal:
    try:
        return ProposalService(db, current_user).generate_pdf(proposal_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{proposal_id}/send", response_model=ProposalSendResult)
def send_proposal(
    proposal_id: str,
    payload: ProposalSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> ProposalSendResult:
    try:
        return ProposalService(db, current_user).send(proposal_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
