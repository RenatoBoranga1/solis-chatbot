import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import Message, WebhookEvent
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
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid WhatsApp payload")

    event_id = _extract_event_id(payload)
    webhook_event = _create_webhook_event(db, payload, event_id)
    service = WhatsAppCloudService()

    try:
        incoming_messages = service.parse_payload(payload)
        logger.info("Received WhatsApp webhook with %s processable message(s).", len(incoming_messages))

        if not incoming_messages:
            _mark_webhook_event_processed(db, webhook_event)
            return WhatsAppWebhookResult(status="ok", ignored=1)

        conversation_service = ConversationService(db)
        processed = 0
        duplicates = 0
        send_errors = 0

        for incoming in incoming_messages:
            if _is_duplicate_message(db, incoming.message_id):
                duplicates += 1
                logger.info("Ignoring duplicate WhatsApp message ending with %s.", _safe_suffix(incoming.message_id))
                continue

            chat_payload = ChatMessageIn(
                channel="whatsapp",
                external_id=incoming.wa_id,
                provider="whatsapp",
                provider_message_id=incoming.message_id,
                message=incoming.text,
                attachment_url=incoming.attachment_url,
                media_id=incoming.media_id,
                media_type=incoming.media_type,
                customer=CustomerIn(
                    name=incoming.contact_name,
                    phone=incoming.phone,
                ),
            )
            chat_response = conversation_service.handle_message(chat_payload)

            read_result = service.mark_message_as_read(incoming.message_id)
            if read_result.get("status") == "error":
                logger.warning("Failed to mark WhatsApp message ending with %s as read.", _safe_suffix(incoming.message_id))

            send_result = service.send_text_message(incoming.wa_id, chat_response.response)
            if _is_send_failure(send_result):
                send_errors += 1
                logger.error(
                    "WhatsApp response delivery failed for message ending with %s; status=%s.",
                    _safe_suffix(incoming.message_id),
                    send_result.get("status", "unknown"),
                )

            processed += 1

        _mark_webhook_event_processed(db, webhook_event)

        if processed == 0 and duplicates > 0:
            return WhatsAppWebhookResult(
                status="duplicate_ignored",
                duplicates=duplicates,
                send_errors=send_errors,
            )

        return WhatsAppWebhookResult(
            status="ok",
            processed=processed,
            duplicates=duplicates,
            send_errors=send_errors,
        )
    except Exception as exc:
        logger.exception("Failed to process WhatsApp webhook event ending with %s.", _safe_suffix(event_id))
        _mark_webhook_event_error(db, webhook_event, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="WhatsApp webhook processing failed",
        ) from exc


def _create_webhook_event(db: Session, payload: dict, event_id: str) -> WebhookEvent:
    webhook_event = WebhookEvent(
        provider="whatsapp",
        event_id=event_id,
        payload=payload,
        processed=False,
    )
    db.add(webhook_event)
    db.commit()
    return webhook_event


def _mark_webhook_event_processed(db: Session, webhook_event: WebhookEvent) -> None:
    webhook_event.processed = True
    webhook_event.error_message = None
    db.add(webhook_event)
    db.commit()


def _mark_webhook_event_error(db: Session, webhook_event: WebhookEvent, exc: Exception) -> None:
    rollback = getattr(db, "rollback", None)
    if callable(rollback):
        rollback()
    webhook_event.processed = False
    webhook_event.error_message = _safe_error_message(exc)
    db.add(webhook_event)
    db.commit()


def _extract_event_id(payload: dict) -> str:
    for entry in _as_list(payload.get("entry")):
        for change in _as_list(_as_dict(entry).get("changes")):
            messages = _as_list(_as_dict(_as_dict(change).get("value")).get("messages"))
            for raw_message in messages:
                message_id = _as_dict(raw_message).get("id")
                if message_id:
                    return str(message_id)
    return str(uuid.uuid4())


def _is_duplicate_message(db: Session, message_id: str) -> bool:
    existing = db.scalar(
        select(Message.id).where(
            Message.provider == "whatsapp",
            Message.provider_message_id == message_id,
        )
    )
    return existing is not None


def _safe_suffix(value: str | None) -> str:
    if not value:
        return "unknown"
    return value[-6:]


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).replace("\n", " ")[:300]
    return f"{exc.__class__.__name__}: {message}"


def _is_send_failure(result: dict) -> bool:
    return result.get("status") in {"error", "skipped"}


def _as_dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list:
    return value if isinstance(value, list) else []
