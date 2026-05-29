import hashlib
import hmac
import json
import unittest

from fastapi.testclient import TestClient

from app.api import routes_whatsapp
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models import Attachment, Handoff, Message, Ticket, WebhookEvent
from app.schemas import ChatMessageIn, ChatMessageOut
from app.services.conversation import ConversationService
from app.services.whatsapp_cloud import WhatsAppCloudService


def whatsapp_text_payload(text: str = "Quero um orçamento", message_id: str = "wamid.test-message") -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "business-account-id",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "5511999999999",
                                "phone_number_id": "123456789",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Cliente Teste"},
                                    "wa_id": "5511988887777",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "5511988887777",
                                    "id": message_id,
                                    "timestamp": "1717000000",
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def whatsapp_image_payload(message_id: str = "wamid.image-message", media_id: str = "media-123") -> dict:
    payload = whatsapp_text_payload(message_id=message_id)
    message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    message["type"] = "image"
    message.pop("text", None)
    message["image"] = {"id": media_id, "mime_type": "image/jpeg", "caption": "Foto do inversor"}
    return payload


def whatsapp_status_payload() -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "business-account-id",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "statuses": [{"id": "wamid.sent-message", "status": "sent"}],
                        },
                    }
                ],
            }
        ],
    }


def whatsapp_unsupported_payload() -> dict:
    payload = whatsapp_text_payload(message_id="wamid.unsupported-message")
    message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    message["type"] = "sticker"
    message.pop("text", None)
    message["sticker"] = {"id": "sticker-123"}
    return payload


def signed_body(payload: dict, secret: str) -> tuple[bytes, str]:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return body, f"sha256={digest}"


class FakeDb:
    def __init__(self, duplicate: bool = False) -> None:
        self.duplicate = duplicate
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    def scalar(self, _statement):
        return "existing-message-id" if self.duplicate else None

    def get(self, _model, _id):
        return None

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        for index, obj in enumerate(self.added, start=1):
            if getattr(obj, "id", None) is None:
                setattr(obj, "id", f"fake-id-{index}")

    def commit(self):
        self.commits += 1

    def refresh(self, _obj):
        return None

    def rollback(self):
        self.rollbacks += 1


class ConversationServicePersistenceTest(unittest.TestCase):
    def test_conversation_service_saves_provider_and_attachment(self):
        db = FakeDb()
        service = ConversationService(db)

        service.handle_message(
            ChatMessageIn(
                channel="whatsapp",
                external_id="5511988887777",
                provider_message_id="wamid.provider-test",
                message="Quero um orcamento",
                attachment_url="whatsapp://media/media-123",
                media_id="media-123",
                media_type="image",
            )
        )

        customer_messages = [
            item for item in db.added if isinstance(item, Message) and item.sender_type == "customer"
        ]
        self.assertEqual(len(customer_messages), 1)
        self.assertEqual(customer_messages[0].provider, "whatsapp")
        self.assertEqual(customer_messages[0].provider_message_id, "wamid.provider-test")

        attachments = [item for item in db.added if isinstance(item, Attachment)]
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].provider, "whatsapp")
        self.assertEqual(attachments[0].provider_media_id, "media-123")
        self.assertEqual(attachments[0].file_type, "image")
        self.assertEqual(attachments[0].file_url, "whatsapp://media/media-123")

    def test_conversation_service_risk_message_creates_high_severity_ticket_and_handoff(self):
        db = FakeDb()
        service = ConversationService(db)

        response = service.handle_message(
            ChatMessageIn(
                channel="whatsapp",
                external_id="5511988887777",
                provider_message_id="wamid.risk-service",
                message="Esta saindo cheiro de queimado do inversor",
            )
        )

        tickets = [item for item in db.added if isinstance(item, Ticket)]
        handoffs = [item for item in db.added if isinstance(item, Handoff)]
        self.assertEqual(response.severity, "alta")
        self.assertTrue(response.handoff_required)
        self.assertTrue(tickets)
        self.assertEqual(tickets[0].severity, "alta")
        self.assertTrue(handoffs)


class WhatsAppWebhookTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.fake_db = FakeDb()
        self.handled_payloads = []
        self.sent_messages = []
        self.marked_read = []

        self.original_verify_token = settings.whatsapp_verify_token
        self.original_app_secret = settings.whatsapp_app_secret
        self.original_app_env = settings.app_env
        settings.whatsapp_verify_token = "verify-token"
        settings.whatsapp_app_secret = None
        settings.app_env = "development"

        app.dependency_overrides[get_db] = lambda: self.fake_db

        self.original_conversation_service = routes_whatsapp.ConversationService
        handled_payloads = self.handled_payloads

        class FakeConversationService:
            def __init__(self, _db) -> None:
                pass

            def handle_message(self, payload):
                handled_payloads.append(payload)
                high_severity = "cheiro de queimado" in payload.message.lower()
                return ChatMessageOut(
                    conversation_id="conversation-1",
                    customer_id="customer-1",
                    response=(
                        "Caso classificado como prioridade alta."
                        if high_severity
                        else "Resposta do Solis pelo WhatsApp."
                    ),
                    intent="suporte_tecnico" if high_severity else "orcamento",
                    severity="alta" if high_severity else "baixa",
                    status="handoff" if high_severity else "open",
                    handoff_required=high_severity,
                    created_ticket_id="ticket-1" if high_severity else None,
                )

        routes_whatsapp.ConversationService = FakeConversationService

        self.original_send = WhatsAppCloudService.send_text_message
        self.original_mark = WhatsAppCloudService.mark_message_as_read
        sent_messages = self.sent_messages
        marked_read = self.marked_read

        def fake_send(_service, to: str, message: str) -> dict:
            sent_messages.append((to, message))
            return {"status": "sent"}

        def fake_mark(_service, message_id: str) -> dict:
            marked_read.append(message_id)
            return {"status": "read"}

        WhatsAppCloudService.send_text_message = fake_send
        WhatsAppCloudService.mark_message_as_read = fake_mark

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        routes_whatsapp.ConversationService = self.original_conversation_service
        WhatsAppCloudService.send_text_message = self.original_send
        WhatsAppCloudService.mark_message_as_read = self.original_mark
        settings.whatsapp_verify_token = self.original_verify_token
        settings.whatsapp_app_secret = self.original_app_secret
        settings.app_env = self.original_app_env

    def test_get_webhook_with_valid_verify_token(self):
        response = self.client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "verify-token",
                "hub.challenge": "challenge-123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "challenge-123")

    def test_get_webhook_with_invalid_verify_token(self):
        response = self.client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "challenge-123",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_post_webhook_with_text_message(self):
        response = self.client.post("/webhook/whatsapp", json=whatsapp_text_payload())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["processed"], 1)
        self.assertEqual(len(self.handled_payloads), 1)
        payload = self.handled_payloads[0]
        self.assertEqual(payload.channel, "whatsapp")
        self.assertEqual(payload.external_id, "5511988887777")
        self.assertEqual(payload.provider_message_id, "wamid.test-message")
        self.assertEqual(payload.customer.name, "Cliente Teste")
        self.assertEqual(payload.customer.phone, "5511988887777")
        self.assertEqual(self.sent_messages[0], ("5511988887777", "Resposta do Solis pelo WhatsApp."))
        self.assertEqual(self.marked_read, ["wamid.test-message"])

    def test_post_webhook_records_webhook_event(self):
        response = self.client.post("/webhook/whatsapp", json=whatsapp_text_payload())

        self.assertEqual(response.status_code, 200)
        events = [item for item in self.fake_db.added if isinstance(item, WebhookEvent)]
        self.assertTrue(events)
        self.assertEqual(events[-1].provider, "whatsapp")
        self.assertEqual(events[-1].event_id, "wamid.test-message")
        self.assertTrue(events[-1].processed)
        self.assertIsNone(events[-1].error_message)

    def test_post_webhook_counts_send_error(self):
        def fake_send_error(_service, _to: str, _message: str) -> dict:
            return {"status": "error", "reason": "send_failed"}

        WhatsAppCloudService.send_text_message = fake_send_error

        response = self.client.post("/webhook/whatsapp", json=whatsapp_text_payload())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["send_errors"], 1)
        events = [item for item in self.fake_db.added if isinstance(item, WebhookEvent)]
        self.assertTrue(events[-1].processed)

    def test_post_webhook_counts_skipped_send_as_operational_error(self):
        def fake_send_skipped(_service, _to: str, _message: str) -> dict:
            return {"status": "skipped", "reason": "missing_whatsapp_config"}

        WhatsAppCloudService.send_text_message = fake_send_skipped

        response = self.client.post("/webhook/whatsapp", json=whatsapp_text_payload())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["send_errors"], 1)

    def test_post_webhook_image_attachment_passes_media_metadata(self):
        response = self.client.post("/webhook/whatsapp", json=whatsapp_image_payload())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.handled_payloads), 1)
        payload = self.handled_payloads[0]
        self.assertEqual(payload.message, "Foto do inversor")
        self.assertEqual(payload.attachment_url, "whatsapp://media/media-123")
        self.assertEqual(payload.media_id, "media-123")
        self.assertEqual(payload.media_type, "image")

    def test_post_webhook_ignores_duplicate_message(self):
        self.fake_db.duplicate = True

        response = self.client.post("/webhook/whatsapp", json=whatsapp_text_payload())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "duplicate_ignored")
        self.assertEqual(response.json()["duplicates"], 1)
        self.assertEqual(self.handled_payloads, [])
        self.assertEqual(self.sent_messages, [])
        events = [item for item in self.fake_db.added if isinstance(item, WebhookEvent)]
        self.assertTrue(events[-1].processed)

    def test_post_webhook_without_messages_returns_ignored(self):
        response = self.client.post("/webhook/whatsapp", json=whatsapp_status_payload())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["ignored"], 1)
        self.assertEqual(self.handled_payloads, [])

    def test_post_webhook_with_unsupported_message_type_is_ignored(self):
        response = self.client.post("/webhook/whatsapp", json=whatsapp_unsupported_payload())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ignored"], 1)
        self.assertEqual(self.handled_payloads, [])

    def test_post_webhook_missing_signature_in_production_returns_403(self):
        settings.app_env = "production"
        settings.whatsapp_app_secret = "meta-app-secret"

        response = self.client.post("/webhook/whatsapp", json=whatsapp_text_payload())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.handled_payloads, [])

    def test_post_webhook_invalid_signature_in_production_returns_403(self):
        settings.app_env = "production"
        settings.whatsapp_app_secret = "meta-app-secret"

        response = self.client.post(
            "/webhook/whatsapp",
            json=whatsapp_text_payload(),
            headers={"X-Hub-Signature-256": "sha256=invalid"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.handled_payloads, [])

    def test_post_webhook_valid_signature_in_production_processes_message(self):
        settings.app_env = "production"
        settings.whatsapp_app_secret = "meta-app-secret"
        body, signature = signed_body(whatsapp_text_payload(message_id="wamid.signed"), settings.whatsapp_app_secret)

        response = self.client.post(
            "/webhook/whatsapp",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["processed"], 1)
        self.assertEqual(len(self.handled_payloads), 1)

    def test_parse_payload_extracts_contact_and_text(self):
        parsed = WhatsAppCloudService().parse_payload(whatsapp_text_payload())

        self.assertEqual(len(parsed), 1)
        message = parsed[0]
        self.assertEqual(message.wa_id, "5511988887777")
        self.assertEqual(message.phone, "5511988887777")
        self.assertEqual(message.contact_name, "Cliente Teste")
        self.assertEqual(message.message_id, "wamid.test-message")
        self.assertEqual(message.text, "Quero um orçamento")
        self.assertEqual(message.message_type, "text")
        self.assertIsNone(message.media_type)

    def test_parse_payload_extracts_image_media_metadata(self):
        parsed = WhatsAppCloudService().parse_payload(whatsapp_image_payload())

        self.assertEqual(len(parsed), 1)
        message = parsed[0]
        self.assertEqual(message.message_type, "image")
        self.assertEqual(message.media_id, "media-123")
        self.assertEqual(message.media_type, "image")
        self.assertEqual(message.attachment_url, "whatsapp://media/media-123")

    def test_parse_payload_ignores_unexpected_shapes_without_exception(self):
        parsed = WhatsAppCloudService().parse_payload(
            {
                "entry": [
                    None,
                    {
                        "changes": [
                            "bad-change",
                            {"value": {"messages": [None, {"type": "text", "id": "wamid.empty", "from": "5511"}]}}
                        ]
                    },
                ]
            }
        )

        self.assertEqual(parsed, [])

    def test_whatsapp_risk_message_generates_high_severity_handoff_response(self):
        response = self.client.post(
            "/webhook/whatsapp",
            json=whatsapp_text_payload("Está saindo cheiro de queimado do inversor", "wamid.risk-message"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(len(self.handled_payloads), 1)
        self.assertEqual(self.handled_payloads[0].message, "Está saindo cheiro de queimado do inversor")
        self.assertEqual(self.sent_messages[0][1], "Caso classificado como prioridade alta.")


if __name__ == "__main__":
    unittest.main()
