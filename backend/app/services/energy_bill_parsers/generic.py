from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.services.energy_bill_parsers.base import (
    ConsumptionHistoryItem,
    EnergyBillParseResult,
    mask_document,
    parse_brl_amount,
    parse_decimal,
    period_from_match,
    sanitize_raw_excerpt,
    sanitize_text_for_database,
)


@dataclass
class ExtractionCandidate:
    value: Any
    anchor: str
    snippet: str
    score: int = 0


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
    TARIFF_FLAG_VALUES = {
        "verde": "Verde",
        "amarela": "Amarela",
        "vermelha": "Vermelha",
        "vermelha patamar 1": "Vermelha patamar 1",
        "vermelha patamar 2": "Vermelha patamar 2",
        "escassez hidrica": "Escassez hidrica",
    }
    DISTRIBUTOR_CONTEXT_TERMS = {
        "cpfl",
        "cnpj",
        "inscricao estadual",
        "agencia",
        "atendimento",
        "posto",
        "endereco da distribuidora",
        "sede",
        "terreo",
        "loja",
        "canal de atendimento",
        "ouvidoria",
        "avisos",
        "mensagens",
        "demonstrativo",
        "informacoes fiscais",
        "companhia",
        "distribuidora",
    }
    BILL_AMOUNT_ANCHORS = [
        "total a pagar",
        "valor a pagar",
        "valor da conta",
        "total da fatura",
        "conta do mes",
        "debito total",
        "valor total",
        "pague ate",
        "vencimento",
    ]
    BILL_AMOUNT_EXCLUDED_CONTEXT = {
        "icms",
        "pis",
        "cofins",
        "tarifa",
        "unitario",
        "unitaria",
        "iluminacao publica",
        "contribuicao",
        "multa",
        "juros",
        "base de calculo",
        "aliquota",
        "imposto",
        "tributo",
    }
    CONSUMPTION_ANCHORS = [
        "consumo faturado",
        "consumo medido",
        "consumo kwh",
        "energia ativa",
        "total consumido",
        "quantidade",
        "historico de consumo",
    ]

    def can_parse(self, text: str, metadata: dict[str, Any] | None = None) -> bool:
        normalized = self._normalize(text)
        return "kwh" in normalized or "energia" in normalized or "conta" in normalized or "fatura" in normalized

    def parse(self, text: str, metadata: dict[str, Any] | None = None) -> EnergyBillParseResult:
        metadata = metadata or {}
        text = sanitize_text_for_database(text)
        debug: dict[str, Any] = {
            "parser": self.name,
            "anchors": {},
            "source_snippets": {},
            "discarded_fields": {},
            "review_warnings": [],
        }

        result = EnergyBillParseResult()
        result.distributor = self._extract_distributor(text) or metadata.get("distributor")
        result.customer_name = self._extract_customer_name(text, debug) or metadata.get("customer_name")
        result.customer_document_masked = self._extract_document(text)
        result.parsed_fields["tariff_flag"] = self._extract_tariff_flag(text, debug)
        result.installation_number = self._extract_installation_number(text, debug) or metadata.get("installation_number")
        result.city, result.state = self._extract_city_state(text, metadata, debug)
        result.reference_month = self._extract_reference_month(text)
        result.due_date = self._extract_due_date(text)
        result.history = self._extract_history(text)
        result.current_consumption_kwh = self._extract_current_consumption(text, debug)
        result.current_bill_amount = self._extract_bill_amount(text, debug)
        if result.current_bill_amount == 0:
            debug["discarded_fields"]["current_bill_amount"] = "R$ 0,00 descartado por nao haver indicacao clara de fatura zerada."
            result.current_bill_amount = None

        debug["has_history"] = bool(result.history)
        debug["months_detected"] = len(result.history) if result.history else (1 if result.current_consumption_kwh is not None else 0)
        debug["metadata_keys"] = sorted(metadata.keys())
        debug["customer_unit_number"] = result.installation_number
        result.parsed_fields = {
            **result.parsed_fields,
            "parser": self.name,
            "has_history": debug["has_history"],
            "months_detected": debug["months_detected"],
            "metadata_keys": debug["metadata_keys"],
            "customer_unit_number": debug["customer_unit_number"],
            "discarded_fields": debug["discarded_fields"],
            "anchors": debug["anchors"],
            "source_snippets": debug["source_snippets"],
            "review_warnings": debug["review_warnings"],
        }
        return result

    def _extract_distributor(self, text: str) -> str | None:
        upper = text.upper()
        for distributor in self.KNOWN_DISTRIBUTORS:
            if distributor in upper:
                return distributor
        match = re.search(r"(?:distribuidora|concessionaria|concessionaria)\s*[:\-]?\s*([A-Za-z0-9 .&-]{3,80})", text, re.I)
        return self._clean_label(match.group(1)) if match else None

    def _extract_customer_name(self, text: str, debug: dict[str, Any]) -> str | None:
        for line in self._lines(text):
            match = re.search(r"\b(?:cliente|titular|nome|consumidor)\s*[:\-]\s*(.+)$", line, re.I)
            if not match:
                continue
            value = self._clean_label(match.group(1))
            if self._looks_like_distributor_context(value) or self._is_tariff_flag(value):
                debug["discarded_fields"]["customer_name"] = f"{value} descartado por contexto suspeito."
                continue
            debug["anchors"]["customer_name"] = "Cliente/Nome"
            debug["source_snippets"]["customer_name"] = line
            return value[:80]
        return None

    def _extract_document(self, text: str) -> str | None:
        match = re.search(r"\b(\d{3}\.?\d{3}\.?\d{3}-?\d{2}|\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})\b", text)
        return mask_document(match.group(1)) if match else None

    def _extract_tariff_flag(self, text: str, debug: dict[str, Any]) -> str | None:
        normalized = self._normalize(text)
        match = re.search(r"bandeira\s+(verde|amarela|vermelha(?:\s+patamar\s+[12])?|escassez\s+h[íi]drica)", text, re.I)
        if match:
            value = self._canonical_tariff_flag(match.group(1))
            debug["anchors"]["tariff_flag"] = "Bandeira tarifaria"
            debug["source_snippets"]["tariff_flag"] = self._snippet_around(text, match.start(), match.end())
            return value
        for raw, value in self.TARIFF_FLAG_VALUES.items():
            if f"bandeira {raw}" in normalized:
                debug["anchors"]["tariff_flag"] = "Bandeira tarifaria"
                return value
        return None

    def _extract_installation_number(self, text: str, debug: dict[str, Any]) -> str | None:
        patterns = [
            r"(?:instala[cç][aã]o|unidade consumidora|uc|codigo do cliente|numero do cliente|n[oº]\s*cliente)\s*[:\-]?\s*([A-Za-z0-9./-]{3,40})",
            r"\bUC\s+([A-Za-z0-9./-]{3,40})\b",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.I):
                value = self._clean_identifier(match.group(1))
                if self._reject_installation_candidate(value, match.group(0), debug):
                    continue
                debug["anchors"]["installation_number"] = match.group(0).split(str(match.group(1)), 1)[0].strip(" :-")
                debug["source_snippets"]["installation_number"] = self._snippet_around(text, match.start(), match.end())
                return value
        return None

    def _extract_city_state(self, text: str, metadata: dict[str, Any], debug: dict[str, Any]) -> tuple[str | None, str | None]:
        city = metadata.get("city")
        state = metadata.get("state")
        if city or state:
            return str(city) if city else None, str(state).upper() if state else None

        patterns = [
            r"(?:cidade|municipio|municipio|localidade)\s*[:\-]\s*([A-Za-zÀ-ÿ' .-]{3,80})\s+(?:uf\s*[:\-]?\s*)?([A-Z]{2})\b",
            r"(?:endereco da instalacao|endereco da unidade consumidora|local de consumo|dados da unidade consumidora)[^\n]{0,120}\b([A-Za-zÀ-ÿ' .-]{3,60})\s*[/\-]\s*([A-Z]{2})\b",
            r"\b([A-Za-zÀ-ÿ' .-]{3,60})\s*/\s*([A-Z]{2})\b",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.I):
                line = self._line_for_position(text, match.start())
                candidate = self._clean_label(match.group(1))
                state_value = match.group(2).upper()
                if self._reject_city_candidate(candidate, line, debug):
                    continue
                debug["anchors"]["city"] = "Cidade/UF"
                debug["source_snippets"]["city"] = line
                return candidate[:120], state_value
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
        match = re.search(r"(?:vencimento|data de vencimento|pague ate)\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", text, re.I)
        return match.group(1).replace("-", "/") if match else None

    def _extract_current_consumption(self, text: str, debug: dict[str, Any]) -> float | None:
        candidates: list[ExtractionCandidate] = []
        patterns = [
            r"(consumo(?:\s+faturado|\s+medido|\s+kwh)?|energia ativa|total consumido|quantidade)\s*[:\-]?\s*([\d.,]+)\s*kwh",
            r"([\d.,]+)\s*kwh[^\n]{0,40}(consumo|energia ativa)",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.I):
                value_group = 2 if match.group(2).replace(".", "").replace(",", "").isdigit() else 1
                value = parse_decimal(match.group(value_group))
                if value is None or value < 0 or value > 100000:
                    continue
                snippet = self._snippet_around(text, match.start(), match.end())
                score = self._anchor_score(snippet, self.CONSUMPTION_ANCHORS)
                candidates.append(ExtractionCandidate(value, "Consumo kWh", snippet, score))
        if not candidates:
            return None
        best = sorted(candidates, key=lambda candidate: candidate.score, reverse=True)[0]
        debug["anchors"]["consumption"] = best.anchor
        debug["source_snippets"]["consumption"] = best.snippet
        return float(best.value)

    def _extract_bill_amount(self, text: str, debug: dict[str, Any]) -> float | None:
        candidates: list[ExtractionCandidate] = []
        for match in re.finditer(r"R?\$?\s*([\d]{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})", text, re.I):
            value = parse_brl_amount(match.group(1))
            if value is None:
                continue
            snippet = self._snippet_around(text, match.start(), match.end(), radius=90)
            normalized = self._normalize(snippet)
            if value == 0 and not self._explicit_zero_bill(normalized):
                debug["discarded_fields"].setdefault("current_bill_amount", "R$ 0,00 descartado por nao haver indicacao clara de fatura zerada.")
                continue
            score = self._anchor_score(normalized, self.BILL_AMOUNT_ANCHORS)
            if any(term in normalized for term in self.BILL_AMOUNT_EXCLUDED_CONTEXT) and score < 8:
                continue
            candidates.append(ExtractionCandidate(value, self._best_anchor(normalized, self.BILL_AMOUNT_ANCHORS), snippet, score))
        if not candidates:
            debug["review_warnings"].append("Valor da conta nao encontrado.")
            return None
        best = sorted(candidates, key=lambda candidate: (candidate.score, float(candidate.value)), reverse=True)[0]
        if best.score <= 0:
            debug["review_warnings"].append("Valor monetario encontrado sem ancora confiavel de total da fatura.")
            return None
        debug["anchors"]["bill_amount"] = best.anchor or "Valor monetario"
        debug["source_snippets"]["bill_amount"] = best.snippet
        return float(best.value)

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

    def _reject_installation_candidate(self, value: str | None, context: str, debug: dict[str, Any]) -> bool:
        if not value:
            return True
        if self._is_tariff_flag(value):
            debug["discarded_fields"]["installation_number"] = f"{value} descartado por parecer bandeira tarifaria."
            return True
        if not re.search(r"\d", value):
            debug["discarded_fields"]["installation_number"] = f"{value} descartado por nao conter numero."
            return True
        if self._looks_like_distributor_context(context):
            debug["discarded_fields"]["installation_number"] = f"{value} descartado por contexto de distribuidora."
            return True
        return False

    def _reject_city_candidate(self, value: str, context: str, debug: dict[str, Any]) -> bool:
        if self._is_tariff_flag(value):
            debug["discarded_fields"]["city"] = f"{value} descartado por parecer bandeira tarifaria."
            return True
        if self._looks_like_distributor_context(value) or self._looks_like_distributor_context(context):
            debug["discarded_fields"]["city"] = f"{self._clean_label(context or value)} descartado por parecer endereco ou bloco da distribuidora."
            debug["review_warnings"].append("Cidade/endereco precisa de revisao.")
            return True
        if len(value.split()) > 6:
            debug["discarded_fields"]["city"] = f"{value} descartado por ser longo demais para cidade."
            return True
        return False

    def _anchor_score(self, text: str, anchors: list[str]) -> int:
        normalized = self._normalize(text)
        score = 0
        for anchor in anchors:
            if anchor in normalized:
                score = max(score, 10 if anchor in {"total a pagar", "valor a pagar", "total da fatura", "consumo faturado"} else 6)
        return score

    def _best_anchor(self, text: str, anchors: list[str]) -> str:
        normalized = self._normalize(text)
        return next((anchor for anchor in anchors if anchor in normalized), "")

    def _explicit_zero_bill(self, normalized_context: str) -> bool:
        return any(term in normalized_context for term in {"fatura zerada", "valor zero", "sem debito", "sem debito total"})

    def _looks_like_distributor_context(self, value: str | None) -> bool:
        normalized = self._normalize(value or "")
        return any(term in normalized for term in self.DISTRIBUTOR_CONTEXT_TERMS)

    def _is_tariff_flag(self, value: str | None) -> bool:
        normalized = self._normalize(value or "").strip(" .:-")
        return normalized in self.TARIFF_FLAG_VALUES or normalized.startswith("bandeira ")

    def _canonical_tariff_flag(self, value: str | None) -> str | None:
        normalized = self._normalize(value or "").strip(" .:-")
        normalized = normalized.removeprefix("bandeira ").strip()
        return self.TARIFF_FLAG_VALUES.get(normalized, self._clean_label(value or "") or None)

    def _snippet_around(self, text: str, start: int, end: int, radius: int = 70) -> str:
        snippet = text[max(0, start - radius) : min(len(text), end + radius)]
        return self._clean_label(sanitize_raw_excerpt(snippet.replace("\n", " "), limit=260))

    def _line_for_position(self, text: str, position: int) -> str:
        start = text.rfind("\n", 0, position) + 1
        end = text.find("\n", position)
        if end == -1:
            end = len(text)
        return self._clean_label(text[start:end])

    def _lines(self, text: str) -> list[str]:
        return [self._clean_label(line) for line in text.splitlines() if self._clean_label(line)]

    @staticmethod
    def _clean_identifier(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9./-]", "", value).strip(" .-/")

    @staticmethod
    def _clean_label(value: str) -> str:
        return re.sub(r"\s{2,}", " ", value).strip(" :-")

    @staticmethod
    def _normalize(value: str) -> str:
        text = unicodedata.normalize("NFKD", sanitize_text_for_database(value))
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return re.sub(r"\s+", " ", text.lower()).strip()
