from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Conversation, Feedback, Lead, Message, Ticket
from app.schemas import DashboardMetrics

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

