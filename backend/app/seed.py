from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import KnowledgeBaseArticle, ProposalKit, User


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

        # Substitua os placeholders abaixo pelos vídeos oficiais antes de ativar envio automático.
        seed_articles = [
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
                video_title="Como verificar o aplicativo de monitoramento",
                video_url="https://www.youtube.com/watch?v=EXEMPLO_APP_MONITORAMENTO",
                resource_type="youtube",
                send_video_with_answer=False,
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
                video_title="Como limpar placas solares com segurança",
                video_url="https://www.youtube.com/watch?v=EXEMPLO_LIMPEZA_PLACAS",
                resource_type="youtube",
                send_video_with_answer=False,
            ),
            KnowledgeBaseArticle(
                title="Ligar e desligar o inversor com segurança",
                question="Como ligar ou desligar o inversor?",
                answer=(
                    "O inversor deve ser operado apenas conforme orientações oficiais e sem abrir equipamentos, "
                    "quadros elétricos ou cabos. Em caso de erro, cheiro de queimado, faísca ou choque, "
                    "não mexa no equipamento e acione a equipe técnica."
                ),
                category="Inversores",
                keywords=["inversor", "ligar inversor", "desligar inversor", "segurança"],
                video_title="Como ligar e desligar o inversor com segurança",
                video_url="https://www.youtube.com/watch?v=EXEMPLO_INVERSOR_SEGURANCA",
                resource_type="youtube",
                send_video_with_answer=False,
            ),
        ]
        for seed_article in seed_articles:
            article = db.scalar(select(KnowledgeBaseArticle).where(KnowledgeBaseArticle.title == seed_article.title))
            if not article:
                db.add(seed_article)
                continue
            for field in ["video_title", "video_url", "resource_type"]:
                if getattr(seed_article, field) and not getattr(article, field):
                    setattr(article, field, getattr(seed_article, field))

        # Kits demonstrativos: revise faixas, equipamentos e valores antes de usar em producao.
        seed_kits = [
            ProposalKit(
                name="Kit Solar 2,75 kWp",
                description="Kit demonstrativo para leads de baixo consumo.",
                min_monthly_consumption_kwh=250,
                max_monthly_consumption_kwh=340,
                min_power_kwp=2.1,
                max_power_kwp=2.9,
                suggested_power_kwp=2.75,
                estimated_monthly_generation_kwh=313,
                module_count=5,
                module_power_wp=550,
                inverter_power_kw=3,
                base_price=0,
                sort_order=10,
                notes="Valor base zerado. Substitua por preco revisado pela Solar Solucoes.",
            ),
            ProposalKit(
                name="Kit Solar 3,30 kWp",
                description="Kit demonstrativo para consumo residencial intermediario.",
                min_monthly_consumption_kwh=341,
                max_monthly_consumption_kwh=430,
                min_power_kwp=2.91,
                max_power_kwp=3.6,
                suggested_power_kwp=3.3,
                estimated_monthly_generation_kwh=390,
                module_count=6,
                module_power_wp=550,
                inverter_power_kw=4,
                base_price=0,
                sort_order=20,
                notes="Valor base zerado. Substitua por preco revisado pela Solar Solucoes.",
            ),
            ProposalKit(
                name="Kit Solar 4,40 kWp",
                description="Kit demonstrativo para consumo residencial/comercial medio.",
                min_monthly_consumption_kwh=431,
                max_monthly_consumption_kwh=570,
                min_power_kwp=3.61,
                max_power_kwp=4.8,
                suggested_power_kwp=4.4,
                estimated_monthly_generation_kwh=520,
                module_count=8,
                module_power_wp=550,
                inverter_power_kw=5,
                base_price=0,
                sort_order=30,
                notes="Valor base zerado. Substitua por preco revisado pela Solar Solucoes.",
            ),
            ProposalKit(
                name="Kit Solar 5,50 kWp",
                description="Kit demonstrativo para consumo maior e pre-propostas robustas.",
                min_monthly_consumption_kwh=571,
                max_monthly_consumption_kwh=710,
                min_power_kwp=4.81,
                max_power_kwp=6.0,
                suggested_power_kwp=5.5,
                estimated_monthly_generation_kwh=650,
                module_count=10,
                module_power_wp=550,
                inverter_power_kw=5,
                base_price=0,
                sort_order=40,
                notes="Valor base zerado. Substitua por preco revisado pela Solar Solucoes.",
            ),
        ]
        for seed_kit in seed_kits:
            kit = db.scalar(select(ProposalKit).where(ProposalKit.name == seed_kit.name))
            if not kit:
                db.add(seed_kit)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
