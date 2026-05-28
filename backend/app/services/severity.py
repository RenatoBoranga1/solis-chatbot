from dataclasses import dataclass

from app.services.intent import normalize


@dataclass(frozen=True)
class SeverityResult:
    level: str
    reason: str
    handoff_required: bool = False


HIGH_RISK_TERMS = [
    "cheiro de queimado",
    "queimado",
    "faisca",
    "faiscando",
    "fumaca",
    "curto",
    "choque",
    "risco eletrico",
    "barulho anormal",
    "aquecimento",
    "muito quente",
    "pegando fogo",
    "disjuntor desarmando toda hora",
    "processo",
    "procon",
    "reclame aqui",
    "prejuizo",
    "ninguem resolve",
]

MEDIUM_TERMS = [
    "sem geracao",
    "nao esta gerando",
    "zerou",
    "gerando pouco",
    "baixa geracao",
    "nao atualiza",
    "sem atualizar",
    "erro intermitente",
    "as vezes",
    "credito",
    "visita tecnica",
]

STOPPED_TERMS = [
    "sistema parado",
    "totalmente parado",
    "inversor desligado",
]

LOW_TERMS = [
    "duvida",
    "limpeza",
    "manutencao preventiva",
    "segunda via",
    "conta de luz",
    "aplicativo",
]


def classify_severity(message: str, intent: str | None = None) -> SeverityResult:
    text = normalize(message)

    for term in HIGH_RISK_TERMS:
        if normalize(term) in text:
            return SeverityResult("alta", f"Termo de alto risco identificado: {term}", True)

    for term in STOPPED_TERMS:
        if normalize(term) in text:
            return SeverityResult("alta", f"Sistema possivelmente parado: {term}", True)

    if intent == "reclamacao":
        return SeverityResult("alta", "Cliente demonstrou insatisfacao ou reclamacao grave.", True)

    for term in MEDIUM_TERMS:
        if normalize(term) in text:
            return SeverityResult("media", f"Ocorrencia tecnica de media gravidade: {term}", False)

    if intent in {"baixa_geracao", "erro_monitoramento", "wifi_inversor", "visita_tecnica"}:
        return SeverityResult("media", "Intencao tecnica normalmente requer triagem.", False)

    for term in LOW_TERMS:
        if normalize(term) in text:
            return SeverityResult("baixa", f"Dúvida ou solicitação simples: {term}", False)

    return SeverityResult("baixa", "Sem sinal de risco ou urgencia.", False)


def is_electrical_risk(message: str) -> bool:
    text = normalize(message)
    electrical_terms = [
        "cheiro de queimado",
        "faisca",
        "faiscando",
        "fumaca",
        "choque",
        "curto",
        "pegando fogo",
        "muito quente",
        "aquecimento",
    ]
    return any(normalize(term) in text for term in electrical_terms)
