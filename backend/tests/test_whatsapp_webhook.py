import unittest

from fastapi.testclient import TestClient

from app.api import routes_whatsapp
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.schemas import ChatMessageOut
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


class FakeDb:
    def __init__(self, duplicate: bool = False) -> None:
        self.duplicate = duplicate

    def scalar(self, _statement):
        return "existing-message-id" if self.duplicate else None


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

    def test_post_webhook_ignores_duplicate_message(self):
        self.fake_db.duplicate = True

        response = self.client.post("/webhook/whatsapp", json=whatsapp_text_payload())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "duplicate_ignored")
        self.assertEqual(response.json()["duplicates"], 1)
        self.assertEqual(self.handled_payloads, [])
        self.assertEqual(self.sent_messages, [])

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
