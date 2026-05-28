# WhatsApp Cloud API

Este guia mostra como conectar o Solis à WhatsApp Business Platform / Cloud API oficial da Meta.

## 1. Criar app na Meta

1. Acesse [Meta for Developers](https://developers.facebook.com/).
2. Crie um app do tipo Business.
3. Vincule ou crie um Business Manager.
4. Adicione o produto WhatsApp ao app.

## 2. Configurar número

1. No produto WhatsApp, configure um número de telefone.
2. Copie o `Phone Number ID`.
3. Copie o `WhatsApp Business Account ID`.
4. Gere um access token com permissão para enviar mensagens.

## 3. Configurar variáveis

No ambiente do backend:

```env
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_BUSINESS_ACCOUNT_ID=
WHATSAPP_VERIFY_TOKEN=solis_verify_token_dev
WHATSAPP_APP_SECRET=
WHATSAPP_API_VERSION=v20.0
```

Em produção, configure também:

```env
APP_ENV=production
WHATSAPP_APP_SECRET=<app-secret-da-meta>
```

Com `APP_ENV=production`, a assinatura `X-Hub-Signature-256` é obrigatória.

## 4. Configurar webhook

No painel da Meta, configure:

```text
https://seu-dominio.com/webhook/whatsapp
```

Use o mesmo valor de `WHATSAPP_VERIFY_TOKEN` no campo Verify Token.

Assine o campo:

```text
messages
```

O Solis implementa:

- `GET /webhook/whatsapp` para validação inicial da Meta.
- `POST /webhook/whatsapp` para receber mensagens.

## 5. Testar localmente com ngrok

Suba a API:

```bash
cd backend
uvicorn app.main:app --reload
```

Exponha localmente:

```bash
ngrok http 8000
```

Configure no painel da Meta:

```text
https://<subdominio-ngrok>/webhook/whatsapp
```

## 6. Fluxo de recebimento

Quando o cliente envia uma mensagem:

1. A Meta chama `POST /webhook/whatsapp`.
2. O backend valida a assinatura quando configurada.
3. O payload oficial é convertido para `WhatsAppIncomingMessage`.
4. Mensagens duplicadas são ignoradas por `provider=whatsapp` e `provider_message_id`.
5. O backend monta um `ChatMessageIn`.
6. O `ConversationService` classifica intenção, gravidade, lead, ticket e handoff.
7. O `WhatsAppCloudService` envia a resposta para a Cloud API.

## 7. Tipos suportados

Nesta etapa, o Solis processa:

- `text`
- `image`
- `document`
- `audio`

Para anexos, o webhook registra uma mensagem como:

```text
Cliente enviou um anexo do tipo image
```

O `media_id` é preservado como `whatsapp://media/<media_id>` em `attachment_url` quando disponível.

## 8. Envio de mensagens

Endpoint oficial usado:

```text
POST https://graph.facebook.com/{version}/{phone_number_id}/messages
```

Payload:

```json
{
  "messaging_product": "whatsapp",
  "to": "5511999999999",
  "type": "text",
  "text": {
    "preview_url": false,
    "body": "Mensagem do Solis"
  }
}
```

## 9. Janela de 24 horas

Quando o cliente inicia a conversa, a empresa pode responder livremente dentro da janela de atendimento de 24 horas.

Fora da janela de 24 horas, mensagens iniciadas pela empresa exigem templates aprovados pela Meta.

## 10. Templates

Use templates para:

- retorno de orçamento;
- lembrete de visita técnica;
- atualização de chamado;
- confirmação de agendamento;
- retomada de conversa fora da janela de 24 horas.

Templates devem ser cadastrados e aprovados no WhatsApp Manager antes do uso.

## 11. Segurança

- Nunca versionar tokens reais.
- Usar HTTPS em produção.
- Configurar `WHATSAPP_APP_SECRET`.
- Validar `X-Hub-Signature-256`.
- Não registrar conteúdo sensível em logs.
- Usar permissões mínimas no token da Meta.
