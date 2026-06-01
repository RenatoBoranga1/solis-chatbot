# Propostas comerciais

A área `Propostas` transforma leads captados pelo Solis em rascunhos comerciais revisáveis pela equipe da Solar Soluções.

## Fluxo principal

1. O cliente passa pelo atendimento do chatbot.
2. O Solis cria um lead de orçamento.
3. No painel, a equipe clica em `Gerar proposta` na tela de Leads.
4. O backend cria uma proposta com status `draft`.
5. A equipe revisa dados técnicos, itens, valores, desconto e condições.
6. A equipe gera o PDF.
7. Em desenvolvimento, o envio é simulado. Em produção, o envio pode ser integrado com WhatsApp, e-mail ou download manual.

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
POST /proposals/{proposal_id}/send
```

Visualização é permitida para perfis internos. Criação, edição, PDF e envio são restritos a `admin`, `comercial` e `gestor`.

## Status

- `draft`: rascunho.
- `under_review`: em revisão.
- `approved`: aprovada internamente.
- `sent`: enviada.
- `accepted`: aceita pelo cliente.
- `rejected`: rejeitada.
- `expired`: expirada.
- `canceled`: cancelada.

## Itens

Itens iniciais criados a partir de lead:

- kit fotovoltaico;
- materiais elétricos;
- mão de obra especializada;
- projeto técnico;
- homologação;
- estrutura de fixação;
- taxas e adequações.

Todos começam editáveis e com valor zero, para evitar preço definitivo sem revisão humana.

## Cálculos

```text
total_price = quantity * unit_price
subtotal = soma dos itens
total_amount = subtotal - discount
```

O sistema recalcula a proposta ao editar itens ou desconto.

## PDF

O serviço `ProposalPdfService` gera um PDF simples e profissional em:

```text
storage/proposals/
```

Configure outro caminho com:

```env
PROPOSAL_STORAGE_PATH=storage/proposals
```

Em produção, recomenda-se armazenar PDFs em S3, Cloudflare R2 ou storage privado com URL temporária. Não publique PDFs com dados pessoais em pasta pública sem controle de acesso.

## WhatsApp e envio

O endpoint `/proposals/{proposal_id}/send` simula envio em desenvolvimento e marca a proposta como `sent`.

Para produção:

- dentro da janela de 24 horas iniciada pelo cliente, pode-se enviar link ou PDF conforme política da Meta;
- fora da janela, usar template aprovado;
- registrar o canal de envio e manter auditoria.

## Cuidados comerciais

A proposta gerada pelo Solis é rascunho. A equipe deve revisar:

- potência estimada;
- geração estimada;
- condições do telhado ou local;
- concessionária e homologação;
- valores de kit, materiais e mão de obra;
- desconto;
- prazo, validade e condições de pagamento.

O PDF não deve prometer economia exata, preço final, garantia ou prazo sem validação técnica e comercial.
