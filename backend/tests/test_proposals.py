import tempfile
import unittest
from datetime import timedelta

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models import (
    AuditLog,
    CompanySettings,
    Conversation,
    Customer,
    Lead,
    Proposal,
    ProposalCustomerResponse,
    ProposalEvent,
    ProposalFollowUp,
    ProposalItem,
    ProposalPriceItem,
    ProposalShareLink,
    User,
    utc_now,
)
from app.schemas import (
    ProposalCustomerResponseIn,
    ProposalCreate,
    ProposalFollowUpCreate,
    ProposalItemCreate,
    ProposalItemUpdate,
    ProposalPriceItemCreate,
    ProposalPriceItemUpdate,
    ProposalShareLinkCreate,
    ProposalSendRequest,
    ProposalUpdate,
)
from app.services.proposals import ProposalService


class FakeScalarResult:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


class FakeDb:
    def __init__(self, objects=None, scalar_queue=None, scalar_items=None):
        self.objects = objects or {}
        self.scalar_queue = list(scalar_queue or [])
        self.scalar_items = list(scalar_items or [])
        self.added = []
        self.deleted = []
        self.commits = 0

    def get(self, model, item_id):
        return self.objects.get((model, item_id))

    def scalar(self, _statement):
        if self.scalar_queue:
            return self.scalar_queue.pop(0)
        return None

    def scalars(self, _statement):
        return FakeScalarResult(self.scalar_items)

    def add(self, obj):
        self.added.append(obj)

    def delete(self, obj):
        self.deleted.append(obj)

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


def admin_user() -> User:
    return User(
        id="user-admin",
        name="Admin",
        email="admin@solarsolucoes.com.br",
        password_hash="hash",
        role="admin",
        active=True,
        created_at=utc_now(),
    )


def support_user() -> User:
    user = admin_user()
    user.id = "user-support"
    user.role = "suporte"
    return user


def customer_fixture() -> Customer:
    return Customer(
        id="customer-1",
        name="Cliente Proposta",
        phone="5511999998888",
        email="cliente@example.com",
        city="Campinas",
        state="SP",
        lgpd_consent=True,
        created_at=utc_now(),
    )


def lead_fixture(customer: Customer) -> Lead:
    return Lead(
        id="lead-1",
        customer_id=customer.id,
        conversation_id="conversation-1",
        property_type="residência",
        average_bill=850,
        utility_company="CPFL",
        roof_type="cerâmica",
        financing_interest=True,
        status="Novo orçamento",
        notes="Cliente pronto para proposta.",
        extra={"city_state": "Campinas SP", "has_energy_bill": "sim"},
        created_at=utc_now(),
    )


def conversation_fixture(customer: Customer) -> Conversation:
    return Conversation(
        id="conversation-1",
        customer_id=customer.id,
        channel="site",
        status="commercial_triage",
        intent="orcamento",
        severity="baixa",
        summary="Lead de orçamento completo.",
        collected_data={"flow": "orcamento", "average_bill": "850", "property_type": "residência"},
        created_at=utc_now(),
    )


def proposal_fixture() -> Proposal:
    proposal = Proposal(
        id="proposal-1",
        customer_id="customer-1",
        proposal_number="SOL-20260601-ABC123",
        status="draft",
        customer_name="Cliente Proposta",
        city="Campinas",
        state="SP",
        property_type="residência",
        average_bill=850,
        validity_days=7,
        subtotal=1000,
        discount=0,
        total_amount=1000,
        payment_conditions="A definir.",
        notes="Rascunho revisável.",
        created_at=utc_now(),
    )
    proposal.items = [
        ProposalItem(
            id="item-1",
            proposal_id=proposal.id,
            category="kit_fotovoltaico",
            description="Kit",
            quantity=2,
            unit="un",
            unit_price=500,
            total_price=1000,
            editable=True,
            sort_order=0,
            created_at=utc_now(),
        )
    ]
    return proposal


def price_item_fixture() -> ProposalPriceItem:
    return ProposalPriceItem(
        id="price-1",
        category="kit_fotovoltaico",
        description="Kit fotovoltaico configurado",
        default_unit="un",
        default_quantity=1,
        default_unit_price=12000,
        active=True,
        sort_order=0,
        notes="Valor base para revisao humana.",
        created_at=utc_now(),
    )


def company_settings_fixture() -> CompanySettings:
    return CompanySettings(
        id="company-1",
        company_name="Solar Solucoes",
        company_phone="(11) 99999-0000",
        company_email="contato@solarsolucoes.com.br",
        company_website="https://solarsolucoes.com.br",
        company_address="Endereco comercial",
        company_logo_url=None,
        primary_color="#FFCC33",
        secondary_color="#0B1F33",
        default_payment_conditions="Entrada e saldo conforme proposta.",
        default_proposal_validity_days=12,
        default_proposal_notes="Observacao padrao de teste.",
        created_at=utc_now(),
    )


def share_link_fixture(proposal: Proposal) -> ProposalShareLink:
    return ProposalShareLink(
        id="share-1",
        proposal_id=proposal.id,
        token="token-publico-teste",
        expires_at=utc_now() + timedelta(days=10),
        revoked_at=None,
        views_count=0,
        created_by="user-admin",
        created_at=utc_now(),
    )


class ProposalServiceTest(unittest.TestCase):
    def test_create_manual_proposal_calculates_totals_and_audits(self):
        db = FakeDb()
        proposal = ProposalService(db, admin_user()).create_proposal(
            ProposalCreate(
                customer_name="Cliente Manual",
                discount=100,
                items=[
                    ProposalItemCreate(
                        category="kit_fotovoltaico",
                        description="Kit fotovoltaico",
                        quantity=2,
                        unit="un",
                        unit_price=750,
                    )
                ],
            )
        )

        self.assertEqual(proposal.subtotal, 1500)
        self.assertEqual(proposal.total_amount, 1400)
        self.assertTrue([item for item in db.added if isinstance(item, AuditLog)])

    def test_create_from_lead_adds_default_items(self):
        customer = customer_fixture()
        lead = lead_fixture(customer)
        conversation = conversation_fixture(customer)
        db = FakeDb(objects={(Lead, lead.id): lead, (Customer, customer.id): customer, (Conversation, conversation.id): conversation})

        proposal = ProposalService(db, admin_user()).create_from_lead(lead.id)

        self.assertEqual(proposal.lead_id, lead.id)
        self.assertEqual(proposal.customer_name, customer.name)
        self.assertGreaterEqual(len(proposal.items), 7)
        self.assertEqual(proposal.status, "draft")
        self.assertIn("rascunho", proposal.notes.lower())
        self.assertTrue(all(float(item.unit_price or 0) == 0 for item in proposal.items))

    def test_create_from_lead_uses_configured_price_table(self):
        customer = customer_fixture()
        lead = lead_fixture(customer)
        conversation = conversation_fixture(customer)
        price_item = price_item_fixture()
        db = FakeDb(
            objects={(Lead, lead.id): lead, (Customer, customer.id): customer, (Conversation, conversation.id): conversation},
            scalar_items=[price_item],
        )

        proposal = ProposalService(db, admin_user()).create_from_lead(lead.id)

        self.assertEqual(len(proposal.items), 1)
        self.assertEqual(proposal.items[0].description, price_item.description)
        self.assertEqual(proposal.total_amount, 12000)
        self.assertIn("tabela de precos", proposal.internal_notes.lower())

    def test_update_item_and_discount_recalculate_total(self):
        proposal = proposal_fixture()
        db = FakeDb(scalar_queue=[proposal, proposal])
        service = ProposalService(db, admin_user())

        updated = service.update_item(
            proposal.id,
            "item-1",
            ProposalItemUpdate(quantity=3, unit_price=600),
        )
        self.assertEqual(updated.subtotal, 1800)

        updated = service.update_proposal(proposal.id, ProposalUpdate(discount=300))
        self.assertEqual(updated.total_amount, 1500)

    def test_status_pdf_and_send(self):
        proposal = proposal_fixture()
        with tempfile.TemporaryDirectory() as tmpdir:
            original_storage = settings.proposal_storage_path
            settings.proposal_storage_path = tmpdir
            try:
                db = FakeDb(scalar_queue=[proposal, proposal, None, proposal])
                service = ProposalService(db, admin_user())
                service.update_status(proposal.id, "approved")
                self.assertEqual(proposal.status, "approved")

                with_pdf = service.generate_pdf(proposal.id)
                self.assertTrue(with_pdf.pdf_url.endswith(".pdf"))
                self.assertEqual(with_pdf.status, "ready_to_send")

                result = service.send(proposal.id, ProposalSendRequest(channel="manual"))
                self.assertEqual(result.status, "ready")
                self.assertEqual(result.channel, "manual")
                self.assertEqual(proposal.status, "ready_to_send")
            finally:
                settings.proposal_storage_path = original_storage

    def test_price_item_crud_and_active_toggle(self):
        price_item = price_item_fixture()
        db = FakeDb(objects={(ProposalPriceItem, price_item.id): price_item})
        service = ProposalService(db, admin_user())

        created = service.create_price_item(
            ProposalPriceItemCreate(
                category="mao_de_obra",
                description="Mao de obra especializada",
                default_unit="servico",
                default_quantity=1,
                default_unit_price=3500,
            )
        )
        self.assertEqual(created.default_unit_price, 3500)

        updated = service.update_price_item(price_item.id, ProposalPriceItemUpdate(default_unit_price=15000))
        self.assertEqual(updated.default_unit_price, 15000)

        inactive = service.set_price_item_active(price_item.id, False)
        self.assertFalse(inactive.active)
        self.assertTrue([item for item in db.added if isinstance(item, AuditLog)])

    def test_apply_price_table_to_existing_proposal(self):
        proposal = proposal_fixture()
        price_item = price_item_fixture()
        db = FakeDb(scalar_queue=[proposal], scalar_items=[price_item])

        updated = ProposalService(db, admin_user()).apply_price_table(proposal.id)

        self.assertEqual(len(updated.items), 1)
        self.assertEqual(updated.items[0].unit_price, 12000)
        self.assertEqual(updated.total_amount, 12000)
        self.assertTrue(db.deleted)

    def test_send_channels_are_simulated_in_development(self):
        proposal = proposal_fixture()
        original_env = settings.app_env
        settings.app_env = "development"
        try:
            db = FakeDb(scalar_queue=[proposal, None, None, proposal, None])
            service = ProposalService(db, admin_user())
            whatsapp = service.send(proposal.id, ProposalSendRequest(channel="whatsapp", recipient_phone="5511999998888"))
            email = service.send(proposal.id, ProposalSendRequest(channel="email", recipient_email="cliente@example.com"))

            self.assertEqual(whatsapp.status, "simulated")
            self.assertEqual(email.status, "simulated")
            self.assertEqual(proposal.status, "sent")
            self.assertTrue([item for item in db.added if isinstance(item, ProposalShareLink)])
            self.assertTrue([item for item in db.added if isinstance(item, ProposalFollowUp)])
        finally:
            settings.app_env = original_env

    def test_production_send_without_whatsapp_credentials_returns_error(self):
        proposal = proposal_fixture()
        original_env = settings.app_env
        settings.app_env = "production"
        try:
            db = FakeDb(scalar_queue=[proposal, None, None])
            result = ProposalService(db, admin_user()).send(
                proposal.id,
                ProposalSendRequest(channel="whatsapp", recipient_phone="5511999998888"),
            )

            self.assertEqual(result.status, "error")
            self.assertIn("WhatsApp", result.message)
        finally:
            settings.app_env = original_env

    def test_create_share_link_records_auditable_link(self):
        proposal = proposal_fixture()
        db = FakeDb(scalar_queue=[proposal])

        link = ProposalService(db, admin_user()).create_share_link(proposal.id, ProposalShareLinkCreate(expires_in_days=5))

        self.assertEqual(link.proposal_id, proposal.id)
        self.assertIsNotNone(link.token)
        self.assertGreaterEqual((link.expires_at - utc_now()).days, 4)
        self.assertTrue([item for item in db.added if isinstance(item, ProposalEvent)])
        self.assertTrue([item for item in db.added if isinstance(item, AuditLog)])

    def test_public_proposal_increments_view_and_returns_company_settings(self):
        proposal = proposal_fixture()
        link = share_link_fixture(proposal)
        company = company_settings_fixture()
        db = FakeDb(scalar_queue=[link, proposal, company])

        public_proposal, public_link, public_company = ProposalService(db).get_public_proposal(link.token)

        self.assertEqual(public_proposal.id, proposal.id)
        self.assertEqual(public_company.company_name, company.company_name)
        self.assertEqual(public_link.views_count, 1)
        self.assertTrue([item for item in db.added if isinstance(item, ProposalEvent)])

    def test_register_customer_acceptance_updates_status_and_response(self):
        proposal = proposal_fixture()
        proposal.status = "sent"
        link = share_link_fixture(proposal)
        db = FakeDb(scalar_queue=[link, proposal])

        response = ProposalService(db, admin_user()).register_customer_response(
            link.token,
            ProposalCustomerResponseIn(
                response_type="accepted",
                customer_name="Cliente Proposta",
                customer_email="cliente@example.com",
                message="Aprovado.",
            ),
        )

        self.assertIsInstance(response, ProposalCustomerResponse)
        self.assertEqual(response.response_type, "accepted")
        self.assertEqual(proposal.status, "accepted")
        self.assertTrue([item for item in db.added if isinstance(item, ProposalEvent)])

    def test_create_and_complete_followup(self):
        proposal = proposal_fixture()
        followup_due = utc_now() + timedelta(days=1)
        db = FakeDb(scalar_queue=[proposal])
        service = ProposalService(db, admin_user())

        followup = service.create_followup(
            proposal.id,
            ProposalFollowUpCreate(due_at=followup_due, channel="whatsapp", note="Retornar proposta"),
        )

        self.assertEqual(followup.status, "pending")
        self.assertEqual(followup.channel, "whatsapp")

        db.objects[(ProposalFollowUp, followup.id)] = followup
        db.objects[(Proposal, proposal.id)] = proposal
        completed = service.complete_followup(followup.id)
        self.assertEqual(completed.status, "completed")
        self.assertIsNotNone(completed.completed_at)

    def test_company_settings_fallback_uses_environment_defaults(self):
        db = FakeDb()

        company = ProposalService(db, admin_user()).get_company_settings()

        self.assertEqual(company.company_name, settings.company_name)
        self.assertEqual(company.default_proposal_validity_days, 7)
        self.assertTrue([item for item in db.added if isinstance(item, CompanySettings)])


class ProposalRoutesPermissionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.proposal = proposal_fixture()
        self.db = FakeDb(scalar_queue=[self.proposal])
        app.dependency_overrides[get_db] = lambda: self.db

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_support_cannot_send_proposal(self):
        app.dependency_overrides[get_current_user] = support_user

        response = self.client.post(f"/proposals/{self.proposal.id}/send", json={"channel": "manual"})

        self.assertEqual(response.status_code, 403)

    def test_admin_can_send_proposal(self):
        app.dependency_overrides[get_current_user] = admin_user

        response = self.client.post(f"/proposals/{self.proposal.id}/send", json={"channel": "manual"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")

    def test_support_cannot_manage_price_table(self):
        app.dependency_overrides[get_current_user] = support_user

        response = self.client.post(
            "/proposal-price-items",
            json={
                "category": "kit_fotovoltaico",
                "description": "Kit",
                "default_unit": "un",
                "default_quantity": 1,
                "default_unit_price": 1000,
            },
        )

        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
