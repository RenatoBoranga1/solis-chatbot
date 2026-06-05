import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models import (
    Attachment,
    AuditLog,
    Conversation,
    Customer,
    EnergyBillExtraction,
    Lead,
    Proposal,
    ProposalKit,
    ProposalKitItem,
    User,
    utc_now,
)
from app.schemas import ChatMessageIn
from app.services.conversation import ConversationService
from app.services.energy_bill_extractor import EnergyBillExtractorService
from app.services.energy_bill_parsers.base import (
    PDF_BINARY_TEXT_NOTICE,
    sanitize_data_for_database,
    sanitize_raw_excerpt,
    sanitize_text_for_database,
)
from app.services.ocr import get_ocr_provider
from app.services.ocr.base import OcrResult


SAMPLE_BILL_TEXT = """
CPFL Paulista
Cliente: Renato Solar
CPF 123.456.789-01
Instalacao: 123456789
Cidade: Campinas SP
Referencia: 05/2026
Vencimento: 12/06/2026
Consumo faturado: 450 kWh
Total a pagar R$ 512,34
Historico de consumo
Jan/2026 390 kWh
Fev/2026 410 kWh
Mar/2026 440 kWh
Abr/2026 455 kWh
Mai/2026 450 kWh
"""


def contains_nul(value) -> bool:
    if isinstance(value, str):
        return "\x00" in value
    if isinstance(value, dict):
        return any(contains_nul(key) or contains_nul(item) for key, item in value.items())
    if isinstance(value, list):
        return any(contains_nul(item) for item in value)
    return False


class FakeScalarResult:
    def __init__(self, items):
        self.items = list(items)

    def all(self):
        return self.items


class FakeDb:
    def __init__(self, objects=None, scalar_queue=None, scalars_queue=None):
        self.objects = objects or {}
        self.scalar_queue = list(scalar_queue or [])
        self.scalars_queue = [list(items) for items in (scalars_queue or [])]
        self.added = []
        self.deleted = []
        self.commits = 0

    def get(self, model, item_id):
        return self.objects.get((model, item_id))

    def scalar(self, _statement):
        if self.scalar_queue:
            return self.scalar_queue.pop(0)
        for item in reversed(self.added):
            if isinstance(item, EnergyBillExtraction):
                return item
        return None

    def scalars(self, _statement):
        if self.scalars_queue:
            return FakeScalarResult(self.scalars_queue.pop(0))
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

    def rollback(self):
        return None

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


def customer_fixture() -> Customer:
    return Customer(
        id="customer-1",
        name="Cliente",
        phone="5511999999999",
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
        property_type="residencia",
        average_bill=None,
        utility_company=None,
        financing_interest=True,
        status="Novo orcamento",
        extra={},
        created_at=utc_now(),
    )


def conversation_fixture(customer: Customer) -> Conversation:
    conversation = Conversation(
        id="conversation-1",
        customer_id=customer.id,
        channel="site",
        status="commercial_triage",
        intent="orcamento",
        severity="baixa",
        collected_data={"flow": "orcamento"},
        created_at=utc_now(),
    )
    conversation.customer = customer
    return conversation


def kit_fixture() -> ProposalKit:
    kit = ProposalKit(
        id="kit-1",
        name="Kit 3,30 kWp",
        min_monthly_consumption_kwh=400,
        max_monthly_consumption_kwh=520,
        min_power_kwp=2.8,
        max_power_kwp=3.8,
        suggested_power_kwp=3.3,
        estimated_monthly_generation_kwh=460,
        module_count=6,
        module_power_wp=550,
        inverter_power_kw=4,
        base_price=18000,
        active=True,
        sort_order=0,
        created_at=utc_now(),
    )
    kit.items = [
        ProposalKitItem(
            id="kit-item-1",
            kit_id=kit.id,
            category="kit_fotovoltaico",
            description="Kit fotovoltaico 3,30 kWp",
            quantity=1,
            unit="kit",
            unit_price=18000,
            total_price=18000,
            sort_order=0,
            created_at=utc_now(),
        )
    ]
    return kit


class EnergyBillParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_ocr_enabled = settings.energy_bill_ocr_enabled
        self.original_ocr_provider = settings.energy_bill_ocr_provider
        self.original_allow_external_ai = settings.energy_bill_allow_external_ai
        self.original_min_text_length = settings.energy_bill_min_text_length

    def tearDown(self) -> None:
        settings.energy_bill_ocr_enabled = self.original_ocr_enabled
        settings.energy_bill_ocr_provider = self.original_ocr_provider
        settings.energy_bill_allow_external_ai = self.original_allow_external_ai
        settings.energy_bill_min_text_length = self.original_min_text_length

    def test_generic_parser_extracts_consumption_value_and_history(self):
        result = EnergyBillExtractorService(FakeDb()).parse_energy_bill_text(SAMPLE_BILL_TEXT)

        self.assertEqual(result.distributor, "CPFL")
        self.assertEqual(result.installation_number, "123456789")
        self.assertEqual(result.current_consumption_kwh, 450)
        self.assertEqual(result.current_bill_amount, 512.34)
        self.assertGreaterEqual(len(result.history), 5)
        self.assertEqual(result.average_consumption_kwh, 429)

    def test_sensitive_document_is_masked(self):
        result = EnergyBillExtractorService(FakeDb()).parse_energy_bill_text(SAMPLE_BILL_TEXT)

        self.assertEqual(result.customer_document_masked, "***.456.789-**")
        self.assertNotIn("123.456.789-01", sanitize_raw_excerpt(SAMPLE_BILL_TEXT))

    def test_sanitize_text_for_database_removes_nul_and_preserves_lines(self):
        value = sanitize_text_for_database("linha 1\x00\nlinha 2\tok\x01")

        self.assertEqual(value, "linha 1\nlinha 2\tok")

    def test_sanitize_raw_excerpt_hides_binary_pdf_payload(self):
        excerpt = sanitize_raw_excerpt("%PDF-1.4\x00obj\nconteudo binario")

        self.assertEqual(excerpt, PDF_BINARY_TEXT_NOTICE)

    def test_confidence_high_and_low(self):
        high = EnergyBillExtractorService(FakeDb()).parse_energy_bill_text(SAMPLE_BILL_TEXT)
        low = EnergyBillExtractorService(FakeDb()).parse_energy_bill_text("Consumo 120 kWh")

        self.assertGreaterEqual(high.confidence_score, settings.energy_bill_min_confidence_auto_apply)
        self.assertLess(low.confidence_score, settings.energy_bill_min_confidence_auto_apply)
        self.assertTrue(low.needs_human_review)

    def test_ocr_disabled_does_not_break(self):
        settings.energy_bill_ocr_enabled = False
        self.assertEqual(EnergyBillExtractorService(FakeDb()).extract_text_with_ocr("conta.png"), "")

    def test_image_uses_mocked_ocr_when_enabled(self):
        settings.energy_bill_ocr_enabled = True
        settings.energy_bill_ocr_provider = "local_tesseract"
        fake_provider = Mock()
        fake_provider.extract_text.return_value = OcrResult(SAMPLE_BILL_TEXT, "local_tesseract", True, 1)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "conta.png"
            path.write_bytes(b"fake-image")
            with patch("app.services.energy_bill_extractor.get_ocr_provider", return_value=fake_provider):
                extraction = EnergyBillExtractorService(FakeDb()).extract_from_file(str(path))

        self.assertEqual(extraction.status, "extracted")
        self.assertEqual(extraction.parsed_fields["ocr_used"], True)
        self.assertEqual(extraction.parsed_fields["ocr_provider"], "local_tesseract")
        self.assertEqual(extraction.parsed_fields["raw_text_source"], "ocr")

    def test_image_with_ocr_disabled_returns_controlled_failure(self):
        settings.energy_bill_ocr_enabled = False
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "conta.jpg"
            path.write_bytes(b"fake-image")
            extraction = EnergyBillExtractorService(FakeDb()).extract_from_file(str(path))

        self.assertEqual(extraction.status, "failed")
        self.assertIn("Ative OCR local", extraction.error_message)
        self.assertEqual(extraction.parsed_fields["ocr_used"], False)
        self.assertEqual(extraction.parsed_fields["ocr_provider"], "disabled")

    def test_textual_pdf_does_not_call_ocr(self):
        settings.energy_bill_ocr_enabled = True
        settings.energy_bill_ocr_provider = "local_tesseract"
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "conta.pdf"
            path.write_bytes(b"%PDF-1.7\n")
            with (
                patch.object(EnergyBillExtractorService, "extract_text_from_pdf", return_value=SAMPLE_BILL_TEXT),
                patch("app.services.energy_bill_extractor.get_ocr_provider") as provider_factory,
            ):
                extraction = EnergyBillExtractorService(FakeDb()).extract_from_file(str(path))

        provider_factory.assert_not_called()
        self.assertEqual(extraction.status, "extracted")
        self.assertEqual(extraction.parsed_fields["ocr_used"], False)
        self.assertEqual(extraction.parsed_fields["extraction_method"], "pdf_text")

    def test_extract_text_from_pdf_does_not_decode_raw_binary_bytes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "conta.pdf"
            path.write_bytes(b"%PDF-1.4\x00\x01conteudo binario sem texto")

            text = EnergyBillExtractorService(FakeDb()).extract_text_from_pdf(str(path))

        self.assertNotIn("%PDF-1.4", text)
        self.assertNotIn("\x00", text)

    def test_scanned_pdf_attempts_ocr_when_direct_text_is_insufficient(self):
        settings.energy_bill_ocr_enabled = True
        settings.energy_bill_ocr_provider = "local_tesseract"
        settings.energy_bill_min_text_length = 80
        fake_provider = Mock()
        fake_provider.extract_text.return_value = OcrResult(SAMPLE_BILL_TEXT, "local_tesseract", True, 2)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "conta.pdf"
            path.write_text("PDF", encoding="utf-8")
            with patch("app.services.energy_bill_extractor.get_ocr_provider", return_value=fake_provider):
                extraction = EnergyBillExtractorService(FakeDb()).extract_from_file(str(path))

        self.assertEqual(extraction.status, "extracted")
        self.assertEqual(extraction.parsed_fields["ocr_used"], True)
        self.assertEqual(extraction.parsed_fields["ocr_page_count"], 2)
        self.assertEqual(extraction.parsed_fields["extraction_method"], "ocr")

    def test_binary_pdf_with_nul_uses_ocr_and_never_stores_nul(self):
        settings.energy_bill_ocr_enabled = True
        settings.energy_bill_ocr_provider = "local_tesseract"
        fake_provider = Mock()
        fake_provider.extract_text.return_value = OcrResult(SAMPLE_BILL_TEXT + "\x00", "local_tesseract", True, 1)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "conta.pdf"
            path.write_bytes(b"%PDF-1.4\x00\x00obj\nconteudo binario")
            with patch("app.services.energy_bill_extractor.get_ocr_provider", return_value=fake_provider):
                extraction = EnergyBillExtractorService(FakeDb()).extract_from_file(str(path))

        self.assertEqual(extraction.status, "extracted")
        self.assertFalse(contains_nul(extraction.raw_text_excerpt))
        self.assertFalse(contains_nul(extraction.parsed_fields))
        self.assertFalse(contains_nul(extraction.raw_extraction))

    def test_pdf_without_text_and_ocr_disabled_returns_failed_without_nul(self):
        settings.energy_bill_ocr_enabled = False
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "conta.pdf"
            path.write_bytes(b"%PDF-1.4\x00\x00obj\nconteudo binario")
            extraction = EnergyBillExtractorService(FakeDb()).extract_from_file(
                str(path),
                {"file_name": "conta\x00.pdf", "ocr_error": "erro\x00controlado"},
            )

        self.assertEqual(extraction.status, "failed")
        self.assertTrue(extraction.needs_human_review)
        self.assertFalse(contains_nul(extraction.raw_text_excerpt))
        self.assertFalse(contains_nul(extraction.error_message))
        self.assertFalse(contains_nul(extraction.parsed_fields))
        self.assertFalse(contains_nul(extraction.raw_extraction))

    def test_sanitize_data_for_database_removes_nul_from_nested_json(self):
        payload = sanitize_data_for_database({"campo\x00": ["valor\x00", {"erro": "x\x00y"}]})

        self.assertFalse(contains_nul(payload))

    def test_external_ocr_provider_is_blocked_without_explicit_permission(self):
        settings.energy_bill_ocr_enabled = True
        settings.energy_bill_ocr_provider = "openai_vision"
        settings.energy_bill_allow_external_ai = False

        provider = get_ocr_provider(settings)
        result = provider.extract_text("conta.png")

        self.assertEqual(result.text, "")
        self.assertFalse(result.used)
        self.assertIn("ENERGY_BILL_ALLOW_EXTERNAL_AI=false", result.error)

    def test_ocr_failure_does_not_break_extraction(self):
        settings.energy_bill_ocr_enabled = True
        settings.energy_bill_ocr_provider = "local_tesseract"
        fake_provider = Mock()
        fake_provider.extract_text.return_value = OcrResult("", "local_tesseract", False, 0, "Tesseract indisponivel.")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "conta.webp"
            path.write_bytes(b"fake-image")
            with patch("app.services.energy_bill_extractor.get_ocr_provider", return_value=fake_provider):
                extraction = EnergyBillExtractorService(FakeDb()).extract_from_file(str(path))

        self.assertEqual(extraction.status, "failed")
        self.assertEqual(extraction.parsed_fields["ocr_error"], "Tesseract indisponivel.")
        self.assertIn("Tesseract indisponivel", extraction.error_message)

    def test_rejects_invalid_file_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "conta.exe"
            path.write_text("Consumo 100 kWh", encoding="utf-8")
            with self.assertRaises(ValueError):
                EnergyBillExtractorService(FakeDb()).extract_from_file(str(path))


class EnergyBillServiceTest(unittest.TestCase):
    def test_detects_possible_energy_bill_attachment_in_budget_context(self):
        customer = customer_fixture()
        conversation = conversation_fixture(customer)
        attachment = Attachment(
            id="attachment-1",
            message_id="message-1",
            conversation_id=conversation.id,
            provider="site",
            file_type="pdf",
            file_url="conta-de-energia.pdf",
            created_at=utc_now(),
        )

        detected = EnergyBillExtractorService(FakeDb()).is_possible_energy_bill_attachment(
            attachment,
            conversation,
            "Segue minha conta de energia",
            "orcamento",
            conversation.collected_data,
        )

        self.assertTrue(detected)

    def test_conversation_creates_pending_extraction_for_energy_bill_attachment(self):
        customer = customer_fixture()
        lead = lead_fixture(customer)
        conversation = conversation_fixture(customer)
        db = FakeDb(
            objects={(Conversation, conversation.id): conversation, (Customer, customer.id): customer, (Lead, lead.id): lead},
            scalar_queue=[None, lead],
        )

        response = ConversationService(db).handle_message(
            ChatMessageIn(
                conversation_id=conversation.id,
                customer_id=customer.id,
                message="Segue minha conta de energia em PDF",
                attachment_url="storage/chat_attachments/conta-energia.pdf",
                media_type="pdf",
            )
        )

        attachments = [item for item in db.added if isinstance(item, Attachment)]
        extractions = [item for item in db.added if isinstance(item, EnergyBillExtraction)]
        self.assertEqual(len(attachments), 1)
        self.assertEqual(len(extractions), 1)
        self.assertEqual(extractions[0].origin, "chatbot")
        self.assertEqual(extractions[0].status, "processing")
        self.assertIn("Recebi sua conta de energia", response.response)
        self.assertEqual(conversation.collected_data["energy_bill_extraction_id"], extractions[0].id)

    def test_conversation_does_not_create_extraction_without_lgpd_consent(self):
        customer = customer_fixture()
        customer.lgpd_consent = False
        conversation = conversation_fixture(customer)
        db = FakeDb(objects={(Conversation, conversation.id): conversation, (Customer, customer.id): customer}, scalar_queue=[conversation])

        ConversationService(db).handle_message(
            ChatMessageIn(
                conversation_id=conversation.id,
                customer_id=customer.id,
                message="Segue minha conta de energia",
                attachment_url="storage/chat_attachments/conta.pdf",
                media_type="pdf",
            )
        )

        self.assertFalse([item for item in db.added if isinstance(item, EnergyBillExtraction)])

    def test_unrelated_attachment_does_not_create_energy_bill_extraction(self):
        customer = customer_fixture()
        conversation = conversation_fixture(customer)
        conversation.intent = "suporte"
        conversation.status = "open"
        conversation.collected_data = {"flow": "suporte"}
        db = FakeDb(objects={(Conversation, conversation.id): conversation, (Customer, customer.id): customer}, scalar_queue=[conversation])

        ConversationService(db).handle_message(
            ChatMessageIn(
                conversation_id=conversation.id,
                customer_id=customer.id,
                message="Segue uma foto do local",
                attachment_url="storage/chat_attachments/foto.png",
                media_type="image",
            )
        )

        self.assertFalse([item for item in db.added if isinstance(item, EnergyBillExtraction)])

    def test_chatbot_image_ack_mentions_ocr_when_disabled(self):
        original = settings.energy_bill_ocr_enabled
        settings.energy_bill_ocr_enabled = False
        customer = customer_fixture()
        lead = lead_fixture(customer)
        conversation = conversation_fixture(customer)
        db = FakeDb(
            objects={(Conversation, conversation.id): conversation, (Customer, customer.id): customer, (Lead, lead.id): lead},
            scalar_queue=[None, lead],
        )
        try:
            response = ConversationService(db).handle_message(
                ChatMessageIn(
                    conversation_id=conversation.id,
                    customer_id=customer.id,
                    message="Segue foto da minha conta de energia",
                    attachment_url="storage/chat_attachments/conta.png",
                    media_type="image",
                )
            )
        finally:
            settings.energy_bill_ocr_enabled = original

        self.assertIn("OCR precisa estar habilitado", response.response)
        self.assertTrue([item for item in db.added if isinstance(item, EnergyBillExtraction)])

    def test_pending_extraction_processing_updates_conversation_and_lead(self):
        customer = customer_fixture()
        lead = lead_fixture(customer)
        conversation = conversation_fixture(customer)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "conta.txt"
            path.write_text(SAMPLE_BILL_TEXT, encoding="utf-8")
            attachment = Attachment(
                id="attachment-1",
                message_id="message-1",
                conversation_id=conversation.id,
                provider="site",
                file_type="txt",
                file_url=str(path),
                created_at=utc_now(),
            )
            db = FakeDb(
                objects={
                    (Attachment, attachment.id): attachment,
                    (Conversation, conversation.id): conversation,
                    (Customer, customer.id): customer,
                    (Lead, lead.id): lead,
                },
                scalar_queue=[None, lead],
            )
            service = EnergyBillExtractorService(db)
            pending = service.create_pending_from_attachment(attachment, conversation, customer, origin="chatbot")

            processed = service.process_pending_extraction(pending.id)

        self.assertEqual(processed.status, "extracted")
        self.assertEqual(processed.distributor, "CPFL")
        self.assertEqual(conversation.collected_data["utility_company"], "CPFL")
        self.assertEqual(conversation.collected_data["current_consumption_kwh"], 450.0)
        self.assertEqual(lead.utility_company, "CPFL")
        self.assertEqual(lead.extra["bill_extraction_origin"], "chatbot")

    def test_create_confirm_and_apply_to_lead(self):
        customer = customer_fixture()
        lead = lead_fixture(customer)
        conversation = conversation_fixture(customer)
        db = FakeDb(objects={(Lead, lead.id): lead, (Conversation, conversation.id): conversation, (Customer, customer.id): customer})
        service = EnergyBillExtractorService(db, admin_user())

        extraction = service.create_from_text(
            SAMPLE_BILL_TEXT,
            {"lead_id": lead.id, "conversation_id": conversation.id, "customer_id": customer.id},
        )
        confirmed = service.confirm_extraction(extraction.id)
        applied = service.apply_to_lead(confirmed.id, lead.id)

        self.assertEqual(confirmed.status, "confirmed")
        self.assertEqual(float(applied.average_bill), 512.34)
        self.assertEqual(applied.utility_company, "CPFL")
        self.assertEqual(applied.extra["average_consumption_kwh"], 429)
        self.assertTrue([item for item in db.added if isinstance(item, AuditLog)])

    def test_generate_proposal_from_extraction_selects_kit_by_average_consumption(self):
        customer = customer_fixture()
        lead = lead_fixture(customer)
        conversation = conversation_fixture(customer)
        extraction = EnergyBillExtractorService(FakeDb()).parse_energy_bill_text(SAMPLE_BILL_TEXT)
        extraction_model = EnergyBillExtraction(
            id="extraction-1",
            lead_id=lead.id,
            conversation_id=conversation.id,
            customer_id=customer.id,
            status="confirmed",
            source="text",
            origin="manual_text",
            distributor=extraction.distributor,
            current_bill_amount=extraction.current_bill_amount,
            average_bill_amount=extraction.average_bill_amount,
            average_consumption_kwh=extraction.average_consumption_kwh,
            estimated_system_power_kwp=extraction.estimated_system_power_kwp,
            estimated_monthly_generation_kwh=extraction.estimated_monthly_generation_kwh,
            confidence_score=extraction.confidence_score,
            needs_human_review=False,
            missing_fields=[],
            parsed_fields={},
            raw_extraction={},
            created_at=utc_now(),
        )
        db = FakeDb(
            objects={(Lead, lead.id): lead, (Conversation, conversation.id): conversation, (Customer, customer.id): customer},
            scalar_queue=[extraction_model, extraction_model, None],
            scalars_queue=[[], [kit_fixture()]],
        )

        proposal = EnergyBillExtractorService(db, admin_user()).generate_proposal(extraction_model.id)

        self.assertIsInstance(proposal, Proposal)
        self.assertEqual(proposal.recommended_kit_name, "Kit 3,30 kWp")
        self.assertEqual(float(proposal.estimated_monthly_generation_kwh), 460)
        self.assertIn("Consumo medio", proposal.internal_notes)


class EnergyBillRoutesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.user = admin_user()
        self.db = FakeDb()
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.user

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_parse_text_endpoint(self):
        response = self.client.post("/energy-bills/parse-text", json={"raw_text": SAMPLE_BILL_TEXT, "metadata": {}})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["distributor"], "CPFL")
        self.assertEqual(payload["current_consumption_kwh"], 450)
        self.assertNotIn("123.456.789-01", str(payload))

    def test_list_endpoint_returns_origin(self):
        extraction = EnergyBillExtraction(
            id="extraction-1",
            status="processing",
            source="site",
            origin="chatbot",
            confidence_score=0,
            needs_human_review=True,
            missing_fields=[],
            parsed_fields={},
            raw_extraction={},
            created_at=utc_now(),
        )
        self.db.scalars_queue = [[extraction]]

        response = self.client.get("/energy-bills")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload[0]["origin"], "chatbot")

    def test_upload_binary_pdf_returns_controlled_failed_extraction_without_500(self):
        original = settings.energy_bill_ocr_enabled
        settings.energy_bill_ocr_enabled = False
        try:
            response = self.client.post(
                "/energy-bills/extract",
                files={"file": ("conta.pdf", b"%PDF-1.4\x00\x00obj\nconteudo binario", "application/pdf")},
            )
        finally:
            settings.energy_bill_ocr_enabled = original

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["status"], "failed")
        self.assertTrue(payload["needs_human_review"])
        self.assertNotIn("\x00", str(payload))


if __name__ == "__main__":
    unittest.main()
