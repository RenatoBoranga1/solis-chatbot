from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class IntentResult:
    name: str
    confidence: float
    matched_terms: list[str]


INTENT_PATTERNS: dict[str, list[str]] = {
    "orcamento": [
        "orcamento",
        "cotacao",
        "quanto custa",
        "preco",
        "valor",
        "instalar energia solar",
        "quero instalar",
        "placa solar",
        "sistema solar",
    ],
    "viabilidade": ["vale a pena", "compensa", "viabilidade", "posso instalar", "meu telhado"],
    "economia_conta": ["economia", "conta de luz", "reduzir conta", "quanto vou economizar"],
    "creditos_energia": ["credito", "creditos", "compensacao", "energia injetada", "saldo de energia"],
    "financiamento": ["financiamento", "financiar", "parcelar", "banco", "credito solar"],
    "acompanhar_instalacao": ["instalacao", "obra", "andamento", "equipe vai instalar"],
    "acompanhar_homologacao": ["homologacao", "concessionaria", "distribuidora", "vistoria"],
    "manutencao": ["manutencao", "limpeza", "preventiva", "lavar placa", "limpar placa"],
    "problema_inversor": ["inversor", "luz vermelha", "desligado", "erro no inversor"],
    "baixa_geracao": ["baixa geracao", "gerando pouco", "nao esta gerando", "sem geracao", "zerou"],
    "erro_monitoramento": ["aplicativo", "app", "monitoramento", "nao atualiza", "sem atualizar"],
    "wifi_inversor": ["wifi", "wi-fi", "internet", "roteador", "conexao"],
    "garantia": ["garantia", "troca", "cobertura", "defeito"],
    "reclamacao": ["reclamacao", "reclamar", "ninguem resolve", "cansado", "procon", "processo"],
    "humano": ["humano", "atendente", "pessoa", "falar com alguem", "consultor", "vendedor"],
    "anexos": ["comprovante", "foto", "print", "documento", "pdf", "anexo"],
    "visita_tecnica": ["visita tecnica", "agendar visita", "tecnico aqui", "ir no local"],
    "comercial": ["setor comercial", "consultor comercial", "vendas", "contrato"],
    "suporte_tecnico": ["suporte", "tecnico", "chamado", "problema", "defeito"],
}


def normalize(text: str) -> str:
    without_accents = "".join(
        char for char in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", without_accents).strip()


def classify_intent(message: str) -> IntentResult:
    text = normalize(message)
    scores: list[tuple[str, float, list[str]]] = []

    for intent, patterns in INTENT_PATTERNS.items():
        matched = [pattern for pattern in patterns if normalize(pattern) in text]
        if not matched:
            continue
        length_bonus = sum(min(len(pattern), 24) for pattern in matched) / 100
        score = min(0.99, 0.48 + (0.13 * len(matched)) + length_bonus)
        scores.append((intent, score, matched))

    if not scores:
        return IntentResult(name="outros", confidence=0.2, matched_terms=[])

    scores.sort(key=lambda item: item[1], reverse=True)
    winner = scores[0]
    return IntentResult(name=winner[0], confidence=winner[1], matched_terms=winner[2])


def is_commercial_intent(intent: str) -> bool:
    return intent in {"orcamento", "viabilidade", "economia_conta", "financiamento", "comercial"}


def is_support_intent(intent: str) -> bool:
    return intent in {
        "manutencao",
        "problema_inversor",
        "baixa_geracao",
        "erro_monitoramento",
        "wifi_inversor",
        "garantia",
        "visita_tecnica",
        "suporte_tecnico",
        "acompanhar_instalacao",
        "acompanhar_homologacao",
    }

