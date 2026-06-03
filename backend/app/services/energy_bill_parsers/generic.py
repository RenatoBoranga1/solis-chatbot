from __future__ import annotations

import re
from typing import Any

from app.services.energy_bill_parsers.base import (
    ConsumptionHistoryItem,
    EnergyBillParseResult,
    mask_document,
    parse_brl_amount,
    parse_decimal,
    period_from_match,
)


class GenericEnergyBillParser:
    name = "generic"

    KNOWN_DISTRIBUTORS = [
        "CPFL",
        "ENEL",
        "CEMIG",
        "NEOENERGIA",
        "ENERGISA",
        "EQUATORIAL",
        "COPEL",
        "CELESC",
        "LIGHT",
        "ELEKTRO",
    ]

    def can_parse(self, text: str, metadata: dict[str, Any] | None = None) -> bool:
        normalized = text.lower()
        return "kwh" in normalized or "energia" in normalized or "conta" in normalized

    def parse(self, text: str, metadata: dict[str, Any] | None = None) -> EnergyBillParseResult:
        metadata = metadata or {}
        result = EnergyBillParseResult()
        result.distributor = self._extract_distributor(text) or metadata.get("distributor")
        result.customer_name = self._extract_customer_name(text) or metadata.get("customer_name")
        result.customer_document_masked = self._extract_document(text)
        result.installation_number = self._extract_installation_number(text) or metadata.get("installation_number")
        result.city, result.state = self._extract_city_state(text, metadata)
        result.reference_month = self._extract_reference_month(text)
        result.due_date = self._extract_due_date(text)
        result.current_consumption_kwh = self._extract_current_consumption(text)
        result.current_bill_amount = self._extract_bill_amount(text)
        result.history = self._extract_history(text)
        result.parsed_fields = {
            "parser": self.name,
            "has_history": bool(result.history),
            "metadata_keys": sorted(metadata.keys()),
        }
        return result

    def _extract_distributor(self, text: str) -> str | None:
        upper = text.upper()
        for distributor in self.KNOWN_DISTRIBUTORS:
            if distributor in upper:
                return distributor
        match = re.search(r"(?:distribuidora|concessionaria|concessionária)\s*[:\-]?\s*([A-Za-z0-9 .&-]{3,80})", text, re.I)
        return self._clean_label(match.group(1)) if match else None

    def _extract_customer_name(self, text: str) -> str | None:
        for pattern in [
            r"(?:cliente|titular|nome)\s*[:\-]\s*([A-Za-zÀ-ÿ' .]{3,80})",
            r"(?:consumidor)\s*[:\-]\s*([A-Za-zÀ-ÿ' .]{3,80})",
        ]:
            match = re.search(pattern, text, re.I)
            if match:
                return self._clean_label(match.group(1))
        return None

    def _extract_document(self, text: str) -> str | None:
        match = re.search(r"\b(\d{3}\.?\d{3}\.?\d{3}-?\d{2}|\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})\b", text)
        return mask_document(match.group(1)) if match else None

    def _extract_installation_number(self, text: str) -> str | None:
        for pattern in [
            r"(?:instala[cç][aã]o|unidade consumidora|uc|c[oó]digo do cliente|codigo do cliente|numero do cliente|n[ºo]\s*cliente)\s*[:\-]?\s*([A-Z0-9.-]{4,30})",
            r"\bUC\s+([A-Z0-9.-]{4,30})\b",
        ]:
            match = re.search(pattern, text, re.I)
            if match:
                return match.group(1).strip(" .-")
        return None

    def _extract_city_state(self, text: str, metadata: dict[str, Any]) -> tuple[str | None, str | None]:
        city = metadata.get("city")
        state = metadata.get("state")
        if city or state:
            return city, state

        match = re.search(r"(?:cidade|municipio|munic[ií]pio)\s*[:\-]\s*([A-Za-zÀ-ÿ' .-]{3,60})\s+(?:uf\s*[:\-]?\s*)?([A-Z]{2})\b", text, re.I)
        if match:
            return self._clean_label(match.group(1)), match.group(2).upper()
        match = re.search(r"\b([A-Za-zÀ-ÿ' .-]{3,60})\s*[/\-]\s*([A-Z]{2})\b", text)
        if match:
            return self._clean_label(match.group(1)), match.group(2).upper()
        return None, None

    def _extract_reference_month(self, text: str) -> str | None:
        patterns = [
            r"(?:refer[eê]ncia|mes/ano|m[eê]s\s*ano)\s*[:\-]?\s*(\d{1,2})[\/\-](\d{2,4})",
            r"(?:refer[eê]ncia|mes/ano|m[eê]s\s*ano)\s*[:\-]?\s*([A-Za-zçÇ]{3,9})[\/\-](\d{2,4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if not match:
                continue
            first, year = match.group(1), match.group(2)
            if first.isdigit():
                month = int(first)
                year = f"20{year}" if len(year) == 2 else year
                return f"{year}-{month:02d}"
            return period_from_match(first, year)
        return None

    def _extract_due_date(self, text: str) -> str | None:
        match = re.search(r"(?:vencimento|data de vencimento)\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", text, re.I)
        return match.group(1).replace("-", "/") if match else None

    def _extract_current_consumption(self, text: str) -> float | None:
        patterns = [
            r"(?:consumo(?:\s+faturado)?|energia ativa|total consumido)\s*[:\-]?\s*([\d.,]+)\s*kwh",
            r"([\d.,]+)\s*kwh\s*(?:consumo|energia ativa)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            value = parse_decimal(match.group(1)) if match else None
            if value is not None:
                return value
        return None

    def _extract_bill_amount(self, text: str) -> float | None:
        patterns = [
            r"(?:total a pagar|valor total|total da conta|importe total)\s*[:\-]?\s*R?\$?\s*([\d.]+,\d{2})",
            r"R\$\s*([\d.]+,\d{2})\s*(?:total|a pagar)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            value = parse_brl_amount(match.group(1)) if match else None
            if value is not None:
                return value
        return None

    def _extract_history(self, text: str) -> list[ConsumptionHistoryItem]:
        items: list[ConsumptionHistoryItem] = []
        seen: set[tuple[str, float]] = set()
        month_pattern = r"(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez|janeiro|fevereiro|mar[cç]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)"
        for match in re.finditer(rf"{month_pattern}[\/\-\s]*(\d{{2,4}})?[^\d]{{0,18}}([\d.,]+)\s*kwh", text, re.I):
            period = period_from_match(match.group(1), match.group(2))
            consumption = parse_decimal(match.group(3))
            if consumption is None:
                continue
            key = (period, consumption)
            if key not in seen:
                seen.add(key)
                items.append(ConsumptionHistoryItem(period=period, consumption_kwh=consumption))

        for match in re.finditer(r"\b(\d{1,2})[\/\-](\d{2,4})\b[^\d]{0,18}([\d.,]+)\s*kwh", text, re.I):
            month = int(match.group(1))
            if month < 1 or month > 12:
                continue
            year = match.group(2)
            year = f"20{year}" if len(year) == 2 else year
            consumption = parse_decimal(match.group(3))
            if consumption is None:
                continue
            period = f"{year}-{month:02d}"
            key = (period, consumption)
            if key not in seen:
                seen.add(key)
                items.append(ConsumptionHistoryItem(period=period, consumption_kwh=consumption))

        return items[:24]

    @staticmethod
    def _clean_label(value: str) -> str:
        return re.sub(r"\s{2,}", " ", value).strip(" :-")
