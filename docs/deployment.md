# Deployment checklist

Use este checklist antes de homologar ou publicar o Solis Chatbot com WhatsApp Cloud API oficial.

## Ambiente

- Configurar HTTPS no dominio real.
- Configurar `APP_ENV=production`.
- Configurar `APP_DEBUG=false`.
- Restringir `FRONTEND_ORIGINS` aos dominios oficiais.
- Trocar credenciais padrao do usuario admin.
- Usar `JWT_SECRET_KEY` forte.
- Usar `FIELD_ENCRYPTION_KEY` forte.

## WhatsApp Cloud API

- Configurar `WHATSAPP_ACCESS_TOKEN`.
- Configurar `WHATSAPP_PHONE_NUMBER_ID`.
- Configurar `WHATSAPP_BUSINESS_ACCOUNT_ID`.
- Configurar `WHATSAPP_VERIFY_TOKEN`.
- Configurar `WHATSAPP_APP_SECRET`.
- Criar e aprovar template `continuar_atendimento_site` no WhatsApp Manager para convites iniciados pela empresa.
- Configurar callback `https://seu-dominio.com/webhook/whatsapp` na Meta.
- Assinar o campo `messages`.
- Validar `GET /webhook/whatsapp` no painel da Meta.
- Confirmar que assinatura ausente ou invalida retorna `403` em producao.

## Análise Inteligente

- Configurar `ENABLE_GENERATIVE_AI=false` para usar apenas fallback por regras.
- Configurar `OPENAI_API_KEY` somente em ambientes que usarão IA generativa.
- Configurar `AI_PROVIDER=openai`.
- Configurar `AI_MODEL` conforme política de custo e qualidade.
- Confirmar que análises mascaram dados sensíveis.
- Orientar atendentes a revisar respostas sugeridas antes do envio.

## Banco e migrations

```bash
cd backend
alembic upgrade head
```

Confirmar tabelas:

- `messages` com `provider` e `provider_message_id`;
- indice unico `ux_messages_provider_message_id`;
- `webhook_events`;
- `attachments`.
- `ai_analyses`.
- `knowledge_base_articles` com campos de vídeo e material de apoio.
- `conversation_channel_links`.
- `proposals`.
- `proposal_items`.
- `proposal_price_items`.
- `proposal_share_links`.
- `proposal_customer_responses`.
- `proposal_events`.
- `proposal_followups`.
- `company_settings`.

## Omnichannel

- Testar `POST /chat/conversations/{conversation_id}/continue-whatsapp`.
- Confirmar que casos de alta gravidade exigem revisão humana.
- Confirmar que telefones estão normalizados apenas com dígitos.
- Confirmar que resposta `SIM` no WhatsApp cria conversa vinculada ao atendimento do site.
- Monitorar links com status `failed`, `expired` ou `pending` antigo.

## Propostas comerciais

- Configurar `PROPOSAL_STORAGE_PATH`.
- Configurar `FRONTEND_ORIGINS` com o dominio publico que servira `/proposta/{token}`.
- Configurar dados da empresa para o PDF: `COMPANY_NAME`, `COMPANY_PHONE`, `COMPANY_EMAIL`, `COMPANY_WEBSITE`, `COMPANY_ADDRESS`, `COMPANY_LOGO_PATH`, `COMPANY_PRIMARY_COLOR` e `COMPANY_SECONDARY_COLOR`.
- Revisar a aba `Configuracoes comerciais` no painel antes da primeira proposta real.
- Configurar SMTP para envio real por e-mail: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME` e `SMTP_USE_TLS`.
- Cadastrar e revisar a tabela de precos antes de gerar propostas reais a partir de lead.
- Confirmar que propostas sem tabela ativa continuam com valores zerados para revisao manual.
- Nao enviar caminho local do PDF ao cliente.
- Validar envio manual, WhatsApp, e-mail e link seguro em ambiente de homologacao.
- Validar pagina publica `https://seu-dominio.com/proposta/{token}`.
- Validar download protegido em `/public/proposals/{token}/pdf`.
- Validar resposta digital do cliente: interessado, aceite, recusa, ajuste e consultor.
- Validar revogacao e expiracao de link seguro.
- Validar criacao e conclusao de follow-ups comerciais.
- Garantir que a pasta de PDFs tenha backup e controle de acesso.
- Revisar permissões dos perfis `admin`, `comercial` e `gestor`.
- Validar geração de PDF antes da homologação.
- Em produção, armazenar PDFs em storage privado, como S3 ou Cloudflare R2.
- Para envio por WhatsApp fora da janela de 24 horas, criar template aprovado pela Meta.
- Reforçar processo interno de revisão humana antes de enviar proposta ao cliente.

## Base multimídia

- Substituir placeholders de vídeos do seed por links oficiais.
- Revisar artigos antes de ativar `send_video_with_answer`.
- Não ativar vídeo automático para instruções com risco elétrico.
- Conferir preview da resposta no painel.

## Testes

```bash
cd backend
python -m unittest discover tests
```

Os testes devem cobrir webhook, assinatura, deduplicacao, anexos, auditoria, `send_errors`, continuidade omnichannel, propostas, tabela de precos, link seguro, resposta digital, follow-ups, configuracoes comerciais, classificacao de gravidade e handoff.
Também devem cobrir análise por regras, lead quente, chamado crítico, resposta sugerida e endpoints de IA.

## Observabilidade e seguranca

- Ativar logs estruturados.
- Nao registrar token, payload bruto, documentos ou telefone completo em logs.
- Monitorar `send_errors`.
- Monitorar eventos `webhook_events.processed=false`.
- Configurar backup do PostgreSQL.
- Configurar politica de retencao LGPD.
- Configurar WAF/rate limit no dominio publico.

## Proximas evolucoes recomendadas

- Processar webhooks em fila/worker com Redis.
- Armazenar midias em S3, R2 ou storage equivalente.
- Armazenar PDFs de propostas em storage privado com URL temporária.
- Criar templates oficiais para mensagens fora da janela de 24 horas.
- Adicionar CI/CD com testes e migrations em release.
