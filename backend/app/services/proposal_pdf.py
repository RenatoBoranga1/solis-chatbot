from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import textwrap

from app.core.config import settings
from app.models import CompanySettings, Proposal


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN_X = 42
PRIMARY = (1.0, 0.80, 0.20)
SECONDARY = (0.04, 0.12, 0.20)
LIGHT = (0.95, 0.97, 0.99)
MID = (0.82, 0.86, 0.90)
DARK_TEXT = (0.08, 0.13, 0.20)
MUTED_TEXT = (0.35, 0.41, 0.48)


@dataclass
class PdfPage:
    commands: list[str]


class ProposalPdfService:
    company_settings: CompanySettings | None = None

    def generate(self, proposal: Proposal, company_settings: CompanySettings | None = None) -> str:
        self.company_settings = company_settings
        storage_dir = Path(settings.proposal_storage_path)
        storage_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{proposal.proposal_number}.pdf".replace("/", "-")
        path = storage_dir / filename
        path.write_bytes(self._build_pdf(proposal))
        return str(path.as_posix())

    def _build_pdf(self, proposal: Proposal) -> bytes:
        pages: list[PdfPage] = []
        page = self._new_page(pages)
        y = self._draw_cover_header(page, proposal)
        y = self._draw_customer_block(page, proposal, y)
        y = self._draw_solution_block(page, proposal, y)
        page, y = self._draw_items_table(page, pages, proposal, y)
        page, y = self._draw_financial_block(page, pages, proposal, y)
        self._draw_notices(page, pages, proposal, y)
        return self._render_document(pages)

    def _new_page(self, pages: list[PdfPage]) -> PdfPage:
        page = PdfPage(commands=[])
        page.commands.append(self._fill_color(*LIGHT))
        page.commands.append(f"0 0 {PAGE_WIDTH} {PAGE_HEIGHT} re f")
        page.commands.append(self._fill_color(1, 1, 1))
        page.commands.append(f"{MARGIN_X} 40 {PAGE_WIDTH - (MARGIN_X * 2)} {PAGE_HEIGHT - 80} re f")
        self._draw_footer(page)
        pages.append(page)
        return page

    def _draw_cover_header(self, page: PdfPage, proposal: Proposal) -> int:
        issue_date = self._format_date(proposal.created_at)
        valid_until = self._format_date((proposal.created_at or datetime.now(timezone.utc)) + timedelta(days=proposal.validity_days))

        page.commands.append(self._fill_color(*SECONDARY))
        page.commands.append(f"{MARGIN_X} 728 {PAGE_WIDTH - (MARGIN_X * 2)} 74 re f")
        page.commands.append(self._fill_color(*PRIMARY))
        page.commands.append(f"{MARGIN_X} 728 10 74 re f")
        self._text(page, self._company_name(), MARGIN_X + 24, 780, 18, "F2", 1, 1, 1)
        self._text(page, "Proposta Comercial de Sistema Solar Fotovoltaico", MARGIN_X + 24, 758, 13, "F1", 1, 1, 1)
        if self.company_settings and self.company_settings.company_logo_url:
            self._text(page, "Logo oficial configurado", MARGIN_X + 24, 742, 7.5, "F1", 1, 1, 1)
        self._text(page, f"Proposta: {proposal.proposal_number}", 380, 781, 9, "F2", 1, 1, 1)
        self._text(page, f"Emissao: {issue_date}", 380, 765, 9, "F1", 1, 1, 1)
        self._text(page, f"Validade: {valid_until}", 380, 750, 9, "F1", 1, 1, 1)
        self._pill(page, proposal.status, 380, 730)
        return 700

    def _draw_customer_block(self, page: PdfPage, proposal: Proposal, y: int) -> int:
        location = " / ".join(part for part in [proposal.city, proposal.state] if part) or "A validar"
        self._section_title(page, "Dados do cliente", y)
        rows = [
            ("Cliente", proposal.customer_name),
            ("Telefone", proposal.customer_phone or "Nao informado"),
            ("E-mail", proposal.customer_email or "Nao informado"),
            ("Cidade/UF", location),
            ("Tipo de imovel", proposal.property_type or "A validar"),
            ("Conta media", f"R$ {self._money(proposal.average_bill)}"),
        ]
        self._key_value_grid(page, rows, y - 28)
        return y - 132

    def _draw_solution_block(self, page: PdfPage, proposal: Proposal, y: int) -> int:
        self._section_title(page, "Resumo da solucao", y)
        cards = [
            ("Potencia estimada", self._measurement(proposal.estimated_system_power_kwp, "kWp")),
            ("Geracao mensal estimada", self._measurement(proposal.estimated_monthly_generation_kwh, "kWh")),
            ("Economia estimada", self._measurement(proposal.estimated_savings_percentage, "%")),
        ]
        card_width = 156
        for index, (label, value) in enumerate(cards):
            x = MARGIN_X + 18 + (index * (card_width + 10))
            page.commands.append(self._fill_color(0.98, 0.99, 1.0))
            page.commands.append(f"{x} {y - 64} {card_width} 52 re f")
            page.commands.append(self._stroke_color(0.85, 0.89, 0.94))
            page.commands.append(f"{x} {y - 64} {card_width} 52 re S")
            self._text(page, label, x + 10, y - 30, 8, "F1", *MUTED_TEXT)
            self._text(page, value, x + 10, y - 49, 13, "F2", *DARK_TEXT)
        warning = "Estimativas dependem de validacao tecnica, analise do local, disponibilidade de rede e regras da concessionaria."
        self._wrapped_text(page, warning, MARGIN_X + 18, y - 86, 93, 8, "F1", MUTED_TEXT)
        self._wrapped_text(
            page,
            "Beneficios da solucao: reducao da dependencia da rede, acompanhamento especializado, monitoramento e suporte no pos-venda.",
            MARGIN_X + 18,
            y - 104,
            93,
            8,
            "F1",
            DARK_TEXT,
        )
        return y - 132

    def _draw_items_table(self, page: PdfPage, pages: list[PdfPage], proposal: Proposal, y: int) -> tuple[PdfPage, int]:
        page, y = self._ensure_space(page, pages, y, 110)
        self._section_title(page, "Itens da proposta", y)
        y -= 30
        y = self._table_header(page, y)
        for item in proposal.items or []:
            row_height = max(34, 14 * len(textwrap.wrap(str(item.description), width=45) or [""]))
            if y - row_height < 110:
                page = self._new_page(pages)
                y = self._table_header(page, 760)
            self._table_row(page, y, row_height, item)
            y -= row_height
        return page, y - 18

    def _draw_financial_block(self, page: PdfPage, pages: list[PdfPage], proposal: Proposal, y: int) -> tuple[PdfPage, int]:
        page, y = self._ensure_space(page, pages, y, 130)
        self._section_title(page, "Resumo financeiro", y)
        y -= 34
        rows = [
            ("Subtotal", f"R$ {self._money(proposal.subtotal)}"),
            ("Desconto", f"R$ {self._money(proposal.discount)}"),
            ("Valor total", f"R$ {self._money(proposal.total_amount)}"),
            ("Condicoes de pagamento", proposal.payment_conditions or "A definir pela equipe comercial."),
            ("Validade", f"{proposal.validity_days} dias"),
        ]
        for label, value in rows:
            self._text(page, label, MARGIN_X + 18, y, 9, "F2", *DARK_TEXT)
            self._wrapped_text(page, value, MARGIN_X + 190, y, 62, 9, "F1", DARK_TEXT)
            y -= 18
        return page, y - 12

    def _draw_notices(self, page: PdfPage, pages: list[PdfPage], proposal: Proposal, y: int) -> None:
        page, y = self._ensure_space(page, pages, y, 145)
        self._section_title(page, "Observacoes importantes", y)
        notices = [
            proposal.notes or "Esta proposta foi gerada como rascunho e deve ser revisada pela equipe Solar Solucoes.",
            "Proximos passos: validacao comercial, confirmacao tecnica, formalizacao contratual e acompanhamento da homologacao.",
            "Esta proposta pode ser aceita digitalmente pelo link seguro compartilhado pela equipe comercial.",
            "Valores sujeitos a validacao tecnica e comercial.",
            "Proposta sujeita a analise do local de instalacao.",
            "Homologacao depende da concessionaria local.",
            "Prazos e condicoes devem ser confirmados pela Solar Solucoes.",
            "A economia estimada nao representa promessa de economia exata sem analise final.",
            "Este documento nao substitui visita tecnica quando ela for necessaria.",
        ]
        y -= 26
        for notice in notices:
            lines = textwrap.wrap(notice, width=95) or [""]
            if y - (len(lines) * 12) < 86:
                page = self._new_page(pages)
                y = 760
            for line in lines:
                self._text(page, f"- {line}", MARGIN_X + 18, y, 8.5, "F1", *DARK_TEXT)
                y -= 12

    def _ensure_space(self, page: PdfPage, pages: list[PdfPage], y: int, needed: int) -> tuple[PdfPage, int]:
        if y - needed >= 90:
            return page, y
        return self._new_page(pages), 760

    def _draw_footer(self, page: PdfPage) -> None:
        page.commands.append(self._fill_color(*SECONDARY))
        page.commands.append(f"{MARGIN_X} 40 {PAGE_WIDTH - (MARGIN_X * 2)} 34 re f")
        footer = "Energia solar com acompanhamento especializado do primeiro contato ao pos-venda."
        contact = " | ".join(
            item
            for item in [self._company_phone(), self._company_email(), self._company_website()]
            if item
        )
        self._text(page, self._company_name(), MARGIN_X + 14, 60, 8, "F2", 1, 1, 1)
        self._text(page, footer, MARGIN_X + 14, 48, 7.5, "F1", 1, 1, 1)
        if contact:
            self._text(page, contact[:80], 312, 54, 7.5, "F1", 1, 1, 1)

    def _section_title(self, page: PdfPage, title: str, y: int) -> None:
        page.commands.append(self._fill_color(*PRIMARY))
        page.commands.append(f"{MARGIN_X + 18} {y - 15} 7 18 re f")
        self._text(page, title, MARGIN_X + 32, y - 9, 13, "F2", *DARK_TEXT)
        page.commands.append(self._stroke_color(0.89, 0.91, 0.94))
        page.commands.append(f"{MARGIN_X + 18} {y - 23} m {PAGE_WIDTH - MARGIN_X - 18} {y - 23} l S")

    def _key_value_grid(self, page: PdfPage, rows: list[tuple[str, str]], y: int) -> None:
        col_width = 245
        row_height = 31
        for index, (label, value) in enumerate(rows):
            col = index % 2
            row = index // 2
            x = MARGIN_X + 18 + (col * (col_width + 12))
            yy = y - (row * row_height)
            page.commands.append(self._fill_color(0.98, 0.99, 1.0))
            page.commands.append(f"{x} {yy - 22} {col_width} 26 re f")
            self._text(page, label, x + 8, yy - 7, 7.5, "F1", *MUTED_TEXT)
            self._text(page, str(value)[:50], x + 8, yy - 18, 9, "F2", *DARK_TEXT)

    def _table_header(self, page: PdfPage, y: int) -> int:
        page.commands.append(self._fill_color(*SECONDARY))
        page.commands.append(f"{MARGIN_X + 18} {y - 22} {PAGE_WIDTH - 120} 22 re f")
        headers = [("Categoria", 54), ("Descricao", 145), ("Qtd", 348), ("Un", 392), ("Unitario", 426), ("Total", 493)]
        for label, x in headers:
            self._text(page, label, x, y - 14, 7.5, "F2", 1, 1, 1)
        return y - 24

    def _table_row(self, page: PdfPage, y: int, height: int, item) -> None:
        page.commands.append(self._fill_color(1, 1, 1))
        page.commands.append(f"{MARGIN_X + 18} {y - height} {PAGE_WIDTH - 120} {height} re f")
        page.commands.append(self._stroke_color(0.88, 0.91, 0.94))
        page.commands.append(f"{MARGIN_X + 18} {y - height} {PAGE_WIDTH - 120} {height} re S")
        self._wrapped_text(page, self._category_label(item.category), 54, y - 12, 16, 7.2, "F2", DARK_TEXT)
        self._wrapped_text(page, str(item.description), 145, y - 12, 44, 7.2, "F1", DARK_TEXT)
        self._text(page, self._number(item.quantity), 348, y - 12, 7.5, "F1", *DARK_TEXT)
        self._text(page, str(item.unit), 392, y - 12, 7.5, "F1", *DARK_TEXT)
        self._text(page, f"R$ {self._money(item.unit_price)}", 426, y - 12, 7.5, "F1", *DARK_TEXT)
        self._text(page, f"R$ {self._money(item.total_price)}", 493, y - 12, 7.5, "F2", *DARK_TEXT)

    def _pill(self, page: PdfPage, text: str, x: int, y: int) -> None:
        page.commands.append(self._fill_color(*PRIMARY))
        page.commands.append(f"{x} {y} 118 14 re f")
        self._text(page, f"Status: {text}", x + 7, y + 4, 7.5, "F2", *SECONDARY)

    def _wrapped_text(
        self,
        page: PdfPage,
        value: str,
        x: int,
        y: int,
        width: int,
        size: float,
        font: str,
        color: tuple[float, float, float],
    ) -> None:
        for index, line in enumerate(textwrap.wrap(str(value), width=width) or [""]):
            self._text(page, line, x, y - (index * (size + 3)), size, font, *color)

    def _text(self, page: PdfPage, value: str, x: int, y: int | float, size: float, font: str, r: float, g: float, b: float) -> None:
        page.commands.append(self._fill_color(r, g, b))
        page.commands.append("BT")
        page.commands.append(f"/{font} {size:g} Tf")
        page.commands.append(f"{x:g} {y:g} Td")
        page.commands.append(f"({self._escape_pdf_text(value)}) Tj")
        page.commands.append("ET")

    def _render_document(self, pages: list[PdfPage]) -> bytes:
        objects: list[bytes] = []

        def add(obj: bytes) -> int:
            objects.append(obj)
            return len(objects)

        font_regular_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        font_bold_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        page_ids: list[int] = []
        for page in pages:
            content = "\n".join(page.commands).encode("latin-1", errors="replace")
            content_id = add(b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream")
            page_id = add(
                b"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 "
                + str(font_regular_id).encode("ascii")
                + b" 0 R /F2 "
                + str(font_bold_id).encode("ascii")
                + b" 0 R >> >> /Contents "
                + str(content_id).encode("ascii")
                + b" 0 R >>"
            )
            page_ids.append(page_id)

        kids = b" ".join(f"{page_id} 0 R".encode("ascii") for page_id in page_ids)
        pages_id = add(b"<< /Type /Pages /Kids [" + kids + b"] /Count " + str(len(page_ids)).encode("ascii") + b" >>")
        for page_id in page_ids:
            objects[page_id - 1] = objects[page_id - 1].replace(b"/Parent 0 0 R", f"/Parent {pages_id} 0 R".encode("ascii"))
        catalog_id = add(b"<< /Type /Catalog /Pages " + str(pages_id).encode("ascii") + b" 0 R >>")

        output = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(len(output))
            output.extend(f"{index} 0 obj\n".encode("ascii"))
            output.extend(obj)
            output.extend(b"\nendobj\n")
        xref_offset = len(output)
        output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        output.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
        output.extend(
            b"trailer\n<< /Size "
            + str(len(objects) + 1).encode("ascii")
            + b" /Root "
            + str(catalog_id).encode("ascii")
            + b" 0 R >>\nstartxref\n"
            + str(xref_offset).encode("ascii")
            + b"\n%%EOF\n"
        )
        return bytes(output)

    @staticmethod
    def _fill_color(r: float, g: float, b: float) -> str:
        return f"{r:g} {g:g} {b:g} rg"

    @staticmethod
    def _stroke_color(r: float, g: float, b: float) -> str:
        return f"{r:g} {g:g} {b:g} RG"

    @staticmethod
    def _escape_pdf_text(value: object) -> str:
        text = str(value or "")
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    @staticmethod
    def _format_date(value: datetime | None) -> str:
        value = value or datetime.now(timezone.utc)
        return value.strftime("%d/%m/%Y")

    @staticmethod
    def _money(value: object) -> str:
        try:
            return f"{float(value or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (TypeError, ValueError):
            return "0,00"

    @staticmethod
    def _number(value: object) -> str:
        try:
            return f"{float(value or 0):g}"
        except (TypeError, ValueError):
            return "0"

    @staticmethod
    def _measurement(value: object, unit: str) -> str:
        if value in (None, ""):
            return "A validar"
        try:
            return f"{float(value):g} {unit}"
        except (TypeError, ValueError):
            return f"{value} {unit}"

    @staticmethod
    def _category_label(category: str) -> str:
        labels = {
            "kit_fotovoltaico": "Kit fotovoltaico",
            "materiais_eletricos": "Materiais eletricos",
            "mao_de_obra": "Mao de obra",
            "projeto": "Projeto tecnico",
            "homologacao": "Homologacao",
            "taxas_concessionaria": "Taxas e adequacoes",
            "estrutura_fixacao": "Estrutura de fixacao",
            "deslocamento": "Deslocamento",
            "monitoramento": "Monitoramento",
            "outros": "Outros",
        }
        return labels.get(category, category)

    def _company_name(self) -> str:
        return (self.company_settings.company_name if self.company_settings else None) or settings.company_name

    def _company_phone(self) -> str | None:
        return (self.company_settings.company_phone if self.company_settings else None) or settings.company_phone

    def _company_email(self) -> str | None:
        return (self.company_settings.company_email if self.company_settings else None) or settings.company_email

    def _company_website(self) -> str | None:
        value = (self.company_settings.company_website if self.company_settings else None) or settings.company_website
        return str(value) if value else None
