# Propostas comerciais

A area `Propostas` transforma leads captados pelo Solis em rascunhos comerciais revisaveis pela equipe da Solar Solucoes.

## Fluxo principal

1. O cliente passa pelo atendimento do chatbot.
2. O Solis cria um lead de orcamento.
3. No painel, a equipe clica em `Gerar proposta` na tela de Leads.
4. O backend cria uma proposta com status `draft`.
5. Se houver tabela de precos ativa, os itens configurados sao carregados.
6. Se nao houver tabela, os itens padrao entram com valores zerados.
7. A equipe revisa dados tecnicos, itens, valores, desconto, validade e condicoes.
8. A equipe gera o PDF premium.
9. A equipe escolhe o canal de envio: manual, WhatsApp, e-mail ou link seguro.

## Endpoints

```text
GET /proposals
POST /proposals
POST /proposals/from-lead/{lead_id}
GET /proposals/{proposal_id}
PUT /proposals/{proposal_id}
PATCH /proposals/{proposal_id}/status
POST /proposals/{proposal_id}/items
PUT /proposals/{proposal_id}/items/{item_id}
DELETE /proposals/{proposal_id}/items/{item_id}
POST /proposals/{proposal_id}/generate-pdf
POST /proposals/{proposal_id}/apply-price-table
POST /proposals/{proposal_id}/send

GET /proposal-price-items
POST /proposal-price-items
PUT /proposal-price-items/{id}
PATCH /proposal-price-items/{id}/active
DELETE /proposal-price-items/{id}
```

Visualizacao e permitida para perfis internos. Criacao, edicao, PDF, envio e gestao da tabela de precos sao restritos a `admin`, `comercial` e `gestor`.

## Status

- `draft`: rascunho.
- `under_review`: em revisao.
- `approved`: aprovada internamente.
- `ready_to_send`: PDF gerado e proposta pronta para escolha do canal de envio.
- `sent`: enviada.
- `accepted`: aceita pelo cliente.
- `rejected`: rejeitada.
- `expired`: expirada.
- `canceled`: cancelada.

## Tabela de precos

A tabela `proposal_price_items` permite configurar itens comerciais reutilizaveis:

- categoria;
- descricao;
- unidade padrao;
- quantidade padrao;
- valor unitario padrao;
- status ativo/inativo;
- ordem de exibicao;
- observacoes internas.

Categorias recomendadas:

- `kit_fotovoltaico`;
- `materiais_eletricos`;
- `mao_de_obra`;
- `projeto`;
- `homologacao`;
- `taxas_concessionaria`;
- `estrutura_fixacao`;
- `deslocamento`;
- `monitoramento`;
- `outros`.

Propostas geradas a partir de lead usam somente itens ativos. A tabela ajuda a reduzir retrabalho, mas nao substitui revisao humana. O bot e a IA nao devem definir preco final.

## Aplicar tabela em proposta existente

Use:

```text
POST /proposals/{proposal_id}/apply-price-table
```

O endpoint remove os itens atuais da proposta, aplica os itens ativos da tabela, recalcula subtotal/total e registra auditoria `proposal.price_table_applied`.

## PDF premium

O `ProposalPdfService` gera um PDF com:

- cabecalho visual com nome da empresa, numero, emissao, validade e status;
- dados do cliente;
- resumo da solucao;
- potencia estimada, geracao mensal estimada e economia estimada;
- tabela de itens com categoria, descricao, quantidade, unidade, valor unitario e total;
- resumo financeiro;
- condicoes de pagamento;
- observacoes comerciais e tecnicas;
- rodape institucional.

Variaveis usadas:

```env
PROPOSAL_STORAGE_PATH=storage/proposals
COMPANY_NAME=Solar Solucoes
COMPANY_PHONE=
COMPANY_EMAIL=
COMPANY_WEBSITE=https://solarsolucoes.com.br
COMPANY_ADDRESS=
COMPANY_LOGO_PATH=
COMPANY_PRIMARY_COLOR=#FFCC33
COMPANY_SECONDARY_COLOR=#0B1F33
```

O PDF continua sendo salvo em `PROPOSAL_STORAGE_PATH`. Em producao, recomenda-se storage privado com URL temporaria.

## Envio da proposta

Endpoint:

```text
POST /proposals/{proposal_id}/send
```

Payload:

```json
{
  "channel": "manual",
  "recipient_phone": "5511999999999",
  "recipient_email": "cliente@example.com",
  "message": "Mensagem opcional",
  "use_template": false,
  "template_name": null,
  "mark_as_sent": false
}
```

Canais:

- `manual`: gera o PDF e deixa pronto para envio humano. Nao marca como `sent`, salvo com `mark_as_sent=true`.
- `whatsapp`: simula em `development`; em `production`, usa `WhatsAppCloudService`.
- `email`: simula em `development`; em `production`, usa SMTP.
- `secure_link`: retorna uma URL publica segura quando `PROPOSAL_PUBLIC_BASE_URL` estiver configurado.

Para WhatsApp ou link seguro, configure:

```env
PROPOSAL_PUBLIC_BASE_URL=https://seu-dominio-seguro.com/proposals
```

Sem essa URL, o sistema nao envia caminho local do PDF para o cliente.

Para e-mail em producao:

```env
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_FROM_NAME=Solar Solucoes
SMTP_USE_TLS=true
```

Mensagens ativas no WhatsApp fora da janela de 24 horas exigem template aprovado pela Meta.

## Auditoria

Acoes registradas em `audit_logs`:

- `proposal.created`;
- `proposal.updated`;
- `proposal.status_changed`;
- `proposal.pdf_generated`;
- `proposal.price_table_applied`;
- `proposal.send_requested`;
- `proposal.sent`;
- `proposal.send_failed`;
- `proposal.email_sent`;
- `proposal.whatsapp_sent`;
- `proposal.secure_link_generated`;
- `proposal_price_item.created`;
- `proposal_price_item.updated`;
- `proposal_price_item.active_changed`;
- `proposal_price_item.deleted`.

## Cuidados comerciais

- Nao transformar estimativas em promessa de economia exata.
- Nao prometer prazo sem validacao tecnica e comercial.
- Nao considerar preco final sem revisao humana.
- Homologacao depende da concessionaria.
- Nao expor PDFs com dados pessoais em diretorio publico sem protecao.
- Revisar todos os valores antes de enviar ao cliente.

## Testes

```bash
cd backend
python -m unittest tests.test_proposals
python -m unittest discover tests
```
