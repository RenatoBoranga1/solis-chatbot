from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import Ticket
from app.schemas import SeverityPatch, StatusPatch, TicketIn, TicketOut, TicketUpdate

router = APIRouter(prefix="/tickets", tags=["Chamados"])


@router.get("", response_model=list[TicketOut])
def list_tickets(
    db: Session = Depends(get_db),
    _user=Depends(require_roles("admin", "suporte", "tecnico", "gestor")),
) -> list[Ticket]:
    return list(db.scalars(select(Ticket).order_by(desc(Ticket.created_at)).limit(300)).all())


@router.post("", response_model=TicketOut)
def create_ticket(
    payload: TicketIn,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("admin", "suporte", "tecnico", "gestor")),
) -> Ticket:
    ticket = Ticket(**payload.model_dump())
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("admin", "suporte", "tecnico", "gestor")),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.put("/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: str,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("admin", "suporte", "tecnico", "gestor")),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.patch("/{ticket_id}/status", response_model=TicketOut)
def update_ticket_status(
    ticket_id: str,
    payload: StatusPatch,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("admin", "suporte", "tecnico", "gestor")),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.status = payload.status
    db.commit()
    db.refresh(ticket)
    return ticket


@router.patch("/{ticket_id}/severity", response_model=TicketOut)
def update_ticket_severity(
    ticket_id: str,
    payload: SeverityPatch,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("admin", "suporte", "tecnico", "gestor")),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.severity = payload.severity
    db.commit()
    db.refresh(ticket)
    return ticket

