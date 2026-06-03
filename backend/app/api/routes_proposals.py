from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import CompanySettings, Proposal, ProposalFollowUp, ProposalShareLink, User
from app.schemas import (
    CompanySettingsIn,
    CompanySettingsOut,
    ProposalCreate,
    ProposalCustomerResponseIn,
    ProposalFollowUpCreate,
    ProposalFollowUpOut,
    ProposalItemCreate,
    ProposalItemUpdate,
    ProposalOut,
    ProposalPriceItemActivePatch,
    ProposalPriceItemCreate,
    ProposalPriceItemOut,
    ProposalPriceItemUpdate,
    ProposalShareLinkCreate,
    ProposalShareLinkOut,
    ProposalSendRequest,
    ProposalSendResult,
    ProposalStatusUpdate,
    ProposalUpdate,
    PublicProposalOut,
    PublicProposalResponseResult,
)
from app.services.proposals import ProposalService

router = APIRouter(prefix="/proposals", tags=["Propostas"])
company_router = APIRouter(prefix="/company-settings", tags=["Configuracoes comerciais"])
public_router = APIRouter(prefix="/public/proposals", tags=["Propostas publicas"])
price_router = APIRouter(prefix="/proposal-price-items", tags=["Tabela de preços de propostas"])

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


@router.get("/followups", response_model=list[ProposalFollowUpOut])
def list_proposal_followups(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*VIEW_ROLES)),
) -> list[ProposalFollowUp]:
    return ProposalService(db).list_followups(status=status)


@router.patch("/followups/{followup_id}/complete", response_model=ProposalFollowUpOut)
def complete_proposal_followup(
    followup_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> ProposalFollowUp:
    try:
        return ProposalService(db, current_user).complete_followup(followup_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/followups/{followup_id}/cancel", response_model=ProposalFollowUpOut)
def cancel_proposal_followup(
    followup_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> ProposalFollowUp:
    try:
        return ProposalService(db, current_user).cancel_followup(followup_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/share-links/{link_id}/revoke", response_model=ProposalShareLinkOut)
def revoke_proposal_share_link(
    link_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> ProposalShareLink:
    try:
        service = ProposalService(db, current_user)
        link = service.revoke_share_link(link_id)
        link.public_url = service.public_url_for_share_link(link)  # type: ignore[attr-defined]
        return link
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


@router.post("/{proposal_id}/share-link", response_model=ProposalShareLinkOut)
def create_proposal_share_link(
    proposal_id: str,
    payload: ProposalShareLinkCreate = ProposalShareLinkCreate(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> ProposalShareLink:
    try:
        service = ProposalService(db, current_user)
        link = service.create_share_link(proposal_id, payload)
        link.public_url = service.public_url_for_share_link(link)  # type: ignore[attr-defined]
        return link
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{proposal_id}/share-links", response_model=list[ProposalShareLinkOut])
def list_proposal_share_links(
    proposal_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*VIEW_ROLES)),
) -> list[ProposalShareLink]:
    try:
        service = ProposalService(db)
        links = service.list_share_links(proposal_id)
        for link in links:
            link.public_url = service.public_url_for_share_link(link)  # type: ignore[attr-defined]
        return links
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{proposal_id}/followups", response_model=ProposalFollowUpOut)
def create_proposal_followup(
    proposal_id: str,
    payload: ProposalFollowUpCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> ProposalFollowUp:
    try:
        return ProposalService(db, current_user).create_followup(proposal_id, payload)
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


@router.post("/{proposal_id}/apply-price-table", response_model=ProposalOut)
def apply_proposal_price_table(
    proposal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> Proposal:
    try:
        return ProposalService(db, current_user).apply_price_table(proposal_id)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


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


@price_router.get("", response_model=list[ProposalPriceItemOut])
def list_proposal_price_items(
    active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*VIEW_ROLES)),
):
    return ProposalService(db).list_price_items(active=active)


@price_router.post("", response_model=ProposalPriceItemOut)
def create_proposal_price_item(
    payload: ProposalPriceItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
):
    return ProposalService(db, current_user).create_price_item(payload)


@price_router.put("/{item_id}", response_model=ProposalPriceItemOut)
def update_proposal_price_item(
    item_id: str,
    payload: ProposalPriceItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
):
    try:
        return ProposalService(db, current_user).update_price_item(item_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@price_router.patch("/{item_id}/active", response_model=ProposalPriceItemOut)
def update_proposal_price_item_active(
    item_id: str,
    payload: ProposalPriceItemActivePatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
):
    try:
        return ProposalService(db, current_user).set_price_item_active(item_id, payload.active)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@price_router.delete("/{item_id}", status_code=204)
def delete_proposal_price_item(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> None:
    try:
        ProposalService(db, current_user).delete_price_item(item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@company_router.get("", response_model=CompanySettingsOut)
def get_company_settings(
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles("admin", "gestor")),
) -> CompanySettings:
    return ProposalService(db).get_company_settings()


@company_router.put("", response_model=CompanySettingsOut)
def update_company_settings(
    payload: CompanySettingsIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "gestor")),
) -> CompanySettings:
    return ProposalService(db, current_user).update_company_settings(payload)


@public_router.get("/{token}", response_model=PublicProposalOut)
def get_public_proposal(token: str, db: Session = Depends(get_db)) -> PublicProposalOut:
    service = ProposalService(db)
    try:
        proposal, link, company = service.get_public_proposal(token)
    except ValueError as exc:
        raise HTTPException(status_code=410, detail=_public_link_error(str(exc))) from exc
    link.public_url = service.public_url_for_share_link(link)  # type: ignore[attr-defined]
    return PublicProposalOut(
        proposal=proposal,
        share_link=link,
        company=company,
        pdf_download_url=f"/public/proposals/{token}/pdf",
    )


@public_router.post("/{token}/responses", response_model=PublicProposalResponseResult)
def create_public_proposal_response(
    token: str,
    payload: ProposalCustomerResponseIn,
    request: Request,
    db: Session = Depends(get_db),
) -> PublicProposalResponseResult:
    service = ProposalService(db)
    try:
        response = service.register_customer_response(
            token,
            payload,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=410, detail=_public_link_error(str(exc))) from exc
    return PublicProposalResponseResult(
        status="ok",
        message=getattr(response, "confirmation_message", "Resposta registrada com sucesso."),
        response=response,
    )


@public_router.get("/{token}/pdf")
def download_public_proposal_pdf(token: str, db: Session = Depends(get_db)) -> FileResponse:
    service = ProposalService(db)
    try:
        proposal = service.register_pdf_download(token)
    except ValueError as exc:
        raise HTTPException(status_code=410, detail=_public_link_error(str(exc))) from exc
    if not proposal.pdf_url or not Path(proposal.pdf_url).exists():
        raise HTTPException(status_code=404, detail="PDF da proposta nao encontrado.")
    filename = f"Proposta-Solar-Solucoes-{proposal.proposal_number}.pdf"
    return FileResponse(proposal.pdf_url, media_type="application/pdf", filename=filename)


def _public_link_error(message: str) -> str:
    if "expired" in message.lower():
        return "Este link de proposta expirou. Solicite um novo link para a equipe Solar Solucoes."
    if "revoked" in message.lower():
        return "Este link de proposta nao esta mais disponivel."
    return "Link de proposta invalido ou indisponivel."
