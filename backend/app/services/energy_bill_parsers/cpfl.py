from __future__ import annotations

import re
from typing import Any

from app.services.energy_bill_parsers.base import (
    ConsumptionHistoryItem,
    EnergyBillParseResult,
    parse_decimal,
    period_from_match,
    sanitize_raw_excerpt,
)
from app.services.energy_bill_parsers.generic import GenericEnergyBillParser


class CPFLEnergyBillParser(GenericEnergyBillParser):
    name = "cpfl"
    MONTH_PATTERN = r"(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez|janeiro|fevereiro|marco|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)"

    def can_parse(self, text: str, metadata: dict[str, Any] | None = None) -> bool:
        return "cpfl" in text.lower()

    def parse(self, text: str, metadata: dict[str, Any] | None = None) -> EnergyBillParseResult:
        result = super().parse(text, metadata)
        result.distributor = result.distributor or "CPFL"
        debug = {
            "discarded_fields": dict(result.parsed_fields.get("discarded_fields") or {}),
            "anchors": dict(result.parsed_fields.get("anchors") or {}),
            "source_snippets": dict(result.parsed_fields.get("source_snippets") or {}),
            "review_warnings": list(result.parsed_fields.get("review_warnings") or []),
        }
        customer_block = self._extract_cpfl_customer_block(text, debug)
        if customer_block:
            result.customer_name = customer_block.get("customer_name") or result.customer_name
            result.customer_address = customer_block.get("customer_address")
            result.customer_district = customer_block.get("customer_district")
            result.customer_postal_code = customer_block.get("customer_postal_code")
            result.city = customer_block.get("city") or result.city
            result.state = customer_block.get("state") or result.state

        tariff_flag = result.parsed_fields.get("tariff_flag") or self._extract_tariff_flag(text, debug)
        result.tariff_flag = str(tariff_flag) if tariff_flag else None
        if result.installation_number and self._is_tariff_flag(result.installation_number):
            debug["discarded_fields"]["installation_number"] = (
                f"{result.installation_number} descartado por parecer bandeira tarifaria em conta CPFL."
            )
            tariff_flag = tariff_flag or self._canonical_tariff_flag(result.installation_number)
            result.installation_number = None
        if not result.installation_number:
            result.installation_number = self._extract_cpfl_installation(text, debug)
        result.customer_unit_number = result.installation_number
        cpfl_history = self._extract_cpfl_consumption_history(text, debug)
        if cpfl_history:
            result.history = cpfl_history
        result.parsed_fields = {
            **result.parsed_fields,
            "parser": self.name,
            "tariff_flag": result.tariff_flag,
            "customer_address": result.customer_address,
            "customer_district": result.customer_district,
            "customer_postal_code": result.customer_postal_code,
            "customer_unit_number": result.installation_number,
            "customer_block_detected": bool(customer_block),
            "customer_block_lines": customer_block.get("customer_block_lines", []) if customer_block else [],
            "discarded_fields": debug["discarded_fields"],
            "anchors": debug["anchors"],
            "source_snippets": debug["source_snippets"],
            "review_warnings": debug["review_warnings"],
            "history_detection": debug.get("history_detection", result.parsed_fields.get("history_detection")),
            "cpfl_rules_applied": True,
        }
        return result

    def _extract_cpfl_customer_block(self, text: str, debug: dict[str, Any]) -> dict[str, Any] | None:
        lines = self._lines(text)
        postal_pattern = re.compile(r"\b(\d{5}-?\d{3})\s+([A-ZÀ-ÿ' .-]{3,60})\s+([A-Z]{2})\b", re.I)
        for index, line in enumerate(lines):
            match = postal_pattern.search(line)
            if not match or index < 3:
                continue
            block_lines = lines[max(0, index - 3) : index + 1]
            context = " ".join(block_lines)
            if self._looks_like_cpfl_header_context(context):
                debug["discarded_fields"]["customer_block"] = f"{sanitize_raw_excerpt(context, limit=220)} descartado por parecer cabecalho da distribuidora."
                continue
            name_line, address_line, district_line = block_lines[-4], block_lines[-3], block_lines[-2]
            if not self._valid_customer_name(name_line) or not self._valid_customer_address(address_line):
                continue
            city = self._clean_label(match.group(2))
            state = match.group(3).upper()
            if self._reject_city_candidate(city, context, debug):
                continue
            postal_code = self._normalize_postal_code(match.group(1))
            debug["anchors"]["customer_block"] = "CEP cidade UF"
            debug["source_snippets"]["customer_block"] = sanitize_raw_excerpt(" | ".join(block_lines), limit=300)
            return {
                "customer_name": self._clean_label(name_line)[:180],
                "customer_address": self._clean_label(address_line)[:260],
                "customer_district": self._clean_label(district_line)[:120],
                "customer_postal_code": postal_code,
                "city": city[:120],
                "state": state,
                "customer_block_lines": [sanitize_raw_excerpt(item, limit=180) for item in block_lines],
            }
        return None

    def _extract_cpfl_consumption_history(self, text: str, debug: dict[str, Any]) -> list[ConsumptionHistoryItem]:
        block = self._history_block(text)
        scan_text = block or text
        require_context = bool(block)
        items: list[ConsumptionHistoryItem] = []
        seen_periods: set[str] = set()
        reference_year = self._reference_year(text)

        month_patterns = [
            (rf"\b{self.MONTH_PATTERN}\s*[\/\-]\s*(\d{{2,4}})\b[^\d\n]{{0,12}}(\d{{1,6}}(?:[,.]\d+)?)\s*(?:kwh)?\b", True),
            (rf"\b{self.MONTH_PATTERN}\s+(\d{{4}})\b[^\d\n]{{0,12}}(\d{{1,6}}(?:[,.]\d+)?)\s*(?:kwh)?\b", True),
            (rf"\b{self.MONTH_PATTERN}\s+(\d{{1,6}}(?:[,.]\d+)?)\s*(?:kwh)?\b", False),
        ]
        for pattern, has_year in month_patterns:
            for match in re.finditer(pattern, scan_text, re.I):
                snippet = self._snippet_around(scan_text, match.start(), match.end(), radius=45)
                normalized_snippet = self._normalize(snippet)
                if not require_context and not any(term in normalized_snippet for term in {"kwh", "historico", "consumo", "medido"}):
                    continue
                month_token = match.group(1)
                year_token = match.group(2) if has_year else reference_year
                value_token = match.group(3) if has_year else match.group(2)
                if not has_year and re.fullmatch(r"(?:19|20)\d{2}", value_token.strip()):
                    continue
                period = period_from_match(month_token, year_token)
                consumption = parse_decimal(value_token)
                if consumption is None or consumption <= 0 or consumption > 100000:
                    continue
                if period in seen_periods:
                    continue
                seen_periods.add(period)
                items.append(ConsumptionHistoryItem(period=period, consumption_kwh=float(consumption)))

        for match in re.finditer(r"\b(\d{1,2})[\/\-](\d{2,4})\b[^\d\n]{0,12}(\d{1,6}(?:[,.]\d+)?)\s*(?:kwh)?\b", scan_text, re.I):
            snippet = self._snippet_around(scan_text, match.start(), match.end(), radius=45)
            normalized_snippet = self._normalize(snippet)
            if not require_context and not any(term in normalized_snippet for term in {"kwh", "historico", "consumo", "medido"}):
                continue
            month = int(match.group(1))
            if month < 1 or month > 12:
                continue
            year_token = match.group(2)
            year = f"20{year_token}" if len(year_token) == 2 else year_token
            period = f"{year}-{month:02d}"
            consumption = parse_decimal(match.group(3))
            if consumption is None or consumption <= 0 or consumption > 100000 or period in seen_periods:
                continue
            seen_periods.add(period)
            items.append(ConsumptionHistoryItem(period=period, consumption_kwh=float(consumption)))

        if items:
            values = [item.consumption_kwh for item in items[:12]]
            debug["history_detection"] = {
                "months_detected": len(items),
                "average_consumption_kwh": round(sum(values) / len(values), 2),
                "source": "historico_cpfl",
                "items": [item.__dict__.copy() for item in items[:12]],
            }
            debug["anchors"]["history"] = "Historico de consumo CPFL"
        return items[:24]

    def _extract_cpfl_installation(self, text: str, debug: dict[str, Any]) -> str | None:
        patterns = [
            r"(?:n[oº]?\s*da\s*instala[cç][aã]o|instala[cç][aã]o)\s*[:\-]?\s*([0-9][0-9./-]{4,30})",
            r"(?:seu\s*c[oó]digo|codigo\s*do\s*cliente)\s*[:\-]?\s*([0-9][0-9./-]{4,30})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if not match:
                continue
            value = self._clean_identifier(match.group(1))
            if self._reject_installation_candidate(value, match.group(0), debug):
                continue
            debug["anchors"]["installation_number"] = "CPFL instalacao/codigo"
            debug["source_snippets"]["installation_number"] = self._snippet_around(text, match.start(), match.end())
            return value
        return None

    def _history_block(self, text: str) -> str:
        lines = text.splitlines()
        for index, line in enumerate(lines):
            normalized = self._normalize(line)
            if "historico" in normalized and "consumo" in normalized:
                return "\n".join(lines[index : index + 40])
            if "consumo dos ultimos meses" in normalized:
                return "\n".join(lines[index : index + 40])
        return ""

    def _reference_year(self, text: str) -> str:
        match = re.search(r"(?:referencia|mes/ano|m[eê]s\s*ano)\s*[:\-]?\s*(?:\d{1,2}|[A-Za-zçÇ]{3,9})[\/\-](\d{2,4})", text, re.I)
        if match:
            year = match.group(1)
            return f"20{year}" if len(year) == 2 else year
        return "0000"

    def _looks_like_cpfl_header_context(self, value: str) -> bool:
        normalized = self._normalize(value)
        return any(
            term in normalized
            for term in {
                "cpfl",
                "danf",
                "companhia",
                "energia s.a",
                "cnpj",
                "inscricao estadual",
                "rua vigato",
                "atendimento",
                "ouvidoria",
                "agencia",
                "sede",
            }
        )

    def _valid_customer_name(self, value: str) -> bool:
        normalized = self._normalize(value)
        if len(value.strip()) < 5:
            return False
        return not any(term in normalized for term in {"cpfl", "danf", "companhia", "cnpj", "inscricao", "atendimento", "ouvidoria"})

    def _valid_customer_address(self, value: str) -> bool:
        normalized = self._normalize(value)
        if len(value.strip()) < 5:
            return False
        return not any(term in normalized for term in {"cpfl", "danf", "companhia", "cnpj", "inscricao", "atendimento", "ouvidoria", "rua vigato"})

    @staticmethod
    def _normalize_postal_code(value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if len(digits) == 8:
            return f"{digits[:5]}-{digits[5:]}"
        return value
