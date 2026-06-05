from __future__ import annotations

import re
from typing import Any

from app.services.energy_bill_parsers.base import EnergyBillParseResult
from app.services.energy_bill_parsers.generic import GenericEnergyBillParser


class CPFLEnergyBillParser(GenericEnergyBillParser):
    name = "cpfl"

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
        tariff_flag = result.parsed_fields.get("tariff_flag") or self._extract_tariff_flag(text, debug)
        if result.installation_number and self._is_tariff_flag(result.installation_number):
            debug["discarded_fields"]["installation_number"] = (
                f"{result.installation_number} descartado por parecer bandeira tarifaria em conta CPFL."
            )
            tariff_flag = tariff_flag or self._canonical_tariff_flag(result.installation_number)
            result.installation_number = None
        if not result.installation_number:
            result.installation_number = self._extract_cpfl_installation(text, debug)
        result.parsed_fields = {
            **result.parsed_fields,
            "parser": self.name,
            "tariff_flag": tariff_flag,
            "customer_unit_number": result.installation_number,
            "discarded_fields": debug["discarded_fields"],
            "anchors": debug["anchors"],
            "source_snippets": debug["source_snippets"],
            "review_warnings": debug["review_warnings"],
            "cpfl_rules_applied": True,
        }
        return result

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
