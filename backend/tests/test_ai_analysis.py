import unittest

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models import AIAnalysis, AuditLog, Conversation, Lead, Message, Proposal, Ticket, User, utc_now
from app.services.ai_analysis import AIAnalysisService


class FakeDb:
    def __init__(self, objects: dict[tuple[type, str], object] | None = None, scalar_queue: list[object | None] | None = None) -> None:
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
        class Result:
            def all(self):
                return []

        return Result()

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


def conversation_fixture(message: str = "Quero orçamento para minha casa") -> Conversation:
    conversation = Conversation(
        id="conversation-1",
        customer_id="customer-1",
        channel="site",
        status="open",
        intent="orcamento",
        severity="baixa",
        summary="Cliente quer orçamento de energia solar.",
        collected_data={"flow": "orcamento", "city_state": "São Paulo SP"},
        bot_resolved=False,
        transferred_to_human=False,
    )
    conversation.messages = [
        Message(
            id="message-1",
            conversation_id=conversation.id,
            sender_type="customer",
            content=message,
            created_at=utc_now(),
        )
    ]
    conversation.handoffs = []
    conversation.attachments = []
    return conversation


def hot_lead_fixture() -> Lead:
    return Lead(
        id="lead-1",
        customer_id="customer-1",
        conversation_id="conversation-1",
        property_type="residência",
        average_bill=850,
        utility_company="Enel",
        roof_type="cerâmica",
        financing_interest=True,
        status="Novo orçamento",
        notes="Cliente quer instalar e tem interesse em financiamento.",
        extra={
            "city_state": "Campinas SP",
            "has_energy_bill": "sim",
            "best_contact_time": "manhã",
            "property_type": "residência",
        },
    )


def critical_ticket_fixture() -> Ticket:
    return Ticket(
        id="ticket-1",
        customer_id="customer-1",
        conversation_id="conversation-1",
        problem_type="Cheiro de queimado no inversor",
        severity="alta",
        status="Novo",
        technical_notes="Cliente relatou cheiro de queimado e sistema parado.",
        extra={"started_at": "hoje", "generation_status": "parado"},
    )


def proposal_with_kit_fixture(lead: Lead) -> Proposal:
    return Proposal(
        id="proposal-1",
        customer_id=lead.customer_id,
        lead_id=lead.id,
        conversation_id=lead.conversation_id,
        proposal_number="SOL-20260603-KIT",
        status="draft",
        customer_name="Cliente Lead",
        recommended_kit_id="kit-1",
        recommended_kit_name="Kit Solar 2,75 kWp",
        kit_selection_reason="Kit escolhido por faixa de potencia estimada.",
        estimated_system_power_kwp=2.75,
        estimated_monthly_generation_kwh=313,
        subtotal=0,
        discount=0,
        total_amount=0,
        validity_days=7,
    )


class AIAnalysisServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_enable_ai = settings.enable_generative_ai
        self.original_openai_key = settings.openai_api_key
        settings.enable_generative_ai = False
        settings.openai_api_key = None

    def tearDown(self) -> None:
        settings.enable_generative_ai = self.original_enable_ai
        settings.openai_api_key = self.original_openai_key

    def test_rule_analysis_without_openai_masks_sensitive_data(self):
        conversation = conversation_fixture(
            "Meu CPF 12345678901 e telefone 5511988887777. Quero instalar energia solar."
        )
        db = FakeDb({(Conversation, conversation.id): conversation})

        analysis = AIAnalysisService(db).analyze_conversation(conversation.id)

        self.assertEqual(analysis.raw_analysis["mode"], "rules")
        self.assertNotIn("12345678901", analysis.executive_summary)
        self.assertNotIn("5511988887777", analysis.executive_summary)
        self.assertTrue([item for item in db.added if isinstance(item, AuditLog)])

    def test_hot_lead_analysis_generates_high_conversion_score(self):
        lead = hot_lead_fixture()
        db = FakeDb({(Lead, lead.id): lead})

        analysis = AIAnalysisService(db).analyze_lead(lead.id)

        self.assertGreaterEqual(analysis.priority_score, 75)
        self.assertEqual(analysis.conversion_probability, "alta")
        self.assertIn("lead_quente", analysis.tags)

    def test_critical_ticket_analysis_generates_critical_risk(self):
        ticket = critical_ticket_fixture()
        db = FakeDb({(Ticket, ticket.id): ticket})

        analysis = AIAnalysisService(db).analyze_ticket(ticket.id)

        self.assertGreaterEqual(analysis.priority_score, 85)
        self.assertEqual(analysis.technical_risk, "critico")
        self.assertIn("não mexa", analysis.suggested_reply.lower())

    def test_generate_suggested_reply_uses_rule_fallback(self):
        conversation = conversation_fixture()
        db = FakeDb({(Conversation, conversation.id): conversation})

        reply = AIAnalysisService(db).generate_suggested_reply(conversation.id)

        self.assertIn("análise", reply.lower())
        self.assertTrue([item for item in db.added if isinstance(item, AIAnalysis)])

    def test_fallback_when_generative_ai_disabled_even_with_key(self):
        settings.enable_generative_ai = False
        settings.openai_api_key = "fake-key"
        lead = hot_lead_fixture()
        db = FakeDb({(Lead, lead.id): lead})

        analysis = AIAnalysisService(db).analyze_lead(lead.id)

        self.assertEqual(analysis.raw_analysis["mode"], "rules")

    def test_lead_analysis_mentions_recommended_kit(self):
        lead = hot_lead_fixture()
        proposal = proposal_with_kit_fixture(lead)
        db = FakeDb({(Lead, lead.id): lead}, scalar_queue=[proposal])

        analysis = AIAnalysisService(db).analyze_lead(lead.id)

        self.assertIn("Kit Solar 2,75 kWp", analysis.recommended_next_action)
        self.assertIn("kit_recomendado", analysis.tags)


class AIAnalysisRoutesTest(unittest.TestCase):
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
        self.conversation = conversation_fixture()
        self.lead = hot_lead_fixture()
        self.ticket = critical_ticket_fixture()
        self.db = FakeDb(
            {
                (Conversation, self.conversation.id): self.conversation,
                (Lead, self.lead.id): self.lead,
                (Ticket, self.ticket.id): self.ticket,
            }
        )
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.user

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_conversation_analysis_endpoint(self):
        response = self.client.post(f"/ai/conversations/{self.conversation.id}/analyze")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analysis_type"], "conversation")
        self.assertIn("suggested_reply", response.json())

    def test_lead_analysis_endpoint(self):
        response = self.client.post(f"/ai/leads/{self.lead.id}/analyze")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analysis_type"], "lead")
        self.assertEqual(response.json()["conversion_probability"], "alta")

    def test_ticket_analysis_endpoint(self):
        response = self.client.post(f"/ai/tickets/{self.ticket.id}/analyze")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analysis_type"], "ticket")
        self.assertEqual(response.json()["technical_risk"], "critico")


if __name__ == "__main__":
    unittest.main()
