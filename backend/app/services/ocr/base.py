from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OcrResult:
    text: str
    provider: str
    used: bool
    page_count: int = 0
    error: str | None = None

    def metadata(self) -> dict[str, object]:
        return {
            "ocr_used": self.used,
            "ocr_provider": self.provider,
            "ocr_page_count": self.page_count,
            "ocr_error": self.error,
        }


class OcrProvider:
    name = "base"

    def extract_text(self, file_path: str, max_pages: int = 3) -> OcrResult:
        raise NotImplementedError


class DisabledOcrProvider(OcrProvider):
    name = "disabled"

    def __init__(self, reason: str | None = None) -> None:
        self.reason = reason or "OCR desabilitado."

    def extract_text(self, file_path: str, max_pages: int = 3) -> OcrResult:
        return OcrResult(text="", provider=self.name, used=False, page_count=0, error=self.reason)
