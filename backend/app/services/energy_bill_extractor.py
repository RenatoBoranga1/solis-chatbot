from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import (
    Attachment,
    AuditLog,
    Conversation,
    Customer,
    EnergyBillConsumptionHistory,
    EnergyBillExtraction,
    Lead,
    Proposal,
    User,
    utc_now,
)
from app.schemas import EnergyBillExtractionConfirm, EnergyBillExtractionUpdate
from app.services.energy_bill_parsers import CPFLEnergyBillParser, GenericEnergyBillParser
from app.services.energy_bill_parsers.base import (
    ConsumptionHistoryItem,
    EnergyBillParseResult,
    sanitize_raw_excerpt,
)
from app.services.proposals import ProposalService

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
ENERGY_BILL_TERMS = {
    "conta de energia",
    "conta de luz",
    "fatura de energia",
    "fatura",
    "boleto de energia",
    "cpfl",
    "enel",
    "cemig",
    "neoenergia",
    "equatorial",
    "energisa",
    "kwh",
    "uc",
    "unidade consumidora",
    "distribuidora",
}
BILL_ATTACHMENT_TYPES = {"pdf", "image", "jpg", "jpeg", "png", "webp"}


class EnergyBillExtractorService:
    def __init__(self, db: Session, actor: User | None = None) -> None:
        self.db = db
        self.actor = actor
        self.parsers = [CPFLEnergyBillParser(), GenericEnergyBillParser()]

    def list_extractions(self, status: str | None = None, lead_id: str | None = None) -> list[EnergyBillExtraction]:
        statement = (
            select(EnergyBillExtraction)
            .options(selectinload(EnergyBillExtraction.history))
            .order_by(desc(EnergyBillExtraction.created_at))
            .limit(300)
        )
        if status:
            statement = statement.where(EnergyBillExtraction.status == status)
        if lead_id:
            statement = statement.where(EnergyBillExtraction.lead_id == lead_id)
        return list(self.db.scalars(statement).all())

    def get_extraction(self, extraction_id: str) -> EnergyBillExtraction:
        extraction = self.db.scalar(
            select(EnergyBillExtraction)
            .where(EnergyBillExtraction.id == extraction_id)
            .options(selectinload(EnergyBillExtraction.history))
        )
        if not extraction:
            raise ValueError("Energy bill extraction not found")
        return extraction

    def is_possible_energy_bill_attachment(
        self,
        attachment: Attachment,
        conversation: Conversation,
        message_text: str,
        intent: str | None = None,
        collected: dict[str, Any] | None = None,
    ) -> bool:
        if not settings.energy_bill_extraction_enabled:
            return False
        file_type = (attachment.file_type or "").lower()
        file_url = attachment.file_url or ""
        suffix = Path(file_url.split("?", 1)[0]).suffix.lower()
        is_readable_file = file_type in BILL_ATTACHMENT_TYPES or suffix in ALLOWED_EXTENSIONS
        if not is_readable_file:
            return False

        collected = collected or {}
        context_text = " ".join(
            [
                message_text or "",
                file_url,
                str(intent or ""),
                str(conversation.intent or ""),
                str(collected.get("flow") or ""),
                str(collected.get("last_question_key") or ""),
            ]
        ).lower()
        commercial_context = (
            (intent in {"orcamento", "viabilidade", "financiamento"})
            or conversation.intent in {"orcamento", "viabilidade", "financiamento"}
            or collected.get("flow") == "orcamento"
            or conversation.status in {"commercial_triage", "proposal_pending"}
        )
        has_bill_hint = any(term in context_text for term in ENERGY_BILL_TERMS)
        explicit_upload_context = collected.get("last_question_key") == "has_energy_bill" or collected.get("has_energy_bill") == "sim"
        return bool(commercial_context and (has_bill_hint or explicit_upload_context))

    def create_pending_from_attachment(
        self,
        attachment: Attachment,
        conversation: Conversation | None = None,
        customer: Customer | None = None,
        origin: str | None = None,
        message_text: str | None = None,
    ) -> EnergyBillExtraction:
        existing = self.db.scalar(select(EnergyBillExtraction).where(EnergyBillExtraction.attachment_id == attachment.id))
        if existing:
            return existing

        conversation = conversation or self.db.get(Conversation, attachment.conversation_id)
        customer_id = customer.id if customer else conversation.customer_id if conversation else None
        lead = self._lead_for_conversation(conversation.id) if conversation else None
        extraction = EnergyBillExtraction(
            conversation_id=conversation.id if conversation else attachment.conversation_id,
            customer_id=customer_id,
            lead_id=lead.id if lead else None,
            attachment_id=attachment.id,
            status="processing",
            source=attachment.provider or "attachment",
            origin=origin or self._origin_from_source(attachment.provider),
            file_name=self._safe_file_name(attachment.file_url),
            file_type=attachment.file_type,
            file_url=attachment.file_url,
            confidence_score=0,
            needs_human_review=True,
            missing_fields=[],
            parsed_fields={
                "auto_created": True,
                "origin": origin or self._origin_from_source(attachment.provider),
                "message_hint": sanitize_raw_excerpt(message_text or "", limit=300),
            },
            raw_extraction={},
        )
        self.db.add(extraction)
        self.db.flush()
        self._update_linked_conversation(extraction)
        self._audit("energy_bill.extraction_created", extraction, {"origin": extraction.origin, "status": extraction.status})
        return extraction

    def process_pending_extraction(self, extraction_id: str) -> EnergyBillExtraction:
        extraction = self.get_extraction(extraction_id)
        if not extraction.attachment_id:
            return extraction
        attachment = extraction.attachment or self.db.get(Attachment, extraction.attachment_id)
        if not attachment or not attachment.file_url:
            self._mark_extraction_failed(extraction, "Arquivo nao encontrado para leitura automatica.")
            self.db.commit()
            self.db.refresh(extraction)
            return self.get_extraction(extraction.id)
        if attachment.file_url.startswith("whatsapp://"):
            self._mark_extraction_failed(extraction, "Midia do WhatsApp ainda nao foi baixada para leitura automatica.")
            self.db.commit()
            self.db.refresh(extraction)
            return self.get_extraction(extraction.id)

        path = Path(attachment.file_url)
        try:
            self._validate_file(path)
            text = self._extract_text(path)
            if not text.strip():
                self._mark_extraction_failed(extraction, "Nao foi possivel extrair texto do arquivo.")
                self.db.commit()
                self.db.refresh(extraction)
                return self.get_extraction(extraction.id)
            result = self.parse_energy_bill_text(text, self._metadata_for_existing_extraction(extraction, path))
            self._fill_extraction_from_result(extraction, result, text)
            self._replace_history(extraction, result.history)
            self._update_linked_conversation(extraction)
            if extraction.lead_id:
                lead = self.db.get(Lead, extraction.lead_id)
                if lead:
                    self._sync_extraction_to_lead(extraction, lead)
            self._audit("energy_bill.extracted", extraction, {"status": extraction.status, "origin": extraction.origin})
            self.db.commit()
            self.db.refresh(extraction)
            return self.get_extraction(extraction.id)
        except Exception as exc:
            logger.warning("Energy bill background extraction failed for extraction %s.", extraction.id)
            self._mark_extraction_failed(extraction, str(exc))
            self.db.commit()
            self.db.refresh(extraction)
            return self.get_extraction(extraction.id)

    def extract_from_attachment(self, attachment_id: str) -> EnergyBillExtraction:
        attachment = self.db.get(Attachment, attachment_id)
        if not attachment:
            raise ValueError("Attachment not found")
        metadata = {
            "attachment_id": attachment.id,
            "conversation_id": attachment.conversation_id,
            "file_url": attachment.file_url,
            "file_type": attachment.file_type,
            "source": attachment.provider or "attachment",
            "origin": self._origin_from_source(attachment.provider),
        }
        if not attachment.file_url or attachment.file_url.startswith("whatsapp://"):
            extraction = self._create_failed_extraction(
                metadata,
                "Arquivo ainda nao esta disponivel localmente para leitura automatica.",
            )
            self._audit("energy_bill.extraction_failed", extraction)
            self.db.commit()
            self.db.refresh(extraction)
            return extraction
        return self.extract_from_file(attachment.file_url, metadata)

    def extract_from_file(self, file_path: str, metadata: dict[str, Any] | None = None) -> EnergyBillExtraction:
        if not settings.energy_bill_extraction_enabled:
            raise ValueError("Energy bill extraction is disabled")
        metadata = metadata or {}
        path = Path(file_path)
        self._validate_file(path)
        text = self._extract_text(path)
        if not text.strip():
            extraction = self._create_failed_extraction(metadata | self._file_metadata(path), "Nao foi possivel extrair texto do arquivo.")
            self._audit("energy_bill.extraction_failed", extraction)
            self.db.commit()
            self.db.refresh(extraction)
            return extraction

        result = self.parse_energy_bill_text(text, metadata)
        extraction = self._create_extraction_from_result(
            result,
            metadata | self._file_metadata(path) | {"raw_text": text},
        )
        self._audit("energy_bill.extracted", extraction, {"status": extraction.status})
        self.db.commit()
        self.db.refresh(extraction)
        return self.get_extraction(extraction.id)

    def extract_text_from_pdf(self, file_path: str) -> str:
        path = Path(file_path)
        try:
            import fitz  # type: ignore[import-not-found]

            with fitz.open(path) as document:
                return "\n".join(page.get_text("text") for page in document)
        except Exception:
            logger.info("PDF text extraction fallback used for energy bill.")
        return path.read_bytes().decode("utf-8", errors="ignore")

    def extract_text_with_ocr(self, file_path: str) -> str:
        if not settings.energy_bill_ocr_enabled:
            logger.info("Energy bill OCR skipped because it is disabled.")
            return ""
        if not settings.energy_bill_allow_external_ai:
            logger.warning("Energy bill OCR/external AI requested but ENERGY_BILL_ALLOW_EXTERNAL_AI is false.")
            return ""
        logger.warning("Energy bill OCR provider '%s' is not implemented in this local build.", settings.energy_bill_ocr_provider)
        return ""

    def parse_energy_bill_text(self, raw_text: str, metadata: dict[str, Any] | None = None) -> EnergyBillParseResult:
        metadata = metadata or {}
        parser = next((candidate for candidate in self.parsers if candidate.can_parse(raw_text, metadata)), self.parsers[-1])
        result = parser.parse(raw_text, metadata)
        stats = self.calculate_consumption_statistics(result.history, result.current_consumption_kwh)
        result.average_consumption_kwh = stats["average_consumption_kwh"]
        result.min_consumption_kwh = stats["min_consumption_kwh"]
        result.max_consumption_kwh = stats["max_consumption_kwh"]
        result.average_bill_amount = result.current_bill_amount
        estimate = self.estimate_solar_system(result.average_consumption_kwh, result.average_bill_amount)
        result.estimated_system_power_kwp = estimate["estimated_system_power_kwp"]
        result.estimated_monthly_generation_kwh = estimate["estimated_monthly_generation_kwh"]
        result.estimated_monthly_savings = estimate["estimated_monthly_savings"]
        result.missing_fields = self._missing_fields(result)
        result.confidence_score = self._confidence_score(result)
        result.needs_human_review = result.confidence_score < settings.energy_bill_min_confidence_auto_apply
        result.parsed_fields = {
            **result.parsed_fields,
            "parser_confidence_inputs": {
                "missing_fields": result.missing_fields,
                "history_count": len(result.history),
            },
        }
        return result

    def calculate_consumption_statistics(
        self,
        history: list[ConsumptionHistoryItem] | list[dict[str, Any]],
        current_consumption: float | None,
    ) -> dict[str, float | None]:
        values: list[float] = []
        for item in history:
            value = item.consumption_kwh if isinstance(item, ConsumptionHistoryItem) else item.get("consumption_kwh")
            if value is not None:
                values.append(float(value))
        if current_consumption is not None and not values:
            values.append(float(current_consumption))
        if not values:
            return {"average_consumption_kwh": None, "min_consumption_kwh": None, "max_consumption_kwh": None}
        return {
            "average_consumption_kwh": round(sum(values) / len(values), 2),
            "min_consumption_kwh": round(min(values), 2),
            "max_consumption_kwh": round(max(values), 2),
        }

    def estimate_solar_system(
        self,
        average_consumption_kwh: float | None,
        average_bill_amount: float | None,
    ) -> dict[str, float | None]:
        if average_consumption_kwh:
            monthly_generation = round(max(float(average_consumption_kwh), 0), 2)
        elif average_bill_amount:
            monthly_generation = max(round((float(average_bill_amount) * 0.85) / 0.95, 2), 0)
        else:
            return {
                "estimated_system_power_kwp": None,
                "estimated_monthly_generation_kwh": None,
                "estimated_monthly_savings": None,
            }
        power_kwp = round(monthly_generation / 135, 3)
        savings = round(float(average_bill_amount or 0) * 0.85, 2) if average_bill_amount else None
        return {
            "estimated_system_power_kwp": power_kwp,
            "estimated_monthly_generation_kwh": monthly_generation,
            "estimated_monthly_savings": savings,
        }

    def apply_to_lead(self, extraction_id: str, lead_id: str) -> Lead:
        extraction = self.get_extraction(extraction_id)
        lead = self.db.get(Lead, lead_id)
        if not lead:
            raise ValueError("Lead not found")

        self._sync_extraction_to_lead(extraction, lead)
        extraction.lead_id = lead.id

        if lead.conversation_id:
            conversation = self.db.get(Conversation, lead.conversation_id)
            if conversation:
                collected = dict(conversation.collected_data or {})
                collected.update(
                    {
                        "has_energy_bill": "sim",
                        "energy_bill_extraction_id": extraction.id,
                        "bill_file_received": True,
                        "bill_extraction_origin": extraction.origin,
                        "bill_extraction_confidence_score": self._float_or_none(extraction.confidence_score),
                        "bill_needs_human_review": extraction.needs_human_review,
                        "average_bill": lead.average_bill,
                        "average_consumption_kwh": self._float_or_none(extraction.average_consumption_kwh),
                        "current_consumption_kwh": self._float_or_none(extraction.current_consumption_kwh),
                        "current_bill_amount": self._float_or_none(extraction.current_bill_amount),
                        "utility_company": extraction.distributor or collected.get("utility_company"),
                        "installation_number": extraction.installation_number,
                        "city": extraction.city or collected.get("city"),
                        "state": extraction.state or collected.get("state"),
                    }
                )
                conversation.collected_data = {key: value for key, value in collected.items() if value is not None}

        self._audit("energy_bill.applied_to_lead", extraction, {"lead_id": lead.id})
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def confirm_extraction(
        self,
        extraction_id: str,
        payload: EnergyBillExtractionConfirm | dict[str, Any] | None = None,
    ) -> EnergyBillExtraction:
        extraction = self.get_extraction(extraction_id)
        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload or {})
        self._apply_update_data(extraction, data)
        extraction.status = "confirmed"
        extraction.needs_human_review = False
        extraction.confirmed_by = self.actor.id if self.actor else extraction.confirmed_by
        extraction.confirmed_at = utc_now()
        self._recalculate_extraction(extraction)
        self._audit("energy_bill.confirmed", extraction)
        self.db.commit()
        self.db.refresh(extraction)
        return self.get_extraction(extraction.id)

    def update_extraction(self, extraction_id: str, payload: EnergyBillExtractionUpdate) -> EnergyBillExtraction:
        extraction = self.get_extraction(extraction_id)
        data = payload.model_dump(exclude_unset=True)
        self._apply_update_data(extraction, data)
        self._recalculate_extraction(extraction)
        self._audit("energy_bill.updated", extraction)
        self.db.commit()
        self.db.refresh(extraction)
        return self.get_extraction(extraction.id)

    def discard_extraction(self, extraction_id: str) -> EnergyBillExtraction:
        extraction = self.get_extraction(extraction_id)
        extraction.status = "discarded"
        extraction.needs_human_review = True
        self._audit("energy_bill.discarded", extraction)
        self.db.commit()
        self.db.refresh(extraction)
        return extraction

    def generate_proposal(self, extraction_id: str) -> Proposal:
        extraction = self.get_extraction(extraction_id)
        lead_id = extraction.lead_id
        if not lead_id and extraction.conversation_id:
            lead = self.db.scalar(select(Lead).where(Lead.conversation_id == extraction.conversation_id).order_by(desc(Lead.created_at)))
            lead_id = lead.id if lead else None
        if not lead_id:
            raise ValueError("No lead linked to this extraction")
        self.apply_to_lead(extraction.id, lead_id)
        return ProposalService(self.db, self.actor).create_from_lead(lead_id)

    def create_from_text(
        self,
        raw_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> EnergyBillExtraction:
        result = self.parse_energy_bill_text(raw_text, metadata)
        extraction = self._create_extraction_from_result(
            result,
            {**(metadata or {}), "raw_text": raw_text, "source": "text", "origin": "manual_text"},
        )
        self._audit("energy_bill.extracted", extraction, {"status": extraction.status})
        self.db.commit()
        self.db.refresh(extraction)
        return self.get_extraction(extraction.id)

    def _extract_text(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self.extract_text_from_pdf(str(path))
        if suffix == ".txt":
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix in IMAGE_EXTENSIONS:
            return self.extract_text_with_ocr(str(path))
        return ""

    def _validate_file(self, path: Path) -> None:
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError("Unsupported energy bill file type")
        if not path.exists() or not path.is_file():
            raise ValueError("Energy bill file not found")
        max_bytes = settings.energy_bill_max_file_size_mb * 1024 * 1024
        if path.stat().st_size > max_bytes:
            raise ValueError("Energy bill file is too large")

    def _create_extraction_from_result(self, result: EnergyBillParseResult, metadata: dict[str, Any]) -> EnergyBillExtraction:
        raw_text = str(metadata.get("raw_text") or "")
        status = "needs_review" if result.needs_human_review else "extracted"
        extraction = EnergyBillExtraction(
            conversation_id=metadata.get("conversation_id"),
            customer_id=metadata.get("customer_id"),
            lead_id=metadata.get("lead_id"),
            attachment_id=metadata.get("attachment_id"),
            status=status,
            source=metadata.get("source") or "manual",
            origin=metadata.get("origin") or self._origin_from_source(metadata.get("source")),
            file_name=metadata.get("file_name"),
            file_type=metadata.get("file_type"),
            file_url=metadata.get("file_url"),
            distributor=result.distributor,
            customer_name=result.customer_name,
            customer_document_masked=result.customer_document_masked,
            installation_number=result.installation_number,
            city=result.city,
            state=result.state,
            reference_month=result.reference_month,
            due_date=result.due_date,
            current_consumption_kwh=result.current_consumption_kwh,
            current_bill_amount=result.current_bill_amount,
            average_consumption_kwh=result.average_consumption_kwh,
            average_bill_amount=result.average_bill_amount,
            min_consumption_kwh=result.min_consumption_kwh,
            max_consumption_kwh=result.max_consumption_kwh,
            estimated_system_power_kwp=result.estimated_system_power_kwp,
            estimated_monthly_generation_kwh=result.estimated_monthly_generation_kwh,
            estimated_monthly_savings=result.estimated_monthly_savings,
            confidence_score=result.confidence_score,
            needs_human_review=result.needs_human_review,
            missing_fields=result.missing_fields,
            parsed_fields=result.parsed_fields,
            raw_extraction=self._raw_extraction(result, raw_text),
            raw_text_excerpt=sanitize_raw_excerpt(raw_text) if raw_text else None,
        )
        self.db.add(extraction)
        self.db.flush()
        self._replace_history(extraction, result.history)
        self._update_linked_conversation(extraction)
        return extraction

    def _create_failed_extraction(self, metadata: dict[str, Any], error_message: str) -> EnergyBillExtraction:
        extraction = EnergyBillExtraction(
            conversation_id=metadata.get("conversation_id"),
            customer_id=metadata.get("customer_id"),
            lead_id=metadata.get("lead_id"),
            attachment_id=metadata.get("attachment_id"),
            status="failed",
            source=metadata.get("source") or "manual",
            origin=metadata.get("origin") or self._origin_from_source(metadata.get("source")),
            file_name=metadata.get("file_name"),
            file_type=metadata.get("file_type"),
            file_url=metadata.get("file_url"),
            confidence_score=0,
            needs_human_review=True,
            missing_fields=["texto legivel da conta de energia"],
            parsed_fields={},
            raw_extraction={},
            error_message=error_message,
        )
        self.db.add(extraction)
        self.db.flush()
        return extraction

    def _replace_history(
        self,
        extraction: EnergyBillExtraction,
        history: list[ConsumptionHistoryItem] | list[dict[str, Any]],
    ) -> None:
        extraction.history = []
        for item in history:
            data = item.__dict__ if isinstance(item, ConsumptionHistoryItem) else dict(item)
            if data.get("consumption_kwh") is None or not data.get("period"):
                continue
            extraction.history.append(
                EnergyBillConsumptionHistory(
                    extraction_id=extraction.id,
                    period=str(data["period"]),
                    consumption_kwh=float(data["consumption_kwh"]),
                    bill_amount=data.get("bill_amount"),
                )
            )

    def _apply_update_data(self, extraction: EnergyBillExtraction, data: dict[str, Any]) -> None:
        history = data.pop("history", None)
        for field, value in data.items():
            if hasattr(extraction, field):
                setattr(extraction, field, value)
        if history is not None:
            self._replace_history(extraction, history)

    def _recalculate_extraction(self, extraction: EnergyBillExtraction) -> None:
        stats = self.calculate_consumption_statistics(
            [
                {"period": item.period, "consumption_kwh": float(item.consumption_kwh), "bill_amount": item.bill_amount}
                for item in extraction.history
            ],
            self._float_or_none(extraction.current_consumption_kwh),
        )
        extraction.average_consumption_kwh = extraction.average_consumption_kwh or stats["average_consumption_kwh"]
        extraction.min_consumption_kwh = stats["min_consumption_kwh"]
        extraction.max_consumption_kwh = stats["max_consumption_kwh"]
        estimate = self.estimate_solar_system(
            self._float_or_none(extraction.average_consumption_kwh),
            self._float_or_none(extraction.average_bill_amount or extraction.current_bill_amount),
        )
        extraction.estimated_system_power_kwp = estimate["estimated_system_power_kwp"]
        extraction.estimated_monthly_generation_kwh = estimate["estimated_monthly_generation_kwh"]
        extraction.estimated_monthly_savings = estimate["estimated_monthly_savings"]

    def _fill_extraction_from_result(
        self,
        extraction: EnergyBillExtraction,
        result: EnergyBillParseResult,
        raw_text: str,
    ) -> None:
        extraction.status = "needs_review" if result.needs_human_review else "extracted"
        extraction.distributor = result.distributor
        extraction.customer_name = result.customer_name
        extraction.customer_document_masked = result.customer_document_masked
        extraction.installation_number = result.installation_number
        extraction.city = result.city
        extraction.state = result.state
        extraction.reference_month = result.reference_month
        extraction.due_date = result.due_date
        extraction.current_consumption_kwh = result.current_consumption_kwh
        extraction.current_bill_amount = result.current_bill_amount
        extraction.average_consumption_kwh = result.average_consumption_kwh
        extraction.average_bill_amount = result.average_bill_amount
        extraction.min_consumption_kwh = result.min_consumption_kwh
        extraction.max_consumption_kwh = result.max_consumption_kwh
        extraction.estimated_system_power_kwp = result.estimated_system_power_kwp
        extraction.estimated_monthly_generation_kwh = result.estimated_monthly_generation_kwh
        extraction.estimated_monthly_savings = result.estimated_monthly_savings
        extraction.confidence_score = result.confidence_score
        extraction.needs_human_review = result.needs_human_review
        extraction.missing_fields = result.missing_fields
        extraction.parsed_fields = {**(extraction.parsed_fields or {}), **result.parsed_fields}
        extraction.raw_extraction = self._raw_extraction(result, raw_text)
        extraction.raw_text_excerpt = sanitize_raw_excerpt(raw_text) if raw_text else None
        extraction.error_message = None

    def _mark_extraction_failed(self, extraction: EnergyBillExtraction, error_message: str) -> None:
        extraction.status = "failed"
        extraction.needs_human_review = True
        extraction.error_message = error_message
        extraction.missing_fields = extraction.missing_fields or ["texto legivel da conta de energia"]
        self._update_linked_conversation(extraction)
        self._audit("energy_bill.extraction_failed", extraction, {"origin": extraction.origin})

    def _metadata_for_existing_extraction(self, extraction: EnergyBillExtraction, path: Path) -> dict[str, Any]:
        return {
            "conversation_id": extraction.conversation_id,
            "customer_id": extraction.customer_id,
            "lead_id": extraction.lead_id,
            "attachment_id": extraction.attachment_id,
            "source": extraction.source,
            "origin": extraction.origin,
            **self._file_metadata(path),
        }

    def _update_linked_conversation(self, extraction: EnergyBillExtraction) -> None:
        if not extraction.conversation_id:
            return
        conversation = self.db.get(Conversation, extraction.conversation_id)
        if not conversation:
            return
        collected = dict(conversation.collected_data or {})
        collected.update(
            {
                "has_energy_bill": "sim",
                "bill_file_received": True,
                "energy_bill_extraction_id": extraction.id,
                "energy_bill_status": extraction.status,
                "bill_extraction_origin": extraction.origin,
                "bill_extraction_confidence_score": self._float_or_none(extraction.confidence_score),
                "bill_needs_human_review": extraction.needs_human_review,
                "current_consumption_kwh": self._float_or_none(extraction.current_consumption_kwh),
                "current_bill_amount": self._float_or_none(extraction.current_bill_amount),
                "average_consumption_kwh": self._float_or_none(extraction.average_consumption_kwh),
                "average_bill": self._float_or_none(extraction.average_bill_amount or extraction.current_bill_amount),
                "utility_company": extraction.distributor or collected.get("utility_company"),
                "installation_number": extraction.installation_number,
                "city": extraction.city or collected.get("city"),
                "state": extraction.state or collected.get("state"),
            }
        )
        conversation.collected_data = {key: value for key, value in collected.items() if value is not None}

    def _raw_extraction(self, result: EnergyBillParseResult, raw_text: str) -> dict[str, Any]:
        raw = result.to_dict()
        if settings.energy_bill_store_raw_text:
            raw["raw_text"] = sanitize_raw_excerpt(raw_text, limit=6000)
        return raw

    def _file_metadata(self, path: Path) -> dict[str, Any]:
        return {"file_name": path.name, "file_type": path.suffix.lower().strip("."), "file_url": str(path)}

    def _lead_for_conversation(self, conversation_id: str) -> Lead | None:
        return self.db.scalar(select(Lead).where(Lead.conversation_id == conversation_id).order_by(desc(Lead.created_at)))

    def _sync_extraction_to_lead(self, extraction: EnergyBillExtraction, lead: Lead) -> None:
        lead.average_bill = extraction.average_bill_amount or extraction.current_bill_amount or lead.average_bill
        lead.utility_company = extraction.distributor or lead.utility_company
        extra = dict(lead.extra or {})
        extra.update(
            {
                "has_energy_bill": "sim",
                "bill_file_received": True,
                "energy_bill_extraction_id": extraction.id,
                "energy_bill_status": extraction.status,
                "bill_extraction_origin": extraction.origin,
                "bill_extraction_confidence_score": self._float_or_none(extraction.confidence_score),
                "bill_needs_human_review": extraction.needs_human_review,
                "average_consumption_kwh": self._float_or_none(extraction.average_consumption_kwh),
                "current_consumption_kwh": self._float_or_none(extraction.current_consumption_kwh),
                "average_bill_amount": self._float_or_none(extraction.average_bill_amount),
                "current_bill_amount": self._float_or_none(extraction.current_bill_amount),
                "installation_number": extraction.installation_number,
                "distributor": extraction.distributor,
                "utility_company": extraction.distributor,
                "estimated_system_power_kwp": self._float_or_none(extraction.estimated_system_power_kwp),
                "estimated_monthly_generation_kwh": self._float_or_none(extraction.estimated_monthly_generation_kwh),
                "estimated_monthly_savings": self._float_or_none(extraction.estimated_monthly_savings),
            }
        )
        if extraction.city:
            extra.setdefault("city", extraction.city)
            extra.setdefault("city_state", f"{extraction.city} {extraction.state or ''}".strip())
        if extraction.state:
            extra.setdefault("state", extraction.state)
        lead.extra = {key: value for key, value in extra.items() if value is not None}

    @staticmethod
    def _origin_from_source(source: str | None) -> str:
        normalized = (source or "").lower()
        if normalized == "whatsapp":
            return "whatsapp"
        if normalized in {"site", "chat", "widget", "chatbot"}:
            return "chatbot"
        if normalized in {"upload", "panel", "admin"}:
            return "panel"
        if normalized == "text":
            return "manual_text"
        return normalized or "api"

    @staticmethod
    def _safe_file_name(file_url: str | None) -> str | None:
        if not file_url:
            return None
        if file_url.startswith("whatsapp://media/"):
            return file_url.rsplit("/", 1)[-1]
        return Path(file_url.split("?", 1)[0]).name or None

    def _missing_fields(self, result: EnergyBillParseResult) -> list[str]:
        checks = {
            "distribuidora": result.distributor,
            "numero da instalacao": result.installation_number,
            "consumo em kWh": result.current_consumption_kwh or result.average_consumption_kwh,
            "valor da conta": result.current_bill_amount or result.average_bill_amount,
            "cidade/UF": result.city and result.state,
        }
        return [label for label, value in checks.items() if not value]

    def _confidence_score(self, result: EnergyBillParseResult) -> float:
        score = 0.15
        if result.distributor:
            score += 0.12
        if result.installation_number:
            score += 0.12
        if result.current_consumption_kwh:
            score += 0.2
        if result.current_bill_amount:
            score += 0.15
        if len(result.history) >= 3:
            score += 0.16
        elif result.history:
            score += 0.08
        if result.city and result.state:
            score += 0.1
        return round(min(score, 0.99), 4)

    def _audit(self, action: str, extraction: EnergyBillExtraction, details: dict[str, Any] | None = None) -> None:
        self.db.add(
            AuditLog(
                actor_user_id=self.actor.id if self.actor else None,
                action=action,
                entity_type="energy_bill_extraction",
                entity_id=extraction.id,
                details={
                    "status": extraction.status,
                    "confidence_score": self._float_or_none(extraction.confidence_score),
                    **(details or {}),
                },
            )
        )

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


def process_energy_bill_extraction_background(extraction_id: str) -> None:
    db = SessionLocal()
    try:
        EnergyBillExtractorService(db).process_pending_extraction(extraction_id)
    finally:
        db.close()
