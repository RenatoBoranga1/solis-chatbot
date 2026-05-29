# WhatsApp Cloud API

Este guia descreve a integracao oficial do Solis com a WhatsApp Business Platform / Cloud API da Meta.

O código já está preparado para receber mensagens oficiais pelo webhook `/webhook/whatsapp`, registrar auditoria, deduplicar eventos, salvar anexos e responder pela Graph API. Para funcionar com um número real, ainda é necessário configurar Meta Business, Meta Developers App, produto WhatsApp, tokens e uma URL pública HTTPS.

## 1. App e numero

1. Crie um app Business em Meta for Developers.
2. Adicione o produto WhatsApp.
3. Configure ou vincule o numero de telefone.
4. Copie `Phone Number ID` e `WhatsApp Business Account ID`.
5. Gere um access token com permissao para envio de mensagens.

## 2. Variaveis

```env
APP_ENV=production
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_BUSINESS_ACCOUNT_ID=
WHATSAPP_VERIFY_TOKEN=solis_verify_token_dev
WHATSAPP_APP_SECRET=
WHATSAPP_API_VERSION=v20.0
```

Em producao, `WHATSAPP_APP_SECRET` e obrigatorio. Sem ele, o webhook rejeita chamadas porque nao consegue validar `X-Hub-Signature-256`.

## 3. Webhook

Callback:

```text
https://seu-dominio.com/webhook/whatsapp
```

Rotas implementadas:

- `GET /webhook/whatsapp`: validacao inicial da Meta com `hub.challenge`.
- `POST /webhook/whatsapp`: recebimento de eventos e mensagens.

Assine o campo `messages` no painel da Meta.

## 4. Teste local

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

Em outro terminal:

```bash
ngrok http 8000
```

Use a URL HTTPS do ngrok como callback:

```text
https://SEU_SUBDOMINIO.ngrok-free.app/webhook/whatsapp
```

Verify token para desenvolvimento:

```text
solis_verify_token_dev
```

Também é possível usar Cloudflare Tunnel, desde que a URL final seja HTTPS e aponte para o backend na porta `8000`.

## 5. Fluxo de entrada

1. A Meta chama `POST /webhook/whatsapp`.
2. O backend valida a assinatura quando `APP_ENV=production`.
3. O payload bruto e salvo em `webhook_events`.
4. O payload e convertido para `WhatsAppIncomingMessage`.
5. A deduplicacao consulta `messages(provider, provider_message_id)`.
6. Mensagens novas viram `ChatMessageIn`.
7. O `ConversationService` classifica intencao, gravidade, lead, ticket e handoff.
8. O `WhatsAppCloudService` envia a resposta pela Graph API.
9. O `WebhookEvent` e marcado como `processed=true` quando termina sem excecao.

## 6. Auditoria

Cada evento recebido gera um registro do modelo `WebhookEvent` em `webhook_events`:

- `provider`: sempre `whatsapp`;
- `event_id`: primeiro `message_id` encontrado, ou UUID quando nao houver mensagem;
- `payload`: JSON bruto recebido da Meta;
- `processed`: comeca `false` e vira `true` ao final;
- `error_message`: erro tecnico resumido quando houver excecao;
- `created_at`: data de recebimento.

O retorno da API nunca expoe o payload bruto.

## 7. Deduplicacao

Mensagens recebidas da Meta podem ser reenviadas. Antes de chamar o `ConversationService`, o webhook verifica:

```text
provider = whatsapp
provider_message_id = incoming.message_id
```

Se ja existir, o webhook:

- nao chama o `ConversationService`;
- nao envia resposta novamente;
- incrementa `duplicates`;
- marca o `WebhookEvent` como processado;
- retorna `duplicate_ignored` quando todas as mensagens forem duplicadas.

O indice unico `ux_messages_provider_message_id` protege o banco contra reprocessamento.

## 8. Anexos

Tipos suportados:

- `text`
- `image`
- `document`
- `audio`

Para `image`, `document` e `audio`, o parser preenche:

- `media_id`;
- `message_type`;
- `attachment_url=whatsapp://media/<media_id>`.

O `ConversationService` mantem `attachment_url` em `messages` por compatibilidade e cria tambem um registro do modelo `Attachment` em `attachments` com `provider`, `provider_media_id`, `file_type`, `file_url`, `message_id` e `conversation_id`.

## 9. Erro de envio

O envio usa:

```text
POST https://graph.facebook.com/{version}/{phone_number_id}/messages
```

Se `send_text_message` retornar `status="error"` ou `status="skipped"`, o webhook incrementa `send_errors` e registra log seguro, sem token, payload bruto ou telefone completo.

## 10. Seguranca

Em `APP_ENV=production`:

- `WHATSAPP_APP_SECRET` e obrigatorio;
- `X-Hub-Signature-256` e obrigatorio;
- assinatura ausente retorna `403`;
- assinatura invalida retorna `403`.

Em `APP_ENV=development`, a ausencia de `WHATSAPP_APP_SECRET` e permitida para testes locais, com warning em log.

## 11. Janela de 24 horas e templates

Dentro da janela de atendimento de 24 horas iniciada pelo cliente, a empresa pode responder livremente. Fora dessa janela, mensagens iniciadas pela empresa exigem templates aprovados no WhatsApp Manager.

## 12. Checklist de producao

Checklist de ativação real:

- [ ] Criar app na Meta Developers.
- [ ] Adicionar produto WhatsApp.
- [ ] Copiar `Phone Number ID`.
- [ ] Gerar `WHATSAPP_ACCESS_TOKEN`.
- [ ] Configurar `WHATSAPP_APP_SECRET`.
- [ ] Definir `WHATSAPP_VERIFY_TOKEN`.
- [ ] Subir backend local.
- [ ] Expor backend com ngrok.
- [ ] Configurar webhook na Meta.
- [ ] Assinar eventos de `messages`.
- [ ] Enviar mensagem de teste.
- [ ] Confirmar criação de `WebhookEvent`.
- [ ] Confirmar resposta automática do bot.
- [ ] Confirmar registro da conversa no painel.

- Rodar `alembic upgrade head`.
- Rodar `python -m unittest discover tests`.
- Usar HTTPS.
- Configurar `APP_ENV=production`.
- Configurar `WHATSAPP_APP_SECRET`.
- Configurar `WHATSAPP_ACCESS_TOKEN`.
- Configurar `WHATSAPP_PHONE_NUMBER_ID`.
- Configurar `WHATSAPP_BUSINESS_ACCOUNT_ID`.
- Restringir CORS.
- Trocar credenciais padrao.
- Ativar logs estruturados sem dados sensiveis.
- Configurar backup do PostgreSQL.
- Monitorar `send_errors`, duplicidades e eventos com `processed=false`.
- Planejar fila/worker para alto volume.
