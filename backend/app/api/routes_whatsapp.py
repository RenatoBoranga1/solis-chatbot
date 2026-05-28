import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import Message
from app.schemas import ChatMessageIn, CustomerIn
from app.schemas_whatsapp import WhatsAppWebhookResult
from app.services.conversation import ConversationService
from app.services.whatsapp_cloud import WhatsAppCloudService, verify_meta_signature

router = APIRouter(tags=["WhatsApp Cloud API"])
logger = logging.getLogger(__name__)


@router.get("/webhook/whatsapp", response_class=PlainTextResponse)
def verify_whatsapp_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
) -> PlainTextResponse:
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return PlainTextResponse(content=hub_challenge)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid WhatsApp verify token")


@router.post("/webhook/whatsapp", response_model=WhatsAppWebhookResult)
async def receive_whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> WhatsAppWebhookResult:
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_meta_signature(raw_body, signature):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid WhatsApp signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from exc

    service = WhatsAppCloudService()
    incoming_messages = service.parse_payload(payload)
    logger.info("Received WhatsApp webhook with %s processable message(s).", len(incoming_messages))

    if not incoming_messages:
        return WhatsAppWebhookResult(status="ok", ignored=1)

    conversation_service = ConversationService(db)
    processed = 0
    duplicates = 0

    for incoming in incoming_messages:
        if _is_duplicate_message(db, incoming.message_id):
            duplicates += 1
            logger.info("Ignoring duplicate WhatsApp message ending with %s.", incoming.message_id[-6:])
            continue

        chat_payload = ChatMessageIn(
            channel="whatsapp",
            external_id=incoming.wa_id,
            provider="whatsapp",
            provider_message_id=incoming.message_id,
            message=incoming.text,
            attachment_url=incoming.attachment_url,
            customer=CustomerIn(
                name=incoming.contact_name,
                phone=incoming.phone,
            ),
        )
        chat_response = conversation_service.handle_message(chat_payload)
        service.mark_message_as_read(incoming.message_id)
        service.send_text_message(incoming.wa_id, chat_response.response)
        processed += 1

    if processed == 0 and duplicates > 0:
        return WhatsAppWebhookResult(status="duplicate_ignored", duplicates=duplicates)

    return WhatsAppWebhookResult(status="ok", processed=processed, duplicates=duplicates)


def _is_duplicate_message(db: Session, message_id: str) -> bool:
    existing = db.scalar(
        select(Message.id).where(
            Message.provider == "whatsapp",
            Message.provider_message_id == message_id,
        )
    )
    return existing is not None
