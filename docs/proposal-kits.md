# Kits fotovoltaicos configuraveis

Este modulo permite que a Solar Solucoes cadastre kits comerciais e use esses kits para gerar pre-propostas a partir de leads captados pelo Solis.

## Objetivo

O sistema sugere um kit quando ha dados suficientes, mas nunca transforma essa sugestao em preco final ou dimensionamento definitivo. Toda proposta gerada automaticamente continua como `draft` e precisa de revisao humana.

## Como cadastrar um kit

No painel, acesse `Propostas` e abra a aba `Kits fotovoltaicos`.

Campos principais:

- nome do kit, por exemplo `Kit Solar 2,75 kWp`;
- descricao;
- faixa de consumo em kWh/mes;
- faixa de potencia em kWp;
- potencia sugerida;
- geracao mensal estimada;
- quantidade de modulos;
- potencia do modulo em Wp;
- potencia do inversor em kW;
- preco base;
- observacoes;
- status ativo/inativo;
- ordem.

Use `base_price=0` enquanto os valores reais nao tiverem sido revisados pela equipe comercial.

## Itens do kit

Cada kit pode ter itens detalhados:

- modulos solares;
- inversor;
- estrutura;
- cabos;
- string box;
- mao de obra;
- projeto;
- homologacao;
- deslocamento;
- monitoramento.

Se o kit tiver itens, a proposta gerada copia esses itens para `proposal_items`. Se nao tiver itens, o sistema cria um item unico com a descricao do kit e o `base_price`.

## Como a selecao automatica funciona

Quando a equipe clica em `Gerar proposta` a partir de um lead:

1. Se o lead tiver `average_consumption_kwh` extraido da conta de energia, o backend usa esse consumo como referencia principal.
2. Se nao houver consumo extraido, o backend estima geracao mensal e potencia a partir da conta media em reais.
3. O `ProposalKitService` busca kits ativos.
4. Primeiro tenta encontrar kit por faixa de potencia.
5. Se nao encontrar, tenta por faixa de consumo/geracao.
6. Se nao encontrar, escolhe o kit imediatamente acima.
7. Se ainda nao houver, escolhe o maior kit ativo.
8. Se nao houver kits, usa a tabela de precos atual.
9. Se nao houver tabela, cria itens padrao zerados.

Exemplo:

```text
Conta media: R$ 350,00
Geracao estimada: aproximadamente 313 kWh/mes
Potencia estimada: aproximadamente 2,32 kWp
Kit recomendado: Kit Solar 2,75 kWp, se houver faixa compativel ativa
```

## Simulador

Use `POST /proposal-kits/simulate` ou o simulador do painel:

```json
{
  "average_bill": 350,
  "estimated_monthly_generation_kwh": null,
  "estimated_power_kwp": null
}
```

Retorno esperado:

```json
{
  "average_bill": 350,
  "estimated_monthly_generation_kwh": 313.16,
  "estimated_power_kwp": 2.32,
  "selected_kit": {
    "name": "Kit Solar 2,75 kWp"
  },
  "selection_reason": "Kit escolhido por faixa de geracao/consumo mensal."
}
```

A simulacao nao grava dados reais nem altera propostas.

Para simular por consumo extraido:

```json
{
  "average_bill": 512.34,
  "estimated_monthly_generation_kwh": 429,
  "estimated_power_kwp": 3.178
}
```

Esse e o mesmo caminho usado quando uma conta de energia confirmada e aplicada ao lead.

## Proposta e PDF

Quando ha kit recomendado, a proposta grava:

- `recommended_kit_id`;
- `recommended_kit_name`;
- `kit_selection_reason`.

A tela da proposta e o PDF exibem:

- nome do kit;
- potencia sugerida;
- quantidade e potencia dos modulos;
- inversor;
- geracao mensal estimada;
- motivo da selecao;
- aviso de revisao tecnica e comercial.

## Regras comerciais obrigatorias

- A proposta automatica fica como `draft`.
- O kit e recomendado, nao definitivo.
- O sistema nao envia proposta automaticamente.
- O sistema nao promete economia exata.
- O sistema nao promete geracao exata.
- O sistema nao promete prazo de instalacao.
- O sistema nao promete homologacao automatica.
- Valores, itens e condicoes devem ser revisados antes do envio.

## Permissoes

Visualizacao:

- `admin`;
- `comercial`;
- `gestor`;
- `suporte`;
- `tecnico`.

Gestao:

- `admin`;
- `comercial`;
- `gestor`.

## Endpoints

```text
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
```

## Homologacao

Antes de vender a solucao:

- cadastrar kits reais da Solar Solucoes;
- revisar faixas de consumo e potencia;
- preencher equipamentos corretos;
- validar precos;
- gerar proposta de teste a partir de lead;
- conferir itemizacao da proposta;
- gerar PDF;
- validar link seguro;
- simular envio por WhatsApp/e-mail;
- confirmar que a proposta fica em rascunho.
