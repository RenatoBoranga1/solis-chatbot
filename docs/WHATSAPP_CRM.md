# Integracao WhatsApp e CRM

## Contrato interno de mensagem

Todos os canais devem ser convertidos para:

```json
{
  "channel": "whatsapp",
  "external_id": "5511999999999",
  "message": "Quero um orçamento",
  "attachment_url": "https://provedor.com/anexo.jpg"
}
```

## Adaptador WhatsApp

Responsabilidades:

- validar origem do webhook;
- normalizar telefone;
- baixar ou apontar anexos;
- chamar `POST /chat/message`;
- enviar resposta para o provedor;
- registrar falhas de entrega.

## CRM

Eventos recomendados para sincronizacao:

- lead criado;
- lead atualizado;
- chamado criado;
- handoff solicitado;
- conversa assumida por humano;
- atendimento resolvido;
- feedback recebido.

O backend ja separa `Lead`, `Ticket`, `Conversation` e `Handoff`, facilitando webhooks ou jobs de sincronizacao com HubSpot, Pipedrive, RD Station, Kommo, Salesforce ou CRM proprio.
