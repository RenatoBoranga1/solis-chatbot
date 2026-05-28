from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import KnowledgeBaseArticle, UnansweredQuestion
from app.services.intent import normalize


@dataclass(frozen=True)
class KnowledgeAnswer:
    answer: str | None
    article_id: str | None
    confidence: float


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

        return KnowledgeAnswer(answer=best_article.answer, article_id=best_article.id, confidence=min(best_score, 0.95))

    def record_unanswered(self, question: str, conversation_id: str | None, intent: str | None) -> None:
        self.db.add(
            UnansweredQuestion(
                conversation_id=conversation_id,
                question=question,
                detected_intent=intent,
            )
        )

