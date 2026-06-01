import unittest

from pydantic import ValidationError

from app.models import AIAnalysis, AuditLog, Conversation, KnowledgeBaseArticle, Message, utc_now
from app.schemas import ChatMessageIn, KnowledgeIn, KnowledgeOut
from app.services.ai_analysis import AIAnalysisService
from app.services.conversation import ConversationService
from app.services.rag import KnowledgeService


class FakeScalarResult:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


class FakeDb:
    def __init__(self, articles=None, objects=None):
        self.articles = articles or []
        self.objects = objects or {}
        self.added = []

    def get(self, model, item_id):
        return self.objects.get((model, item_id))

    def scalar(self, _statement):
        return None

    def scalars(self, _statement):
        return FakeScalarResult(self.articles)

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        for index, obj in enumerate(self.added, start=1):
            if getattr(obj, "id", None) is None:
                setattr(obj, "id", f"fake-id-{index}")
            if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
                setattr(obj, "created_at", utc_now())

    def commit(self):
        return None

    def refresh(self, _obj):
        return None


def multimedia_article(send_video: bool = True) -> KnowledgeBaseArticle:
    return KnowledgeBaseArticle(
        id="article-1",
        title="Limpeza das placas solares",
        question="Quando devo limpar as placas solares?",
        answer="A limpeza das placas deve respeitar condições seguras de acesso.",
        category="Limpeza das placas",
        keywords=["limpeza", "placas", "manutenção preventiva"],
        active=True,
        use_for_ai=True,
        video_title="Como limpar placas solares com segurança",
        video_url="https://youtu.be/limpeza-segura",
        send_video_with_answer=send_video,
        send_resource_with_answer=False,
        created_at=utc_now(),
    )


class KnowledgeMultimediaTest(unittest.TestCase):
    def test_create_article_schema_accepts_valid_youtube_url(self):
        payload = KnowledgeIn(
            title="Vídeo de limpeza",
            question="Como limpar placas?",
            answer="Use apenas orientações oficiais.",
            category="Limpeza das placas",
            keywords=["limpeza"],
            video_title="Como limpar placas solares com segurança",
            video_url="https://www.youtube.com/watch?v=abc123",
            send_video_with_answer=True,
        )

        self.assertEqual(payload.video_url, "https://www.youtube.com/watch?v=abc123")
        self.assertTrue(payload.send_video_with_answer)

    def test_rejects_unsafe_url(self):
        with self.assertRaises(ValidationError):
            KnowledgeIn(
                title="URL insegura",
                question="Teste",
                answer="Teste",
                category="Segurança elétrica",
                video_url="javascript:alert(1)",
            )

    def test_output_schema_returns_multimedia_fields(self):
        article = multimedia_article()

        output = KnowledgeOut.model_validate(article)

        self.assertEqual(output.video_title, "Como limpar placas solares com segurança")
        self.assertEqual(output.video_url, "https://youtu.be/limpeza-segura")
        self.assertTrue(output.send_video_with_answer)

    def test_knowledge_answer_includes_video_when_enabled(self):
        service = KnowledgeService(FakeDb(articles=[multimedia_article()]))

        answer = service.answer_from_base("Tenho dúvida sobre limpeza das placas")

        self.assertIn("Vídeo recomendado:", answer.answer)
        self.assertIn("https://youtu.be/limpeza-segura", answer.answer)

    def test_chatbot_includes_video_for_safe_educational_question(self):
        db = FakeDb(articles=[multimedia_article()])
        response = ConversationService(db).handle_message(
            ChatMessageIn(channel="site", message="Tenho dúvida sobre limpeza das placas")
        )

        self.assertIn("Vídeo recomendado:", response.response)
        self.assertIn("https://youtu.be/limpeza-segura", response.response)

    def test_chatbot_does_not_include_video_for_electrical_risk(self):
        db = FakeDb(articles=[multimedia_article()])
        response = ConversationService(db).handle_message(
            ChatMessageIn(channel="site", message="Está saindo cheiro de queimado do inversor")
        )

        self.assertNotIn("https://youtu.be/limpeza-segura", response.response)
        self.assertTrue(response.handoff_required)
        self.assertEqual(response.severity, "alta")

    def test_ai_analysis_suggests_video_when_article_matches(self):
        conversation = Conversation(
            id="conversation-1",
            customer_id="customer-1",
            channel="site",
            status="open",
            intent="manutencao",
            severity="baixa",
            summary="Cliente perguntou sobre limpeza das placas.",
            collected_data={},
            bot_resolved=False,
            transferred_to_human=False,
        )
        conversation.messages = [
            Message(
                id="message-1",
                conversation_id=conversation.id,
                sender_type="customer",
                content="Tenho dúvida sobre limpeza das placas",
                created_at=utc_now(),
            )
        ]
        db = FakeDb(
            articles=[multimedia_article()],
            objects={(Conversation, conversation.id): conversation},
        )

        analysis = AIAnalysisService(db).analyze_conversation(conversation.id)

        self.assertIn("Enviar vídeo oficial", analysis.recommended_next_action)
        self.assertIn("https://youtu.be/limpeza-segura", analysis.suggested_reply)
        self.assertTrue([item for item in db.added if isinstance(item, AIAnalysis)])
        self.assertTrue([item for item in db.added if isinstance(item, AuditLog)])


if __name__ == "__main__":
    unittest.main()
