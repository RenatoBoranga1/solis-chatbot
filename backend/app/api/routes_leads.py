from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import Lead
from app.schemas import LeadIn, LeadOut, LeadUpdate, StatusPatch

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.get("", response_model=list[LeadOut])
def list_leads(
    db: Session = Depends(get_db),
    _user=Depends(require_roles("admin", "comercial", "gestor")),
) -> list[Lead]:
    return list(db.scalars(select(Lead).order_by(desc(Lead.created_at)).limit(300)).all())


@router.post("", response_model=LeadOut)
def create_lead(
    payload: LeadIn,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("admin", "comercial", "gestor")),
) -> Lead:
    lead = Lead(**payload.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("admin", "comercial", "gestor")),
) -> Lead:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.put("/{lead_id}", response_model=LeadOut)
def update_lead(
    lead_id: str,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("admin", "comercial", "gestor")),
) -> Lead:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    db.commit()
    db.refresh(lead)
    return lead


@router.patch("/{lead_id}/status", response_model=LeadOut)
def update_lead_status(
    lead_id: str,
    payload: StatusPatch,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("admin", "comercial", "gestor")),
) -> Lead:
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.status = payload.status
    db.commit()
    db.refresh(lead)
    return lead

