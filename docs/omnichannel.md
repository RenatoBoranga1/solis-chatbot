# Continuidade omnichannel site -> WhatsApp

Esta etapa permite que um atendimento iniciado no widget do site continue no WhatsApp oficial da Solar Soluções sem perder o contexto coletado pelo Solis.

## Fluxo

1. Cliente inicia conversa no widget do site.
2. Solis coleta dados e classifica intenção, gravidade, lead ou chamado.
3. No painel, a equipe clica em `WhatsApp` na conversa qualificada.
4. O backend cria um registro em `conversation_channel_links`.
5. Em desenvolvimento, o convite pode ser simulado. Em produção, deve ser enviado por template aprovado pela Meta.
6. O cliente responde `SIM`, `ok`, `confirmo` ou equivalente no WhatsApp.
7. O webhook identifica o telefone, confirma o vínculo e cria a conversa no canal `whatsapp`.
8. A conversa WhatsApp herda `collected_data`, `summary`, `intent` e `severity` da conversa do site.

## Modelo

Tabela: `conversation_channel_links`

- `customer_id`: cliente do atendimento.
- `source_conversation_id`: conversa original do site.
- `target_conversation_id`: conversa WhatsApp criada após confirmação.
- `source_channel`: normalmente `site`.
- `target_channel`: normalmente `whatsapp`.
- `external_id`: identificador externo, geralmente telefone.
- `phone`: telefone normalizado, somente dígitos.
- `lead_id`: lead vinculado, quando houver.
- `ticket_id`: chamado vinculado, quando houver.
- `status`: `pending`, `invited`, `confirmed`, `expired` ou `failed`.
- `confirmed_at`: data de confirmação pelo WhatsApp.

## Endpoint

```text
POST /chat/conversations/{conversation_id}/continue-whatsapp
```

Payload opcional:

```json
{
  "template_name": "continuar_atendimento_site",
  "custom_message": "Mensagem revisada pela equipe",
  "review_confirmed": false
}
```

Resposta:

```json
{
  "status": "simulated",
  "conversation_channel_link_id": "...",
  "phone": "5511999998888",
  "message": "Olá...",
  "target_conversation_id": null
}
```

## Segurança operacional

- Casos com `severity=alta` exigem revisão humana antes do convite.
- Em produção, mensagens iniciadas pela empresa devem usar template aprovado pela Meta.
- O telefone é normalizado para reduzir duplicidade entre site e WhatsApp.
- O webhook só confirma a migração quando a resposta do cliente for afirmativa.
- O contexto preservado inclui a origem em `collected_data.migrated_from_channel` e `collected_data.source_conversation_id`.

## Testes manuais

1. Criar conversa pelo widget e informar telefone.
2. Completar um fluxo até `commercial_triage` ou `technical_triage`.
3. No painel, clicar em `WhatsApp`.
4. Em desenvolvimento, confirmar status simulado e badge `WhatsApp enviado`.
5. Enviar `SIM` pelo webhook WhatsApp com o mesmo telefone.
6. Confirmar que o link vira `confirmed`.
7. Confirmar que a conversa WhatsApp mantém dados coletados no site.
