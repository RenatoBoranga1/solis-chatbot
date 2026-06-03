from __future__ import annotations

from app.services.ocr.base import OcrProvider, OcrResult


class OpenAIVisionOcrProvider(OcrProvider):
    name = "openai_vision"

    def __init__(self, enabled: bool, api_key: str | None) -> None:
        self.enabled = enabled
        self.api_key = api_key

    def extract_text(self, file_path: str, max_pages: int = 3) -> OcrResult:
        if not self.enabled:
            return OcrResult("", self.name, False, 0, "OCR externo bloqueado por ENERGY_BILL_ALLOW_EXTERNAL_AI=false.")
        if not self.api_key:
            return OcrResult("", self.name, False, 0, "OCR externo sem chave configurada.")
        return OcrResult("", self.name, False, 0, "Provider de OCR externo preparado, mas nao implementado nesta versao.")
