from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models import EnergyBillExtraction, Lead, Proposal, User
from app.schemas import (
    EnergyBillExtractionConfirm,
    EnergyBillExtractionOut,
    EnergyBillExtractionUpdate,
    EnergyBillParsedData,
    EnergyBillParseTextIn,
    LeadOut,
    ProposalOut,
)
from app.services.energy_bill_extractor import EnergyBillExtractorService, UPLOAD_FAILURE_MESSAGE
from app.services.energy_bill_parsers.base import sanitize_text_for_database

router = APIRouter(prefix="/energy-bills", tags=["Contas de energia"])
logger = logging.getLogger(__name__)

VIEW_ROLES = ("admin", "comercial", "gestor", "suporte", "tecnico")
MANAGE_ROLES = ("admin", "comercial", "gestor")


@router.get("", response_model=list[EnergyBillExtractionOut])
def list_energy_bill_extractions(
    status_filter: str | None = Query(default=None, alias="status"),
    lead_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*VIEW_ROLES)),
) -> list[EnergyBillExtraction]:
    return EnergyBillExtractorService(db).list_extractions(status=status_filter, lead_id=lead_id)


@router.post("/parse-text", response_model=EnergyBillParsedData)
def parse_energy_bill_text(
    payload: EnergyBillParseTextIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*VIEW_ROLES)),
) -> dict[str, Any]:
    result = EnergyBillExtractorService(db).parse_energy_bill_text(payload.raw_text, payload.metadata)
    return result.to_dict()


@router.post("/extract", response_model=EnergyBillExtractionOut, status_code=status.HTTP_201_CREATED)
async def extract_energy_bill_file(
    file: UploadFile = File(...),
    conversation_id: str | None = Form(default=None),
    customer_id: str | None = Form(default=None),
    lead_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> EnergyBillExtraction:
    storage_dir = Path(settings.energy_bill_storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_text_for_database(Path(file.filename or "conta-energia").name, limit=260) or "conta-energia"
    path = storage_dir / safe_name
    content = await file.read()
    max_bytes = settings.energy_bill_max_file_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="Arquivo maior que o limite configurado.")
    path.write_bytes(content)
    metadata = {
        "conversation_id": conversation_id,
        "customer_id": customer_id,
        "lead_id": lead_id,
        "source": "upload",
        "origin": "panel",
        "file_name": safe_name,
        "file_type": path.suffix.lower().strip("."),
        "file_url": str(path),
    }
    service = EnergyBillExtractorService(db, current_user)
    try:
        return service.extract_from_file(str(path), metadata)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning("Unexpected energy bill upload processing failure. reason=%s", exc.__class__.__name__)
        db.rollback()
        try:
            return service.create_failed_from_file(str(path), metadata, UPLOAD_FAILURE_MESSAGE)
        except Exception as fallback_exc:
            logger.error("Could not create failed energy bill extraction. reason=%s", fallback_exc.__class__.__name__)
            db.rollback()
            raise HTTPException(status_code=400, detail=UPLOAD_FAILURE_MESSAGE) from fallback_exc


@router.post("/extract-from-attachment/{attachment_id}", response_model=EnergyBillExtractionOut)
def extract_energy_bill_from_attachment(
    attachment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> EnergyBillExtraction:
    try:
        return EnergyBillExtractorService(db, current_user).extract_from_attachment(attachment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{extraction_id}", response_model=EnergyBillExtractionOut)
def get_energy_bill_extraction(
    extraction_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_roles(*VIEW_ROLES)),
) -> EnergyBillExtraction:
    try:
        return EnergyBillExtractorService(db).get_extraction(extraction_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{extraction_id}", response_model=EnergyBillExtractionOut)
def update_energy_bill_extraction(
    extraction_id: str,
    payload: EnergyBillExtractionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> EnergyBillExtraction:
    try:
        return EnergyBillExtractorService(db, current_user).update_extraction(extraction_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{extraction_id}/confirm", response_model=EnergyBillExtractionOut)
def confirm_energy_bill_extraction(
    extraction_id: str,
    payload: EnergyBillExtractionConfirm = EnergyBillExtractionConfirm(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> EnergyBillExtraction:
    try:
        return EnergyBillExtractorService(db, current_user).confirm_extraction(extraction_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{extraction_id}/apply-to-lead/{lead_id}", response_model=LeadOut)
def apply_energy_bill_to_lead(
    extraction_id: str,
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> Lead:
    try:
        return EnergyBillExtractorService(db, current_user).apply_to_lead(extraction_id, lead_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{extraction_id}/generate-proposal", response_model=ProposalOut)
def generate_proposal_from_energy_bill(
    extraction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> Proposal:
    try:
        return EnergyBillExtractorService(db, current_user).generate_proposal(extraction_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{extraction_id}/discard", response_model=EnergyBillExtractionOut)
def discard_energy_bill_extraction(
    extraction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGE_ROLES)),
) -> EnergyBillExtraction:
    try:
        return EnergyBillExtractorService(db, current_user).discard_extraction(extraction_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
