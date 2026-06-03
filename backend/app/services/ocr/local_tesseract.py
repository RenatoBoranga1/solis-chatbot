from __future__ import annotations

from pathlib import Path

from app.services.ocr.base import OcrProvider, OcrResult

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


class LocalTesseractOcrProvider(OcrProvider):
    name = "local_tesseract"

    def extract_text(self, file_path: str, max_pages: int = 3) -> OcrResult:
        path = Path(file_path)
        try:
            if path.suffix.lower() == ".pdf":
                return self._extract_pdf(path, max_pages)
            if path.suffix.lower() in IMAGE_EXTENSIONS:
                return self._extract_image(path)
            return OcrResult("", self.name, False, 0, "Tipo de arquivo nao suportado para OCR local.")
        except ImportError as exc:
            return OcrResult("", self.name, False, 0, f"Dependencia de OCR indisponivel: {exc.name}.")
        except Exception as exc:
            return OcrResult("", self.name, False, 0, f"Falha controlada no OCR local: {exc.__class__.__name__}.")

    def _extract_image(self, path: Path) -> OcrResult:
        image = self._prepare_image(path)
        text = self._run_tesseract(image)
        return OcrResult(text=text, provider=self.name, used=True, page_count=1, error=None if text.strip() else "OCR nao encontrou texto legivel.")

    def _extract_pdf(self, path: Path, max_pages: int) -> OcrResult:
        import pypdfium2 as pdfium  # type: ignore[import-not-found]

        document = pdfium.PdfDocument(str(path))
        page_limit = min(len(document), max(max_pages, 1))
        chunks: list[str] = []
        for index in range(page_limit):
            page = document[index]
            bitmap = page.render(scale=2).to_pil()
            chunks.append(self._run_tesseract(self._prepare_pil_image(bitmap)))
        text = "\n".join(part for part in chunks if part.strip())
        error = None if text.strip() else "OCR nao encontrou texto legivel no PDF escaneado."
        return OcrResult(text=text, provider=self.name, used=True, page_count=page_limit, error=error)

    def _prepare_image(self, path: Path):
        from PIL import Image  # type: ignore[import-not-found]

        with Image.open(path) as image:
            return self._prepare_pil_image(image.copy())

    @staticmethod
    def _prepare_pil_image(image):
        from PIL import ImageOps  # type: ignore[import-not-found]

        prepared = ImageOps.grayscale(image)
        prepared = ImageOps.autocontrast(prepared)
        width, height = prepared.size
        if width < 1200:
            ratio = 1200 / max(width, 1)
            prepared = prepared.resize((1200, max(int(height * ratio), 1)))
        return prepared

    @staticmethod
    def _run_tesseract(image) -> str:
        import pytesseract  # type: ignore[import-not-found]

        return pytesseract.image_to_string(image, lang="por+eng")
