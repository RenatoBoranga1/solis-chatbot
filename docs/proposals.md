# Propostas comerciais

A area `Propostas` transforma leads captados pelo Solis em rascunhos comerciais revisaveis pela equipe da Solar Solucoes.

## Fluxo principal

1. O cliente passa pelo atendimento do chatbot.
2. O Solis cria um lead de orcamento.
3. No painel, a equipe clica em `Gerar proposta` na tela de Leads.
4. O backend cria uma proposta com status `draft`.
5. Se houver leitura confirmada da conta de energia, o consumo medio extraido alimenta kWh/kWp e selecao de kit.
6. Se houver tabela de precos ativa, os itens configurados sao carregados.
7. Se nao houver tabela, os itens padrao entram com valores zerados.
8. A equipe revisa dados tecnicos, itens, valores, desconto, validade e condicoes.
9. A equipe gera o PDF premium.
10. A equipe escolhe o canal de envio: manual, WhatsApp, e-mail ou link seguro.
11. O sistema gera um token seguro para a pagina `/proposta/{token}`.
12. O cliente visualiza, baixa o PDF e registra interesse, aceite, recusa, pedido de ajuste ou pedido de consultor.
13. A equipe acompanha a linha do tempo e os follow-ups comerciais no painel.

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
POST /proposals/{proposal_id}/share-link
GET /proposals/{proposal_id}/share-links
PATCH /proposals/share-links/{link_id}/revoke
GET /proposals/followups
POST /proposals/{proposal_id}/followups
PATCH /proposals/followups/{followup_id}/complete
PATCH /proposals/followups/{followup_id}/cancel

GET /public/proposals/{token}
POST /public/proposals/{token}/responses
GET /public/proposals/{token}/pdf

GET /company-settings
PUT /company-settings

GET /proposal-price-items
POST /proposal-price-items
PUT /proposal-price-items/{id}
PATCH /proposal-price-items/{id}/active
DELETE /proposal-price-items/{id}

GET /proposal-kits
POST /proposal-kits
POST /proposal-kits/simulate
GET /proposal-kits/{kit_id}
PUT /proposal-kits/{kit_id}
PATCH /proposal-kits/{kit_id}/active
DELETE /proposal-kits/{kit_id}
POST /proposal-kits/{kit_id}/items
PUT /proposal-kits/{kit_id}/items/{item_id}
DELETE /proposal-kits/{kit_id}/items/{item_id}

GET /energy-bills
POST /energy-bills/{extraction_id}/apply-to-lead/{lead_id}
POST /energy-bills/{extraction_id}/generate-proposal
```

Visualizacao e permitida para perfis internos. Criacao, edicao, PDF, envio, follow-ups, links seguros, configuracoes comerciais e gestao da tabela de precos sao restritos a `admin`, `comercial` e `gestor`. Kits podem ser visualizados por `admin`, `comercial`, `gestor`, `suporte` e `tecnico`; gestao de kits fica restrita a `admin`, `comercial` e `gestor`. As rotas `/public/proposals/{token}` sao publicas, mas exigem token valido, nao revogado e nao expirado.

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

## Kits fotovoltaicos configuraveis

A tabela `proposal_kits` permite cadastrar kits comerciais por faixa de consumo e potencia:

- nome e descricao;
- consumo minimo/maximo em kWh/mes;
- potencia minima/maxima em kWp;
- potencia sugerida;
- geracao mensal estimada;
- quantidade de modulos e potencia por modulo;
- potencia do inversor;
- preco base;
- status ativo/inativo;
- ordem e observacoes.

A tabela `proposal_kit_items` permite detalhar os itens de cada kit. Se um kit nao tiver itens, o sistema cria um item unico `Kit fotovoltaico recomendado` usando o `base_price`.

Ao gerar proposta por lead, a selecao automatica segue esta ordem:

1. kit ativo cuja faixa de potencia contem a potencia estimada;
2. kit ativo cuja faixa de consumo/geracao contem a geracao estimada;
3. kit ativo imediatamente acima da potencia estimada;
4. maior kit ativo;
5. fallback para tabela de precos ou itens padrao zerados.

Campos gravados na proposta:

- `recommended_kit_id`;
- `recommended_kit_name`;
- `kit_selection_reason`.

Exemplo com R$ 350,00 de conta media:

- geracao estimada aproximada: 313 kWh/mes;
- potencia estimada aproximada: 2,32 kWp;
- se houver kit ativo compativel, ele sera exibido como recomendado.

A proposta continua `draft`. O kit e uma recomendacao, nao um dimensionamento definitivo. Revise telhado, sombreamento, padrao de entrada, concessionaria, estrutura, valores e condicoes antes de enviar.

Quando houver `average_consumption_kwh` vindo do Leitor Inteligente de Conta de Energia, esse consumo medio tem prioridade sobre a estimativa por valor em reais. A prioridade de pre-dimensionamento passa a ser:

1. media extraida do historico mensal da conta (`average_source=history_12_months` ou `history_partial`);
2. consumo atual da fatura quando o historico nao foi identificado (`current_consumption_only`);
3. valor medio da conta informado no lead;
4. valor atual da fatura, quando for o unico dado confiavel.

As notas internas da proposta indicam quando o consumo veio do historico da conta e quantos meses foram detectados. Isso melhora a escolha de kit, mas continua exigindo revisao humana, validacao tecnica e analise comercial antes do envio.

Guia completo: [`proposal-kits.md`](proposal-kits.md).

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
- kit fotovoltaico recomendado, quando houver;
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

## Configuracoes comerciais

A tabela `company_settings` centraliza dados usados em propostas e PDFs:

- nome, telefone, e-mail, site e endereco da empresa;
- URL de logotipo;
- cores principal e secundaria;
- validade padrao da proposta;
- condicoes de pagamento padrao;
- observacoes comerciais padrao.

Esses dados podem ser editados no painel pela aba `Configuracoes comerciais`, para perfis `admin` e `gestor`. Se ainda nao existir registro salvo, o backend cria um fallback usando as variaveis `COMPANY_NAME`, `COMPANY_PHONE`, `COMPANY_EMAIL`, `COMPANY_WEBSITE`, `COMPANY_ADDRESS`, `COMPANY_LOGO_PATH`, `COMPANY_PRIMARY_COLOR` e `COMPANY_SECONDARY_COLOR`.

Em producao, configure `FRONTEND_ORIGINS` com o dominio publico do frontend. O link de proposta usa o primeiro dominio configurado para gerar `/proposta/{token}`.

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
- `whatsapp`: gera link seguro, simula em `development`; em `production`, usa `WhatsAppCloudService`.
- `email`: gera link seguro, simula em `development`; em `production`, usa SMTP.
- `secure_link`: gera ou reaproveita um link seguro ativo para compartilhamento humano.

O sistema nunca envia caminho local do PDF ao cliente. WhatsApp, e-mail e link seguro usam a pagina publica `/proposta/{token}`. O download do PDF passa por `GET /public/proposals/{token}/pdf`, que valida token, expiracao e revogacao antes de servir o arquivo.

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

## Link seguro e pagina publica

Cada link seguro fica em `proposal_share_links` com:

- token aleatorio;
- data de expiracao;
- data de revogacao;
- quantidade de visualizacoes;
- ultima visualizacao;
- usuario que criou o link.

Endpoints:

```text
POST /proposals/{proposal_id}/share-link
GET /proposals/{proposal_id}/share-links
PATCH /proposals/share-links/{link_id}/revoke
GET /public/proposals/{token}
GET /public/proposals/{token}/pdf
```

A pagina publica do frontend fica em:

```text
https://seu-dominio.com/proposta/{token}
```

Ela mostra resumo da proposta, dados principais, itens, condicoes, total, download do PDF e botoes de resposta do cliente. Token expirado, revogado ou inexistente retorna mensagem de indisponibilidade.

## Resposta digital do cliente

O endpoint publico:

```text
POST /public/proposals/{token}/responses
```

Aceita:

- `interested`;
- `accepted`;
- `rejected`;
- `request_changes`;
- `talk_to_consultant`.

As respostas ficam em `proposal_customer_responses`. Quando o cliente aceita, a proposta passa para `accepted`. Quando recusa, passa para `rejected`. Quando solicita ajuste e a proposta estava enviada, volta para `under_review`. Cada resposta tambem gera evento em `proposal_events` e auditoria interna.

## Follow-ups comerciais

A tabela `proposal_followups` organiza retornos comerciais apos envio da proposta:

- canal (`manual`, `whatsapp`, `email`, `phone`);
- vencimento;
- status (`pending`, `completed`, `canceled`);
- observacao;
- responsavel;
- data de conclusao.

Endpoints:

```text
GET /proposals/followups
POST /proposals/{proposal_id}/followups
PATCH /proposals/followups/{followup_id}/complete
PATCH /proposals/followups/{followup_id}/cancel
```

Quando uma proposta e marcada como enviada ou simulada por WhatsApp/e-mail, o sistema cria retornos padrao de 24 horas e 3 dias, sem duplicar follow-ups pendentes do mesmo canal.

## Linha do tempo

Eventos comerciais sao registrados em `proposal_events` e aparecem no detalhe da proposta:

- proposta criada ou atualizada;
- PDF gerado;
- link seguro criado, visto ou revogado;
- proposta baixada;
- proposta enviada;
- resposta digital do cliente;
- follow-up criado, concluido ou cancelado.

Esses eventos ajudam auditoria, gestao comercial e rastreabilidade sem depender apenas de logs tecnicos.

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
- `proposal.share_link_created`;
- `proposal.share_link_revoked`;
- `proposal.customer_interested`;
- `proposal.accepted`;
- `proposal.rejected`;
- `proposal.change_requested`;
- `proposal.followup_created`;
- `proposal_price_item.created`;
- `proposal_price_item.updated`;
- `proposal_price_item.active_changed`;
- `proposal_price_item.deleted`.
- `proposal_kit.created`;
- `proposal_kit.updated`;
- `proposal_kit.active_changed`;
- `proposal_kit.deleted`;
- `proposal_kit.item_created`;
- `proposal_kit.item_updated`;
- `proposal_kit.item_deleted`.

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
