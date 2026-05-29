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
- Configurar callback `https://seu-dominio.com/webhook/whatsapp` na Meta.
- Assinar o campo `messages`.
- Validar `GET /webhook/whatsapp` no painel da Meta.
- Confirmar que assinatura ausente ou invalida retorna `403` em producao.

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

## Testes

```bash
cd backend
python -m unittest discover tests
```

Os testes devem cobrir webhook, assinatura, deduplicacao, anexos, auditoria, `send_errors`, classificacao de gravidade e handoff.

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
- Criar templates oficiais para mensagens fora da janela de 24 horas.
- Adicionar CI/CD com testes e migrations em release.
