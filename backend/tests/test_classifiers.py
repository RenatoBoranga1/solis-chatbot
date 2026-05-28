import unittest

from app.services.intent import classify_intent
from app.services.severity import classify_severity, is_electrical_risk


class IntentClassifierTest(unittest.TestCase):
    def test_budget_intent(self):
        result = classify_intent("Quero instalar energia solar e preciso de um orcamento")
        self.assertEqual(result.name, "orcamento")
        self.assertGreater(result.confidence, 0.6)

    def test_monitoring_app_intent(self):
        result = classify_intent("O app de monitoramento nao atualiza desde ontem")
        self.assertEqual(result.name, "erro_monitoramento")

    def test_human_request(self):
        result = classify_intent("Quero falar com atendente humano")
        self.assertEqual(result.name, "humano")


class SeverityClassifierTest(unittest.TestCase):
    def test_electrical_risk_is_high(self):
        result = classify_severity("Esta saindo cheiro de queimado do inversor")
        self.assertEqual(result.level, "alta")
        self.assertTrue(result.handoff_required)
        self.assertTrue(is_electrical_risk("Tem cheiro de queimado"))

    def test_low_generation_is_medium_or_high(self):
        result = classify_severity("Meu sistema esta gerando pouco")
        self.assertEqual(result.level, "media")

    def test_general_question_is_low(self):
        result = classify_severity("Tenho uma duvida sobre limpeza das placas")
        self.assertEqual(result.level, "baixa")


if __name__ == "__main__":
    unittest.main()

