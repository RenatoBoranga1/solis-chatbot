from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Conversation, Feedback, Lead, Message, Proposal, ProposalFollowUp, ProposalShareLink, Ticket
from app.schemas import DashboardMetrics, ProposalMetrics

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/metrics", response_model=DashboardMetrics)
def metrics(
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
) -> DashboardMetrics:
    total_atendimentos = db.scalar(select(func.count(Conversation.id))) or 0
    leads_orcamento = db.scalar(select(func.count(Lead.id))) or 0
    chamados_abertos = db.scalar(select(func.count(Ticket.id)).where(Ticket.status.notin_(["Resolvido", "Cancelado"]))) or 0
    baixa = db.scalar(select(func.count(Ticket.id)).where(Ticket.severity == "baixa")) or 0
    media = db.scalar(select(func.count(Ticket.id)).where(Ticket.severity == "media")) or 0
    alta = db.scalar(select(func.count(Ticket.id)).where(Ticket.severity == "alta")) or 0
    resolvidos = db.scalar(select(func.count(Conversation.id)).where(Conversation.bot_resolved.is_(True))) or 0
    transferidos = db.scalar(select(func.count(Conversation.id)).where(Conversation.transferred_to_human.is_(True))) or 0
    satisfacao = db.scalar(select(func.avg(Feedback.rating)))
    taxa = round((leads_orcamento / total_atendimentos) * 100, 2) if total_atendimentos else 0.0
    proposal_metrics = _proposal_metrics(db)
    return DashboardMetrics(
        total_atendimentos=total_atendimentos,
        leads_orcamento=leads_orcamento,
        chamados_abertos=chamados_abertos,
        baixa_gravidade=baixa,
        media_gravidade=media,
        alta_gravidade=alta,
        resolvidos_pelo_bot=resolvidos,
        transferidos_para_humano=transferidos,
        taxa_conversao_orcamento=taxa,
        satisfacao_media=float(satisfacao) if satisfacao is not None else None,
        proposal_metrics=proposal_metrics,
    )


def _proposal_metrics(db: Session) -> ProposalMetrics:
    created = db.scalar(select(func.count(Proposal.id))) or 0
    sent = db.scalar(select(func.count(Proposal.id)).where(Proposal.status.in_(["sent", "accepted", "rejected"]))) or 0
    accepted = db.scalar(select(func.count(Proposal.id)).where(Proposal.status == "accepted")) or 0
    rejected = db.scalar(select(func.count(Proposal.id)).where(Proposal.status == "rejected")) or 0
    open_count = db.scalar(
        select(func.count(Proposal.id)).where(Proposal.status.in_(["draft", "under_review", "approved", "ready_to_send", "sent"]))
    ) or 0
    viewed = db.scalar(select(func.count(ProposalShareLink.id)).where(ProposalShareLink.views_count > 0)) or 0
    pending_followups = db.scalar(select(func.count(ProposalFollowUp.id)).where(ProposalFollowUp.status == "pending")) or 0
    overdue_followups = db.scalar(
        select(func.count(ProposalFollowUp.id)).where(
            ProposalFollowUp.status == "pending",
            ProposalFollowUp.due_at < func.now(),
        )
    ) or 0
    total_pipeline_value = db.scalar(
        select(func.coalesce(func.sum(Proposal.total_amount), 0)).where(
            Proposal.status.in_(["draft", "under_review", "approved", "ready_to_send", "sent"])
        )
    ) or 0
    accepted_value = db.scalar(
        select(func.coalesce(func.sum(Proposal.total_amount), 0)).where(Proposal.status == "accepted")
    ) or 0
    average_ticket = db.scalar(select(func.avg(Proposal.total_amount)).where(Proposal.total_amount > 0)) or 0
    proposed_leads = db.scalar(select(func.count(func.distinct(Proposal.lead_id))).where(Proposal.lead_id.is_not(None))) or 0
    total_leads = db.scalar(select(func.count(Lead.id))) or 0
    conversion_rate = round((accepted / sent) * 100, 2) if sent else 0.0
    return ProposalMetrics(
        created=created,
        sent=sent,
        accepted=accepted,
        rejected=rejected,
        open=open_count,
        viewed=viewed,
        pending_followups=pending_followups,
        overdue_followups=overdue_followups,
        total_pipeline_value=float(total_pipeline_value),
        accepted_value=float(accepted_value),
        average_ticket=round(float(average_ticket), 2),
        conversion_rate=conversion_rate,
        leads_without_proposal=max(int(total_leads - proposed_leads), 0),
    )


@router.get("/intents")
def intents(db: Session = Depends(get_db), _user=Depends(get_current_user)) -> list[dict[str, int | str]]:
    rows = db.execute(
        select(Conversation.intent, func.count(Conversation.id)).group_by(Conversation.intent).order_by(func.count().desc())
    )
    return [{"intent": intent or "nao_classificado", "total": total} for intent, total in rows]


@router.get("/severity")
def severity(db: Session = Depends(get_db), _user=Depends(get_current_user)) -> list[dict[str, int | str]]:
    rows = db.execute(select(Ticket.severity, func.count(Ticket.id)).group_by(Ticket.severity))
    return [{"severity": severity or "nao_classificado", "total": total} for severity, total in rows]


@router.get("/resolution-rate")
def resolution_rate(db: Session = Depends(get_db), _user=Depends(get_current_user)) -> dict[str, float | int]:
    total = db.scalar(select(func.count(Conversation.id))) or 0
    resolved = db.scalar(select(func.count(Conversation.id)).where(Conversation.bot_resolved.is_(True))) or 0
    transfered = db.scalar(select(func.count(Conversation.id)).where(Conversation.transferred_to_human.is_(True))) or 0
    bot_rate = round((resolved / total) * 100, 2) if total else 0.0
    handoff_rate = round((transfered / total) * 100, 2) if total else 0.0
    return {"total": total, "bot_resolution_rate": bot_rate, "handoff_rate": handoff_rate}


@router.get("/top-questions")
def top_questions(db: Session = Depends(get_db), _user=Depends(get_current_user)) -> list[dict[str, int | str]]:
    rows = db.execute(
        select(Message.content, func.count(Message.id))
        .where(Message.sender_type == "customer")
        .group_by(Message.content)
        .order_by(func.count().desc())
        .limit(20)
    )
    return [{"question": content, "total": total} for content, total in rows]
