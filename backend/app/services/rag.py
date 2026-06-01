from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KnowledgeBaseArticle, UnansweredQuestion
from app.services.intent import normalize
from app.services.severity import is_electrical_risk


@dataclass(frozen=True)
class KnowledgeAnswer:
    answer: str | None
    article_id: str | None
    confidence: float
    video_url: str | None = None
    video_title: str | None = None
    resource_url: str | None = None
    resource_title: str | None = None
    resource_type: str | None = None


class KnowledgeService:
    def __init__(self, db: Session):
        self.db = db

    def answer_from_base(self, question: str, category: str | None = None) -> KnowledgeAnswer:
        text = normalize(question)
        statement = select(KnowledgeBaseArticle).where(
            KnowledgeBaseArticle.active.is_(True),
            KnowledgeBaseArticle.use_for_ai.is_(True),
        )
        if category:
            statement = statement.where(KnowledgeBaseArticle.category == category)

        articles = list(self.db.scalars(statement).all())
        best_article: KnowledgeBaseArticle | None = None
        best_score = 0.0

        for article in articles:
            terms = [article.title, article.question, article.category, *article.keywords]
            normalized_terms = [normalize(term) for term in terms if term]
            score = 0.0
            for term in normalized_terms:
                if term and term in text:
                    score += min(0.35, len(term) / 80)
            for token in text.split():
                if len(token) > 3 and token in normalize(article.question + " " + article.answer):
                    score += 0.02
            if score > best_score:
                best_score = score
                best_article = article

        if not best_article or best_score < 0.18:
            return KnowledgeAnswer(answer=None, article_id=None, confidence=best_score)

        return KnowledgeAnswer(
            answer=self._format_answer(best_article, question),
            article_id=best_article.id,
            confidence=min(best_score, 0.95),
            video_url=best_article.video_url,
            video_title=best_article.video_title,
            resource_url=best_article.resource_url,
            resource_title=best_article.resource_title,
            resource_type=best_article.resource_type,
        )

    def record_unanswered(self, question: str, conversation_id: str | None, intent: str | None) -> None:
        self.db.add(
            UnansweredQuestion(
                conversation_id=conversation_id,
                question=question,
                detected_intent=intent,
            )
        )

    def find_matching_article(self, question: str, category: str | None = None) -> KnowledgeBaseArticle | None:
        answer = self.answer_from_base(question, category)
        if not answer.article_id:
            return None
        article = self.db.get(KnowledgeBaseArticle, answer.article_id)
        if article:
            return article
        articles = list(self.db.scalars(select(KnowledgeBaseArticle)).all())
        return next((item for item in articles if item.id == answer.article_id), None)

    def _format_answer(self, article: KnowledgeBaseArticle, question: str) -> str:
        sections = [article.answer]
        normalized_question = normalize(question)

        if "limpeza" in normalized_question and "placa" in normalized_question:
            sections.append(
                "Atenção: Faça a limpeza apenas em condições seguras e, se houver risco de altura, "
                "telhado molhado ou dificuldade de acesso, solicite equipe especializada."
            )

        if "inversor" in normalized_question and any(term in normalized_question for term in ["ligar", "desligar"]):
            sections.append(
                "Atenção: Siga apenas orientações oficiais e não abra equipamentos, quadros elétricos ou cabos. "
                "Em caso de erro, cheiro de queimado, faísca ou choque, não mexa no equipamento e acione a equipe técnica."
            )

        if not is_electrical_risk(question) and article.send_video_with_answer and article.video_url:
            sections.append(
                "\n".join(
                    [
                        "Vídeo recomendado:",
                        article.video_title or "Vídeo oficial da Solar Soluções",
                        article.video_url,
                    ]
                )
            )

        if article.send_resource_with_answer and article.resource_url:
            sections.append(
                "\n".join(
                    [
                        "Material de apoio:",
                        article.resource_title or "Material oficial da Solar Soluções",
                        article.resource_url,
                    ]
                )
            )

        return "\n\n".join(section for section in sections if section)
