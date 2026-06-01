from pathlib import Path
import textwrap

from app.core.config import settings
from app.models import Proposal


class ProposalPdfService:
    def generate(self, proposal: Proposal) -> str:
        storage_dir = Path(settings.proposal_storage_path)
        storage_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{proposal.proposal_number}.pdf".replace("/", "-")
        path = storage_dir / filename

        lines = self._proposal_lines(proposal)
        pdf_bytes = self._build_simple_pdf(lines)
        path.write_bytes(pdf_bytes)
        return str(path.as_posix())

    def _proposal_lines(self, proposal: Proposal) -> list[str]:
        location = " / ".join(part for part in [proposal.city, proposal.state] if part) or "Nao informado"
        lines = [
            "Solar Solucoes",
            "Proposta Comercial de Sistema Solar Fotovoltaico",
            f"Numero: {proposal.proposal_number}",
            f"Validade: {proposal.validity_days} dias",
            "",
            "Dados do cliente",
            f"Cliente: {proposal.customer_name}",
            f"Cidade/UF: {location}",
            f"Telefone: {proposal.customer_phone or 'Nao informado'}",
            f"E-mail: {proposal.customer_email or 'Nao informado'}",
            "",
            "Resumo da solucao",
            f"Tipo de imovel: {proposal.property_type or 'A validar'}",
            f"Conta media: R$ {self._money(proposal.average_bill)}",
            f"Potencia estimada: {proposal.estimated_system_power_kwp or 'A validar'} kWp",
            f"Geracao estimada mensal: {proposal.estimated_monthly_generation_kwh or 'A validar'} kWh",
            f"Economia estimada: {proposal.estimated_savings_percentage or 'A validar'}%",
            "",
            "Itens da proposta",
        ]
        for item in proposal.items or []:
            lines.append(
                f"- {item.category}: {item.description} | {self._number(item.quantity)} {item.unit} x "
                f"R$ {self._money(item.unit_price)} = R$ {self._money(item.total_price)}"
            )
        lines.extend(
            [
                "",
                "Resumo financeiro",
                f"Subtotal: R$ {self._money(proposal.subtotal)}",
                f"Desconto: R$ {self._money(proposal.discount)}",
                f"Total: R$ {self._money(proposal.total_amount)}",
                f"Condicoes de pagamento: {proposal.payment_conditions or 'A definir pela equipe comercial'}",
                "",
                "Observacoes",
                proposal.notes or "Esta proposta foi gerada como rascunho e deve ser revisada pela equipe Solar Solucoes.",
                "",
                "Observacoes importantes",
                "- Valores sujeitos a validacao tecnica e comercial.",
                "- Proposta sujeita a analise do local de instalacao.",
                "- Homologacao depende da concessionaria local.",
                "- Prazos e condicoes devem ser confirmados pela Solar Solucoes.",
                "- A economia estimada nao representa promessa de economia exata sem analise final.",
                "",
                "Solar Solucoes - Energia solar fotovoltaica",
                "Atendimento comercial e tecnico especializado.",
            ]
        )
        return lines

    def _build_simple_pdf(self, lines: list[str]) -> bytes:
        wrapped: list[str] = []
        for line in lines:
            if not line:
                wrapped.append("")
                continue
            wrapped.extend(textwrap.wrap(line, width=92) or [""])

        pages = [wrapped[index : index + 44] for index in range(0, len(wrapped), 44)] or [[]]
        objects: list[bytes] = []

        def add(obj: bytes) -> int:
            objects.append(obj)
            return len(objects)

        font_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        page_ids: list[int] = []
        content_ids: list[int] = []
        for page_lines in pages:
            content = self._page_content(page_lines)
            content_id = add(b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream")
            content_ids.append(content_id)
            page_id = add(
                b"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 "
                + str(font_id).encode("ascii")
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

    def _page_content(self, lines: list[str]) -> bytes:
        commands = ["BT", "/F1 10 Tf", "50 800 Td", "14 TL"]
        for line in lines:
            commands.append(f"({self._escape_pdf_text(line)}) Tj")
            commands.append("T*")
        commands.append("ET")
        return "\n".join(commands).encode("latin-1", errors="replace")

    @staticmethod
    def _escape_pdf_text(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

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
