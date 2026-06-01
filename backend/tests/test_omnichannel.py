import unittest

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.phone import normalize_phone
from app.db.session import get_db
from app.main import app
from app.models import Conversation, ConversationChannelLink, Customer, Lead, Message, User, utc_now
from app.schemas import ChatMessageIn, ContinueWhatsAppIn
from app.services.conversation import ConversationService
from app.services.omnichannel import OmnichannelService


class FakeScalarResult:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


class FakeDb:
    def __init__(self, objects=None, scalar_queue=None):
        self.objects = objects or {}
        self.scalar_queue = list(scalar_queue or [])
        self.added = []
        self.commits = 0

    def get(self, model, item_id):
        return self.objects.get((model, item_id))

    def scalar(self, _statement):
        if self.scalar_queue:
            return self.scalar_queue.pop(0)
        return None

    def scalars(self, _statement):
        return FakeScalarResult([])

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        for index, obj in enumerate(self.added, start=1):
            if getattr(obj, "id", None) is None:
                setattr(obj, "id", f"fake-id-{index}")
            if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
                setattr(obj, "created_at", utc_now())

    def commit(self):
        self.commits += 1

    def refresh(self, _obj):
        return None


def customer_fixture() -> Customer:
    return Customer(
        id="customer-1",
        name="Renato Cliente",
        phone="5511999998888",
        lgpd_consent=True,
        created_at=utc_now(),
    )


def site_conversation_fixture(customer: Customer, severity: str = "baixa") -> Conversation:
    conversation = Conversation(
        id="site-conversation-1",
        customer_id=customer.id,
        channel="site",
        status="commercial_triage",
        intent="orcamento",
        severity=severity,
        summary="Cliente quer orçamento e informou dados iniciais.",
        collected_data={"flow": "orcamento", "city_state": "Campinas SP", "average_bill": "850"},
        bot_resolved=False,
        transferred_to_human=True,
        created_at=utc_now(),
    )
    conversation.customer = customer
    conversation.messages = []
    conversation.handoffs = []
    conversation.attachments = []
    conversation.outbound_channel_links = []
    conversation.inbound_channel_links = []
    return conversation


def lead_fixture(customer: Customer, conversation: Conversation) -> Lead:
    return Lead(
        id="lead-1",
        customer_id=customer.id,
        conversation_id=conversation.id,
        property_type="residência",
        average_bill=850,
        utility_company="CPFL",
        financing_interest=True,
        status="Novo orçamento",
        notes="Lead captado pelo site.",
        extra={"city_state": "Campinas SP"},
        created_at=utc_now(),
    )


class OmnichannelServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_env = settings.app_env
        self.original_token = settings.whatsapp_access_token
        self.original_phone_id = settings.whatsapp_phone_number_id
        settings.app_env = "development"
        settings.whatsapp_access_token = None
        settings.whatsapp_phone_number_id = None

    def tearDown(self) -> None:
        settings.app_env = self.original_env
        settings.whatsapp_access_token = self.original_token
        settings.whatsapp_phone_number_id = self.original_phone_id

    def test_normalize_phone_returns_digits_only(self):
        self.assertEqual(normalize_phone("(11) 99999-8888"), "11999998888")

    def test_create_site_to_whatsapp_link_simulates_invitation_in_development(self):
        customer = customer_fixture()
        conversation = site_conversation_fixture(customer)
        lead = lead_fixture(customer, conversation)
        db = FakeDb(
            objects={(Conversation, conversation.id): conversation, (Customer, customer.id): customer},
            scalar_queue=[lead, None, None],
        )

        result = OmnichannelService(db).continue_on_whatsapp(conversation.id, ContinueWhatsAppIn())

        links = [item for item in db.added if isinstance(item, ConversationChannelLink)]
        self.assertEqual(result.status, "simulated")
        self.assertTrue(links)
        self.assertEqual(links[0].source_conversation_id, conversation.id)
        self.assertEqual(links[0].target_channel, "whatsapp")
        self.assertEqual(links[0].lead_id, lead.id)
        self.assertEqual(links[0].status, "invited")

    def test_continue_whatsapp_requires_phone(self):
        customer = customer_fixture()
        customer.phone = None
        conversation = site_conversation_fixture(customer)
        db = FakeDb(objects={(Conversation, conversation.id): conversation, (Customer, customer.id): customer})

        with self.assertRaises(ValueError):
            OmnichannelService(db).continue_on_whatsapp(conversation.id, ContinueWhatsAppIn())

    def test_high_severity_requires_human_review(self):
        customer = customer_fixture()
        conversation = site_conversation_fixture(customer, severity="alta")
        db = FakeDb(objects={(Conversation, conversation.id): conversation, (Customer, customer.id): customer})

        with self.assertRaises(PermissionError):
            OmnichannelService(db).continue_on_whatsapp(conversation.id, ContinueWhatsAppIn())

    def test_whatsapp_confirmation_creates_linked_conversation_with_context(self):
        customer = customer_fixture()
        source = site_conversation_fixture(customer)
        link = ConversationChannelLink(
            id="link-1",
            customer_id=customer.id,
            source_conversation_id=source.id,
            source_channel="site",
            target_channel="whatsapp",
            external_id=customer.phone,
            phone=customer.phone,
            lead_id="lead-1",
            status="invited",
            created_at=utc_now(),
        )
        db = FakeDb(
            objects={(Customer, customer.id): customer, (Conversation, source.id): source},
            scalar_queue=[customer, link],
        )

        response = ConversationService(db).handle_message(
            ChatMessageIn(
                channel="whatsapp",
                external_id=customer.phone,
                message="SIM",
                customer={"name": customer.name, "phone": customer.phone},
            )
        )

        conversations = [item for item in db.added if isinstance(item, Conversation) and item.channel == "whatsapp"]
        messages = [item for item in db.added if isinstance(item, Message)]
        self.assertTrue(conversations)
        self.assertEqual(link.status, "confirmed")
        self.assertEqual(link.target_conversation_id, conversations[0].id)
        self.assertEqual(conversations[0].collected_data["source_conversation_id"], source.id)
        self.assertEqual(conversations[0].collected_data["migrated_from_channel"], "site")
        self.assertIn("conta de energia", response.response.lower())
        self.assertTrue(messages)


class OmnichannelRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.user = User(
            id="user-1",
            name="Admin",
            email="admin@solarsolucoes.com.br",
            password_hash="hash",
            role="admin",
            active=True,
            created_at=utc_now(),
        )
        self.customer = customer_fixture()
        self.conversation = site_conversation_fixture(self.customer)
        self.db = FakeDb(
            objects={(Conversation, self.conversation.id): self.conversation, (Customer, self.customer.id): self.customer},
            scalar_queue=[None, None, None],
        )
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.user

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_continue_whatsapp_endpoint_returns_simulated_status(self):
        response = self.client.post(f"/chat/conversations/{self.conversation.id}/continue-whatsapp", json={})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "simulated")
        self.assertEqual(response.json()["phone"], self.customer.phone)
        self.assertIn("conversation_channel_link_id", response.json())


if __name__ == "__main__":
    unittest.main()
