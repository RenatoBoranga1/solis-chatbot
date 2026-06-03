from __future__ import annotations

from app.services.ocr.base import DisabledOcrProvider, OcrProvider
from app.services.ocr.local_tesseract import LocalTesseractOcrProvider
from app.services.ocr.openai_vision import OpenAIVisionOcrProvider


def get_ocr_provider(settings) -> OcrProvider:
    if not settings.energy_bill_ocr_enabled:
        return DisabledOcrProvider("OCR desabilitado. Ative OCR local para leitura automatica de fotos ou PDFs escaneados.")

    provider = (settings.energy_bill_ocr_provider or "disabled").lower()
    if provider == "local_tesseract":
        return LocalTesseractOcrProvider()
    if provider == "openai_vision":
        return OpenAIVisionOcrProvider(
            enabled=settings.energy_bill_allow_external_ai,
            api_key=settings.openai_api_key,
        )
    return DisabledOcrProvider(f"Provider de OCR '{provider}' nao esta habilitado.")
