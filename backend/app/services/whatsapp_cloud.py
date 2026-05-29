import hashlib
import hmac
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.schemas_whatsapp import WhatsAppIncomingMessage

logger = logging.getLogger(__name__)

SUPPORTED_MESSAGE_TYPES = {"text", "image", "document", "audio"}


def verify_meta_signature(raw_body: bytes, signature_header: str | None) -> bool:
    app_secret = settings.whatsapp_app_secret
    app_env = settings.app_env.strip().lower()
    if not app_secret:
        if app_env == "production":
            logger.error("WhatsApp signature validation is required in production.")
            return False
        logger.warning("WhatsApp app secret is not configured; skipping signature validation in development.")
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        if app_env == "production":
            logger.warning("WhatsApp signature header is missing or malformed in production.")
        return False

    digest = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, signature_header)


class WhatsAppCloudService:
    def __init__(self) -> None:
        self.version = settings.whatsapp_api_version.strip("/") or "v20.0"
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.access_token = settings.whatsapp_access_token
        self.base_url = f"https://graph.facebook.com/{self.version}"

    def send_text_message(self, to: str, message: str) -> dict:
        if not self._is_configured():
            logger.warning("WhatsApp send skipped because access token or phone number id is not configured.")
            return {"status": "skipped", "reason": "missing_whatsapp_config"}

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message[:4096],
            },
        }
        try:
            with httpx.Client(timeout=15) as client:
                response = client.post(
                    f"{self.base_url}/{self.phone_number_id}/messages",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError:
            logger.exception("Failed to send WhatsApp text message.")
            return {"status": "error", "reason": "send_failed"}

    def mark_message_as_read(self, message_id: str) -> dict:
        if not self._is_configured():
            return {"status": "skipped", "reason": "missing_whatsapp_config"}

        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        try:
            with httpx.Client(timeout=15) as client:
                response = client.post(
                    f"{self.base_url}/{self.phone_number_id}/messages",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError:
            logger.exception("Failed to mark WhatsApp message as read.")
            return {"status": "error", "reason": "mark_read_failed"}

    def parse_payload(self, payload: dict) -> list[WhatsAppIncomingMessage]:
        incoming: list[WhatsAppIncomingMessage] = []

        for entry in self._as_list(payload.get("entry")):
            entry_data = self._as_dict(entry)
            for change in self._as_list(entry_data.get("changes")):
                change_data = self._as_dict(change)
                value = self._as_dict(change_data.get("value"))
                contacts_by_wa_id = self._contacts_by_wa_id(self._as_list(value.get("contacts")))

                for raw_message in self._as_list(value.get("messages")):
                    message = self._as_dict(raw_message)
                    message_type = message.get("type")
                    if message_type not in SUPPORTED_MESSAGE_TYPES:
                        logger.info("Ignoring unsupported WhatsApp message type: %s", message_type)
                        continue

                    from_number = str(message.get("from") or "")
                    contact = contacts_by_wa_id.get(from_number, {})
                    contact_name = contact.get("profile", {}).get("name")
                    wa_id = str(contact.get("wa_id") or from_number)
                    text, media_id, attachment_url, raw_type_payload = self._extract_content(message, message_type)

                    if not wa_id or not message.get("id"):
                        logger.info("Ignoring WhatsApp message without wa_id or message id.")
                        continue
                    if not text.strip():
                        logger.info("Ignoring WhatsApp message ending with %s because it has no processable text.", str(message.get("id"))[-6:])
                        continue

                    incoming.append(
                        WhatsAppIncomingMessage(
                            wa_id=wa_id,
                            phone=wa_id,
                            contact_name=contact_name,
                            message_id=message["id"],
                            text=text,
                            timestamp=message.get("timestamp"),
                            message_type=message_type,
                            media_id=media_id,
                            media_type=message_type if media_id else None,
                            attachment_url=attachment_url,
                            raw_type_payload=raw_type_payload,
                        )
                    )

        return incoming

    def download_media(self, media_id: str) -> bytes | None:
        if not self.access_token:
            logger.warning("WhatsApp media download skipped because access token is not configured.")
            return None

        try:
            with httpx.Client(timeout=30) as client:
                metadata_response = client.get(f"{self.base_url}/{media_id}", headers=self._headers())
                metadata_response.raise_for_status()
                media_url = metadata_response.json().get("url")
                if not media_url:
                    return None

                media_response = client.get(media_url, headers=self._headers())
                media_response.raise_for_status()
                return media_response.content
        except httpx.HTTPError:
            logger.exception("Failed to download WhatsApp media.")
            return None

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _is_configured(self) -> bool:
        return bool(self.access_token and self.phone_number_id)

    @staticmethod
    def _contacts_by_wa_id(contacts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {
            str(contact.get("wa_id")): contact
            for raw_contact in contacts
            if (contact := WhatsAppCloudService._as_dict(raw_contact)).get("wa_id")
        }

    @staticmethod
    def _extract_content(message: dict, message_type: str) -> tuple[str, str | None, str | None, dict]:
        if message_type == "text":
            text_payload = WhatsAppCloudService._as_dict(message.get("text"))
            text = text_payload.get("body") or ""
            return text, None, None, text_payload

        type_payload = WhatsAppCloudService._as_dict(message.get(message_type))
        media_id = type_payload.get("id")
        text = type_payload.get("caption") or f"Cliente enviou um anexo do tipo {message_type}"
        attachment_url = f"whatsapp://media/{media_id}" if media_id else None
        return text, media_id, attachment_url, type_payload

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        return value if isinstance(value, list) else []
