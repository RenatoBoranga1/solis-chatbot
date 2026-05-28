# Arquitetura

## Componentes

- FastAPI exposta como API central.
- PostgreSQL como banco transacional.
- Alembic para migrations.
- Redis opcional para rate limit, filas, locks e tarefas futuras.
- React para painel administrativo e demonstracao do widget.
- Widget JavaScript puro para incorporacao no site institucional.
- Adaptadores de canal para site, WhatsApp e futuros Instagram/Facebook.
- Servico de conhecimento preparado para RAG.
- Servico de IA generativa opcional com prompt oficial do Solis.

## Fluxo de mensagem

1. Canal recebe mensagem do cliente.
2. Adaptador normaliza para `ChatMessageIn`.
3. API persiste mensagem do cliente.
4. Classificador identifica intencao.
5. Classificador de gravidade avalia risco.
6. Orquestrador decide proxima pergunta, resposta, criacao de lead/ticket ou handoff.
7. Mensagem do Solis e persistida.
8. Canal entrega a resposta ao cliente.

## RAG

Inicialmente, o projeto usa recuperacao por categoria, palavras-chave e similaridade textual simples. A interface foi pensada para trocar por embeddings sem alterar os fluxos:

- gerar embedding ao salvar artigo ativo;
- buscar top-k por vetor;
- reranquear por regras de seguranca;
- enviar contexto oficial ao modelo;
- bloquear resposta quando a confianca for baixa.

## Seguranca

- JWT no painel.
- Perfis de acesso.
- Senhas com hash bcrypt.
- CORS restrito por variavel de ambiente.
- Rate limit via middleware simples, substituivel por Redis.
- Sanitizacao basica de entrada.
- Criptografia utilitaria para campos sensiveis.
- Auditoria de eventos criticos.

## Escalabilidade

Para producao, recomenda-se:

- workers FastAPI com Gunicorn/Uvicorn;
- filas para webhooks de WhatsApp;
- storage externo para anexos;
- logs estruturados;
- tracing e metricas;
- replica de leitura para dashboards pesados;
- feature flags para habilitar IA generativa gradualmente.

