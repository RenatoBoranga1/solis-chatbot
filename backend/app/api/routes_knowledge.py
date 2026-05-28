from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models import KnowledgeBaseArticle
from app.schemas import KnowledgeIn, KnowledgeOut

router = APIRouter(prefix="/knowledge", tags=["Base de conhecimento"])


@router.get("", response_model=list[KnowledgeOut])
def list_articles(
    db: Session = Depends(get_db),
    _user=Depends(require_roles("admin", "suporte", "comercial", "gestor")),
) -> list[KnowledgeBaseArticle]:
    return list(db.scalars(select(KnowledgeBaseArticle).order_by(desc(KnowledgeBaseArticle.updated_at))).all())


@router.post("", response_model=KnowledgeOut)
def create_article(
    payload: KnowledgeIn,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("admin", "suporte", "comercial", "gestor")),
) -> KnowledgeBaseArticle:
    article = KnowledgeBaseArticle(**payload.model_dump())
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


@router.put("/{article_id}", response_model=KnowledgeOut)
def update_article(
    article_id: str,
    payload: KnowledgeIn,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("admin", "suporte", "comercial", "gestor")),
) -> KnowledgeBaseArticle:
    article = db.get(KnowledgeBaseArticle, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    for field, value in payload.model_dump().items():
        setattr(article, field, value)
    db.commit()
    db.refresh(article)
    return article


@router.delete("/{article_id}")
def delete_article(
    article_id: str,
    db: Session = Depends(get_db),
    _user=Depends(require_roles("admin", "gestor")),
) -> dict[str, str]:
    article = db.get(KnowledgeBaseArticle, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    db.delete(article)
    db.commit()
    return {"status": "deleted"}

