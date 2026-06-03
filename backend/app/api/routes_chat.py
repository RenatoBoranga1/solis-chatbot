import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models import Conversation
from app.schemas import (
    AssignIn,
    ChatAttachmentOut,
    ChatMessageIn,
    ChatMessageOut,
    ContinueWhatsAppIn,
    ContinueWhatsAppOut,
    ConversationOut,
    HandoffIn,
)
from app.services.conversation import ConversationService
from app.services.omnichannel import OmnichannelService

router = APIRouter(prefix="/chat", tags=["Chat"])

CHAT_ATTACHMENT_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
CHAT_ATTACHMENT_TYPES = {
    ".pdf": "pdf",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
}


@router.post("/message", response_model=ChatMessageOut)
def message(
    payload: ChatMessageIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ChatMessageOut:
    service = ConversationService(db)
    try:
        return service.handle_message(payload, background_tasks=background_tasks)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/attachments", response_model=ChatAttachmentOut, status_code=status.HTTP_201_CREATED)
async def upload_chat_attachment(file: UploadFile = File(...)) -> ChatAttachmentOut:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in CHAT_ATTACHMENT_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Envie PDF ou imagem nos formatos PNG, JPG ou WEBP.")

    content = await file.read()
    max_bytes = settings.energy_bill_max_file_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="Arquivo maior que o limite permitido.")

    storage_dir = Path(settings.chat_attachment_storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4()}{suffix}"
    path = storage_dir / safe_name
    path.write_bytes(content)
    return ChatAttachmentOut(
        attachment_url=str(path),
        file_name=Path(file.filename or safe_name).name,
        media_type=CHAT_ATTACHMENT_TYPES.get(suffix, "unknown"),
    )


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
) -> list[Conversation]:
    return list(
        db.scalars(
            select(Conversation)
            .options(selectinload(Conversation.messages), selectinload(Conversation.outbound_channel_links))
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
        .options(
            selectinload(Conversation.messages),
            selectinload(Conversation.outbound_channel_links),
            selectinload(Conversation.inbound_channel_links),
        )
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


@router.post("/conversations/{conversation_id}/continue-whatsapp", response_model=ContinueWhatsAppOut)
def continue_whatsapp(
    conversation_id: str,
    payload: ContinueWhatsAppIn,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
) -> ContinueWhatsAppOut:
    service = OmnichannelService(db)
    try:
        return service.continue_on_whatsapp(conversation_id, payload)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
