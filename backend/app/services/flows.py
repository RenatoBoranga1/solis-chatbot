from dataclasses import dataclass


@dataclass(frozen=True)
class FlowQuestion:
    key: str
    question: str
    customer_field: str | None = None


BUDGET_FLOW: list[FlowQuestion] = [
    FlowQuestion("name", "Perfeito, vou te ajudar com o orçamento. Qual é seu nome completo?", "name"),
    FlowQuestion("city_state", "Em qual cidade e estado fica o imóvel?", None),
    FlowQuestion("phone", "Qual telefone ou WhatsApp a equipe pode usar para contato?", "phone"),
    FlowQuestion("email", "Se puder informar, qual é seu e-mail?", "email"),
    FlowQuestion(
        "property_type",
        "O imóvel é residência, comércio, indústria, propriedade rural, condomínio ou usina?",
        None,
    ),
    FlowQuestion("average_bill", "Qual é o valor médio mensal da sua conta de energia?", None),
    FlowQuestion("utility_company", "Qual é a distribuidora de energia que atende o imóvel?", None),
    FlowQuestion("has_energy_bill", "Você possui a conta de luz em PDF ou foto para enviar depois?", None),
    FlowQuestion("ownership", "O imóvel é próprio ou alugado?", None),
    FlowQuestion("roof_type", "O telhado é de cerâmica, fibrocimento, metálico, laje ou a instalação seria em solo?", None),
    FlowQuestion("financing_interest", "Você tem interesse em financiamento?", None),
    FlowQuestion("best_contact_time", "Qual é o melhor horário para a equipe comercial falar com você?", None),
]


SUPPORT_FLOW: list[FlowQuestion] = [
    FlowQuestion("inverter_on", "Entendi, vou te ajudar com isso. O inversor está ligado?", None),
    FlowQuestion("error_message", "Aparece alguma mensagem de erro no inversor ou no aplicativo?", None),
    FlowQuestion("started_at", "Desde quando o problema começou?", None),
    FlowQuestion(
        "recent_event",
        "Houve chuva forte, queda de energia, manutenção elétrica ou alteração na internet antes do problema?",
        None,
    ),
    FlowQuestion("attachments", "Se puder, envie foto do inversor ou print do aplicativo.", None),
    FlowQuestion("generation_status", "O sistema está totalmente parado ou apenas gerando menos?", None),
    FlowQuestion("name", "Obrigado pelas informações. Qual é seu nome para registrar o chamado?", "name"),
    FlowQuestion("document_or_code", "Você tem CPF/CNPJ ou código de cliente para localizar o cadastro?", None),
    FlowQuestion("city", "Em qual cidade fica a instalação?", "city"),
    FlowQuestion("phone", "Qual telefone ou WhatsApp para retorno da equipe técnica?", "phone"),
    FlowQuestion("installation_address", "Qual é o endereço da instalação?", None),
    FlowQuestion("problem_type", "Qual é o tipo de problema percebido?", None),
    FlowQuestion("inverter_model", "Você sabe a marca ou modelo do inversor?", None),
]


APP_FLOW: list[FlowQuestion] = [
    FlowQuestion("wifi_changed", "O Wi-Fi ou a senha da internet foram trocados recentemente?", None),
    FlowQuestion("router_restarted", "O roteador foi reiniciado ou ficou sem energia nos últimos dias?", None),
    FlowQuestion("app_print", "Pode enviar um print da tela do aplicativo que não atualiza?", None),
]


def get_flow_questions(flow: str) -> list[FlowQuestion]:
    if flow == "orcamento":
        return BUDGET_FLOW
    if flow == "suporte":
        return SUPPORT_FLOW
    if flow == "app_monitoramento":
        return APP_FLOW
    return []


def next_missing_question(flow: str, collected: dict) -> FlowQuestion | None:
    for question in get_flow_questions(flow):
        if not collected.get(question.key):
            return question
    return None


def summarize_collected_data(collected: dict) -> str:
    visible_items = []
    labels = {
        "name": "Nome",
        "city_state": "Cidade/estado",
        "city": "Cidade",
        "phone": "Telefone",
        "email": "E-mail",
        "property_type": "Tipo de imóvel",
        "average_bill": "Conta média",
        "utility_company": "Distribuidora",
        "roof_type": "Telhado",
        "financing_interest": "Interesse em financiamento",
        "problem_type": "Problema",
        "inverter_model": "Inversor",
        "error_message": "Erro informado",
        "started_at": "Início",
        "recent_event": "Evento recente",
        "generation_status": "Status de geração",
    }
    for key, label in labels.items():
        if collected.get(key):
            visible_items.append(f"{label}: {collected[key]}")
    return "; ".join(visible_items)
