from __future__ import annotations

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
        result.parsed_fields = {**result.parsed_fields, "parser": self.name}
        return result
