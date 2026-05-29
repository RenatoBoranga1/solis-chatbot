from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import User
from app.schemas import AIAnalysisOut, DashboardAIInsights, SuggestedReplyOut
from app.services.ai_analysis import AIAnalysisService

router = APIRouter(prefix="/ai", tags=["Análise Inteligente"])

internal_user = require_roles("admin", "comercial", "suporte", "tecnico", "gestor")


@router.post("/conversations/{conversation_id}/analyze", response_model=AIAnalysisOut)
def analyze_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(internal_user),
):
    service = AIAnalysisService(db, actor_user_id=current_user.id)
    try:
        return service.analyze_conversation(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/conversations/{conversation_id}/analysis", response_model=AIAnalysisOut)
def get_conversation_analysis(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(internal_user),
):
    analysis = AIAnalysisService(db, actor_user_id=current_user.id).get_latest_conversation_analysis(conversation_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.post("/leads/{lead_id}/analyze", response_model=AIAnalysisOut)
def analyze_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(internal_user),
):
    service = AIAnalysisService(db, actor_user_id=current_user.id)
    try:
        return service.analyze_lead(lead_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/leads/{lead_id}/analysis", response_model=AIAnalysisOut)
def get_lead_analysis(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(internal_user),
):
    analysis = AIAnalysisService(db, actor_user_id=current_user.id).get_latest_lead_analysis(lead_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.post("/tickets/{ticket_id}/analyze", response_model=AIAnalysisOut)
def analyze_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(internal_user),
):
    service = AIAnalysisService(db, actor_user_id=current_user.id)
    try:
        return service.analyze_ticket(ticket_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/tickets/{ticket_id}/analysis", response_model=AIAnalysisOut)
def get_ticket_analysis(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(internal_user),
):
    analysis = AIAnalysisService(db, actor_user_id=current_user.id).get_latest_ticket_analysis(ticket_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.post("/conversations/{conversation_id}/suggest-reply", response_model=SuggestedReplyOut)
def suggest_reply(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(internal_user),
):
    service = AIAnalysisService(db, actor_user_id=current_user.id)
    try:
        reply = service.generate_suggested_reply(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SuggestedReplyOut(conversation_id=conversation_id, suggested_reply=reply)


@router.get("/dashboard/insights", response_model=DashboardAIInsights)
def dashboard_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(internal_user),
):
    return AIAnalysisService(db, actor_user_id=current_user.id).generate_daily_insights()
