from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Conversation
from app.schemas import AssignIn, ChatMessageIn, ChatMessageOut, ConversationOut, HandoffIn
from app.services.conversation import ConversationService

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/message", response_model=ChatMessageOut)
def message(payload: ChatMessageIn, db: Session = Depends(get_db)) -> ChatMessageOut:
    service = ConversationService(db)
    try:
        return service.handle_message(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
) -> list[Conversation]:
    return list(
        db.scalars(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .order_by(desc(Conversation.created_at))
            .limit(200)
        ).all()
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
) -> Conversation:
    conversation = db.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post("/conversations/{conversation_id}/handoff")
def handoff(
    conversation_id: str,
    payload: HandoffIn,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
) -> dict[str, str]:
    service = ConversationService(db)
    try:
        handoff_record = service.request_handoff(conversation_id, payload.reason, payload.assigned_to)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": handoff_record.id, "status": "handoff"}


@router.post("/conversations/{conversation_id}/assign", response_model=ConversationOut)
def assign(
    conversation_id: str,
    payload: AssignIn,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
) -> Conversation:
    service = ConversationService(db)
    try:
        return service.assign_conversation(conversation_id, payload.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

