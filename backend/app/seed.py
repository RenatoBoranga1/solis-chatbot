from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import KnowledgeBaseArticle, User


def seed() -> None:
    db = SessionLocal()
    try:
        admin = db.scalar(select(User).where(User.email == "admin@solarsolucoes.com.br"))
        if not admin:
            db.add(
                User(
                    name="Administrador Solar Soluções",
                    email="admin@solarsolucoes.com.br",
                    password_hash=hash_password("Solar@12345"),
                    role="admin",
                )
            )

        article = db.scalar(select(KnowledgeBaseArticle).where(KnowledgeBaseArticle.title == "Economia com energia solar"))
        if not article:
            db.add_all(
                [
                    KnowledgeBaseArticle(
                        title="Economia com energia solar",
                        question="Quanto posso economizar com energia solar?",
                        answer=(
                            "A economia depende do consumo, local de instalação, modalidade tarifária, "
                            "distribuidora e dimensionamento do projeto. A Solar Soluções faz uma análise "
                            "personalizada da conta de energia antes de estimar economia e potência ideal."
                        ),
                        category="Economia na conta de luz",
                        keywords=["economia", "conta de luz", "energia solar", "potência ideal"],
                    ),
                    KnowledgeBaseArticle(
                        title="Aplicativo de monitoramento sem atualizar",
                        question="O aplicativo de monitoramento não atualiza. O que pode ser?",
                        answer=(
                            "Quando o aplicativo não atualiza, uma causa comum é falha de internet ou perda de "
                            "conexão do inversor com o roteador. Isso não significa necessariamente que o sistema "
                            "parou de gerar, mas a equipe técnica deve verificar os dados e, se necessário, reconfigurar a conexão."
                        ),
                        category="Monitoramento remoto",
                        keywords=["aplicativo", "app", "monitoramento", "wifi", "internet"],
                    ),
                    KnowledgeBaseArticle(
                        title="Limpeza das placas solares",
                        question="Quando devo limpar as placas solares?",
                        answer=(
                            "A limpeza das placas depende do ambiente, poeira, folhas e período sem chuva. "
                            "A recomendação deve considerar segurança de acesso ao telhado e orientação técnica. "
                            "O cliente não deve subir no telhado sem equipamento e condições adequadas."
                        ),
                        category="Limpeza das placas",
                        keywords=["limpeza", "placas", "manutenção preventiva", "segurança"],
                    ),
                ]
            )
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
