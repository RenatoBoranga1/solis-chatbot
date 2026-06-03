from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ConsumptionHistoryItem:
    period: str
    consumption_kwh: float
    bill_amount: float | None = None


@dataclass
class EnergyBillParseResult:
    distributor: str | None = None
    customer_name: str | None = None
    customer_document_masked: str | None = None
    installation_number: str | None = None
    city: str | None = None
    state: str | None = None
    reference_month: str | None = None
    due_date: str | None = None
    current_consumption_kwh: float | None = None
    current_bill_amount: float | None = None
    average_consumption_kwh: float | None = None
    average_bill_amount: float | None = None
    min_consumption_kwh: float | None = None
    max_consumption_kwh: float | None = None
    estimated_system_power_kwp: float | None = None
    estimated_monthly_generation_kwh: float | None = None
    estimated_monthly_savings: float | None = None
    confidence_score: float = 0
    needs_human_review: bool = True
    missing_fields: list[str] = field(default_factory=list)
    parsed_fields: dict[str, Any] = field(default_factory=dict)
    history: list[ConsumptionHistoryItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = self.__dict__.copy()
        data["history"] = [item.__dict__.copy() for item in self.history]
        return data


class EnergyBillParser(Protocol):
    name: str

    def can_parse(self, text: str, metadata: dict[str, Any] | None = None) -> bool:
        ...

    def parse(self, text: str, metadata: dict[str, Any] | None = None) -> EnergyBillParseResult:
        ...


MONTHS = {
    "jan": "01",
    "janeiro": "01",
    "fev": "02",
    "fevereiro": "02",
    "mar": "03",
    "marco": "03",
    "março": "03",
    "abr": "04",
    "abril": "04",
    "mai": "05",
    "maio": "05",
    "jun": "06",
    "junho": "06",
    "jul": "07",
    "julho": "07",
    "ago": "08",
    "agosto": "08",
    "set": "09",
    "setembro": "09",
    "out": "10",
    "outubro": "10",
    "nov": "11",
    "novembro": "11",
    "dez": "12",
    "dezembro": "12",
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def parse_decimal(value: str | None) -> float | None:
    if not value:
        return None
    clean = value.strip()
    clean = re.sub(r"[^\d,.-]", "", clean)
    if not clean:
        return None
    if "," in clean and "." in clean:
        clean = clean.replace(".", "").replace(",", ".")
    elif "," in clean:
        clean = clean.replace(",", ".")
    try:
        return float(clean)
    except ValueError:
        return None


def parse_brl_amount(value: str | None) -> float | None:
    return parse_decimal(value)


def mask_document(text: str | None) -> str | None:
    if not text:
        return None
    value = re.sub(r"\D", "", text)
    if len(value) == 11:
        return f"***.{value[3:6]}.{value[6:9]}-**"
    if len(value) == 14:
        return f"**.{value[2:5]}.{value[5:8]}/****-**"
    return None


def sanitize_raw_excerpt(text: str, limit: int = 1200) -> str:
    excerpt = text[:limit]
    excerpt = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[email mascarado]", excerpt)
    excerpt = re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "[documento mascarado]", excerpt)
    excerpt = re.sub(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", "[documento mascarado]", excerpt)
    return excerpt


def period_from_match(month: str, year: str | None = None) -> str:
    month_clean = month.strip().lower().replace(".", "")
    month_number = MONTHS.get(month_clean[:3], MONTHS.get(month_clean))
    if not month_number:
        return month
    year_value = year or ""
    if len(year_value) == 2:
        year_value = f"20{year_value}"
    return f"{year_value or '0000'}-{month_number}"
