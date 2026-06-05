# Leitor Inteligente de Conta de Energia

Este modulo transforma contas de energia em dados estruturados para orcamento fotovoltaico, revisao comercial e geracao de proposta em rascunho.

## Objetivo

Reduzir digitacao manual e melhorar a precisao do pre-dimensionamento. O sistema extrai dados, calcula medias e sugere estimativas, mas nao substitui analise tecnica, validacao comercial ou vistoria.

## Fluxo

1. Cliente envia conta pelo widget, WhatsApp ou equipe faz upload no painel.
2. O anexo fica registrado em `attachments`.
3. Se o atendimento estiver em contexto de orcamento e houver consentimento LGPD, o `ConversationService` cria automaticamente uma extracao em `energy_bill_extractions`.
4. A extracao recebe uma origem: `chatbot`, `whatsapp`, `panel`, `manual_text` ou `api`.
5. Para arquivos locais do widget/painel, o processamento e agendado em background e o chat continua rapido.
6. O parser tenta extrair texto direto. Se o arquivo for imagem ou PDF escaneado e OCR estiver habilitado, usa OCR local.
7. O sistema calcula media de consumo, potencia estimada e economia estimada.
8. Se a confianca for baixa, o status fica `needs_review`.
9. Um humano revisa e confirma.
10. A extracao confirmada pode ser aplicada ao lead.
11. A proposta gerada usa consumo medio extraido para escolher o kit fotovoltaico.

## Tabelas

`energy_bill_extractions` guarda:

- vinculos com conversa, cliente, lead e anexo;
- status da leitura;
- `source`, que indica o provedor tecnico do anexo;
- `origin`, que indica a entrada de negocio (`chatbot`, `whatsapp`, `panel`, `manual_text` ou `api`);
- distribuidora, unidade consumidora, cidade/UF, referencia e vencimento;
- nome do titular, endereco, bairro, CEP, unidade/codigo do cliente e bandeira tarifaria;
- consumo atual, valor atual, medias e estimativas;
- score de confianca;
- campos faltantes;
- `raw_text_excerpt` mascarado;
- auditoria de confirmacao.

`energy_bill_consumption_history` guarda o historico mensal extraido:

- periodo;
- consumo em kWh;
- valor, quando disponivel.

## Status

- `pending`: criado, ainda sem processamento.
- `processing`: criado automaticamente a partir de anexo e aguardando leitura em background.
- `extracted`: leitura com confianca suficiente.
- `needs_review`: leitura util, mas exige revisao humana.
- `confirmed`: revisado e aprovado por usuario interno.
- `failed`: nao foi possivel extrair texto ou dados minimos.
- `discarded`: descartado pela equipe.

## Configuracao

```env
ENERGY_BILL_EXTRACTION_ENABLED=true
ENERGY_BILL_OCR_ENABLED=false
ENERGY_BILL_OCR_PROVIDER=disabled
ENERGY_BILL_OCR_MAX_PAGES=3
ENERGY_BILL_MIN_TEXT_LENGTH=80
ENERGY_BILL_ALLOW_EXTERNAL_AI=false
ENERGY_BILL_MAX_FILE_SIZE_MB=10
ENERGY_BILL_STORE_RAW_TEXT=false
ENERGY_BILL_MIN_CONFIDENCE_AUTO_APPLY=0.85
ENERGY_BILL_STORAGE_PATH=storage/energy_bills
CHAT_ATTACHMENT_STORAGE_PATH=storage/chat_attachments
```

Recomendacao inicial: manter OCR e IA externa desligados ate homologar o fluxo com contas reais e politica LGPD revisada.

Para OCR local:

```env
ENERGY_BILL_OCR_ENABLED=true
ENERGY_BILL_OCR_PROVIDER=local_tesseract
```

OCR externo/visao por IA fica apenas preparado. So use `ENERGY_BILL_OCR_PROVIDER=openai_vision` com `ENERGY_BILL_ALLOW_EXTERNAL_AI=true`, contrato/base legal revisados e chave configurada. Por padrao, nenhuma imagem e enviada para servico externo.

## Endpoints

```text
GET /energy-bills
GET /energy-bills/{extraction_id}
POST /energy-bills/extract
POST /energy-bills/extract-from-attachment/{attachment_id}
PUT /energy-bills/{extraction_id}
POST /energy-bills/{extraction_id}/confirm
POST /energy-bills/{extraction_id}/apply-to-lead/{lead_id}
POST /energy-bills/{extraction_id}/generate-proposal
POST /energy-bills/{extraction_id}/discard
POST /energy-bills/parse-text
POST /chat/attachments
```

Visualizacao: `admin`, `comercial`, `gestor`, `suporte`, `tecnico`.

Gestao, confirmacao, aplicacao em lead e proposta: `admin`, `comercial`, `gestor`.

## Automacao por chatbot

Quando o cliente envia PDF ou imagem no widget durante o fluxo de orcamento, o frontend primeiro envia o arquivo para `POST /chat/attachments`. A rota valida extensao e tamanho, salva em `CHAT_ATTACHMENT_STORAGE_PATH` e devolve `attachment_url` e `media_type`.

Em seguida, `POST /chat/message` recebe a mensagem do cliente com o anexo salvo. O `ConversationService`:

- registra `Message` e `Attachment`;
- verifica se ha contexto comercial e consentimento LGPD;
- detecta pistas como "conta de energia", "conta de luz", "fatura", "kWh" ou distribuidoras;
- cria `EnergyBillExtraction` com `origin=chatbot` e `status=processing`;
- agenda o processamento em background;
- atualiza `conversation.collected_data` com `bill_file_received`, `energy_bill_extraction_id`, `energy_bill_status` e origem.

Se a leitura terminar com sucesso, `conversation.collected_data` e o lead vinculado recebem consumo, valor, distribuidora, cidade/UF, unidade consumidora, confianca e necessidade de revisao. Se o arquivo for invalido, nao relacionado ou sem consentimento LGPD, a extracao nao e criada automaticamente.

## WhatsApp

Mensagens WhatsApp com `image`, `document` ou `audio` ja geram `Attachment` com `provider_media_id`. Quando o anexo parecer conta de energia em um fluxo comercial, a extracao pode ser criada com `origin=whatsapp`.

Enquanto o download real da midia da Meta nao estiver habilitado, arquivos WhatsApp ficam referenciados como `whatsapp://media/<media_id>` e a leitura automatica e marcada para revisao/falha operacional. O proximo passo de producao e baixar a midia para storage privado antes de processar.

## Parsers

A primeira versao inclui:

- parser generico para textos de contas brasileiras;
- parser CPFL com regras por ancoras textuais e descarte de campos suspeitos.

O parser busca:

- kWh atual;
- valor total;
- historico mensal;
- distribuidora;
- unidade consumidora;
- endereco, bairro, CEP e bloco real do cliente;
- bandeira tarifaria, sem confundir `Verde`/`Amarela`/`Vermelha` com unidade;
- cidade/UF;
- referencia e vencimento;
- CPF/CNPJ mascarado.

Novos parsers podem ser adicionados em `backend/app/services/energy_bill_parsers/`.

### Regras especificas CPFL

Contas CPFL podem trazer no topo um cabecalho da distribuidora com `CPFL Energia`, `DANF3E`, razao social, endereco institucional, CNPJ, inscricao estadual e canais de atendimento. Esses dados nao pertencem ao cliente e nao devem preencher nome, endereco, cidade ou unidade consumidora.

O parser CPFL agora procura o bloco real do cliente pelo padrao:

```text
NOME DO CLIENTE
ENDERECO
BAIRRO
CEP CIDADE UF
```

Exemplo aceito:

```text
RENATO DE OLIVEIRA BORANGA
R ARMANDO CEZARIO CAMPOS 41
CENTRO
18970-000 CHAVANTES SP
```

Esse bloco preenche `customer_name`, `customer_address`, `customer_district`, `customer_postal_code`, `city` e `state`. Linhas com `CPFL`, `DANF`, `Companhia`, `Energia S.A.`, `CNPJ`, `Inscricao Estadual`, `Rua Vigato`, `atendimento`, `ouvidoria`, `agencia` ou `sede` sao descartadas como cabecalho da distribuidora.

O historico CPFL aceita formatos como:

```text
JAN/2026 320 kWh
FEV 340
MAR 2026 360 kWh
01/2026 320 kWh
```

O parser deduplica meses e ignora valores monetarios, tarifas, CNPJ/CPF, CEP e datas de vencimento. Quando o bloco de `Historico de consumo` existe, ele vira a fonte principal da media. Se houver 12 meses ou mais, `parsed_fields.average_source=history_12_months`; com 3 a 11 meses, `history_partial`; sem historico, a media fica limitada ao consumo atual ou nula.

## Precisao e descarte conservador

O leitor segue a regra: e melhor retornar `null` e pedir revisao humana do que preencher campo com chute.

Regras importantes:

- `Verde`, `Amarela`, `Vermelha`, `Bandeira Verde`, `Bandeira Amarela`, `Bandeira Vermelha` e `Escassez hidrica` sao tratados como `tariff_flag`.
- Bandeira tarifaria nunca deve preencher unidade consumidora, instalacao, cidade, endereco ou nome do cliente.
- Linhas com `CPFL`, `CNPJ`, `agencia`, `atendimento`, `posto`, `sede`, `terreo`, `loja`, `ouvidoria`, `demonstrativo` ou `informacoes fiscais` nao sao usadas como cidade/endereco do cliente.
- `R$ 0,00` nao e considerado valor valido, salvo quando houver indicacao clara de fatura zerada.
- Valores de `ICMS`, `PIS/COFINS`, tarifa unitaria, multa, juros, imposto ou iluminacao publica nao sao usados como valor total quando nao ha ancora de total da fatura.
- O valor total prioriza ancoras como `Total a pagar`, `Valor a pagar`, `Total da fatura`, `Valor da conta` e `Vencimento`.
- Consumo atual prioriza contexto `Consumo faturado`, `Consumo medido`, `Consumo kWh` e `Energia ativa`.

O campo `parsed_fields` registra informacoes de auditoria para revisao:

- `parser`;
- `cpfl_rules_applied`;
- `tariff_flag`;
- `customer_unit_number`;
- `customer_block_detected`;
- `customer_block_lines`;
- `history_detection`;
- `months_detected`;
- `average_source`;
- `confidence_inputs`;
- `discarded_fields`;
- `anchors`;
- `source_snippets`, sempre mascarado;
- `review_warnings`;
- `review_reasons`.

O painel mostra esses dados em `Detalhes da extracao`, facilitando entender por que um campo foi descartado ou por que a leitura ficou em revisao.

## OCR

O OCR suporta PNG, JPG, JPEG, WEBP e PDFs escaneados. Para PDF, o sistema sempre tenta primeiro a extracao textual com PyMuPDF. Se o texto for vazio, insuficiente, iniciar com `%PDF`, parecer binario ou nao tiver pistas reais de conta de energia, o OCR processa no maximo `ENERGY_BILL_OCR_MAX_PAGES` paginas quando estiver habilitado.

O sistema nunca deve decodificar bytes brutos de PDF como texto. Todo texto extraido e sanitizado antes de ir para o banco, removendo `NUL (0x00)` e controles perigosos em campos `Text`, `String` e JSONB (`parsed_fields` e `raw_extraction`). Quando o arquivo for PDF escaneado/binario e OCR estiver desligado ou falhar, a extracao fica como `failed`/`needs_review` com mensagem amigavel para revisao manual, sem erro 500 no painel.

Providers:

- `disabled`: padrao seguro, retorna texto vazio e erro controlado.
- `local_tesseract`: usa `pytesseract`, `Pillow` e `pypdfium2`.
- `openai_vision`: preparado, mas bloqueado sem `ENERGY_BILL_ALLOW_EXTERNAL_AI=true`.

Metadados gravados em `parsed_fields`:

- `extraction_method`: `pdf_text`, `text_file`, `ocr`, `pdf_text_insufficient`, `image_ocr_failed` ou `unsupported`;
- `ocr_used`;
- `ocr_provider`;
- `ocr_page_count`;
- `ocr_error`;
- `raw_text_source`;
- `direct_text_length`.

Quando OCR estiver desabilitado e o arquivo parecer imagem ou PDF escaneado, o painel mostra: "O arquivo parece ser imagem ou PDF escaneado. Ative OCR local para leitura automatica ou revise manualmente." Quando OCR local extrair texto, o painel orienta revisar os dados antes de aplicar ao lead.

Dependencias no Docker:

- `tesseract-ocr`;
- `tesseract-ocr-por`;
- `tesseract-ocr-eng`;
- pacotes Python `pytesseract`, `Pillow` e `pypdfium2`.
- pacote Python `PyMuPDF` para extracao textual segura de PDF.

## LGPD e seguranca

- Nao logar texto bruto completo da conta.
- Nao expor CPF/CNPJ completo.
- `raw_text_excerpt` e mascarado.
- `raw_text_excerpt`, `parsed_fields`, `raw_extraction` e mensagens de erro sao sanitizados para remover NUL/control characters.
- `ENERGY_BILL_STORE_RAW_TEXT=false` por padrao.
- Validar tipo e tamanho de arquivo.
- Rejeitar extensoes executaveis.
- Revisar permissoes do painel.
- Usar storage privado em producao.
- Ativar IA/OCR externo somente com base legal, contrato e politica de privacidade revisados.
- Validar OCR com contas reais antes de ativar em producao.
- Processar apenas as primeiras paginas configuradas para evitar carga excessiva.

## Propostas e kits

Ao aplicar a extracao ao lead, o sistema grava em `lead.extra`:

- `energy_bill_extraction_id`;
- `bill_file_received`;
- `bill_extraction_origin`;
- `bill_extraction_confidence_score`;
- `bill_needs_human_review`;
- `average_consumption_kwh`;
- `current_consumption_kwh`;
- `average_bill_amount`;
- `current_bill_amount`;
- `customer_unit_number`;
- `customer_address`;
- `customer_district`;
- `customer_postal_code`;
- `tariff_flag`;
- `history_months_detected`;
- `average_source`;
- `estimated_system_power_kwp`;
- `estimated_monthly_generation_kwh`;
- `utility_company`.

Ao gerar proposta, o backend prefere `average_consumption_kwh` vindo de historico da conta. Se nao houver historico, usa o consumo atual; se tambem nao houver, cai para valor medio da conta/valor atual. As notas internas da proposta indicam se o pre-dimensionamento veio de `history_12_months`, `history_partial` ou `current_consumption_only`.

A proposta continua `draft` e deve ser revisada antes de envio.

Extracoes com valor da conta ausente, cidade/UF ausente, unidade consumidora ausente ou confianca abaixo de 80% precisam ser confirmadas por usuario interno antes de aplicar ao lead. Esse bloqueio evita que uma leitura incerta alimente automaticamente proposta ou CRM.

## Como testar

Backend:

```bash
cd backend
python -m unittest discover tests
python -m compileall app tests
alembic upgrade head --sql
```

Painel:

1. Acesse `http://localhost:5173`.
2. Entre no painel admin.
3. Abra `Contas`.
4. Envie um `.txt` com dados de conta ou cole texto em `Testar texto extraido`.
5. Envie tambem uma imagem/PDF escaneado em ambiente com OCR local habilitado.
6. Confira consumo, valor, historico, confianca, campos faltantes e metadados de OCR.
7. Abra `Detalhes da extracao` e confira ancoras, trechos mascarados e campos descartados.
8. Confirme a leitura quando os dados estiverem corretos.
9. Aplique em um lead.
10. Gere proposta e revise o kit recomendado.

Widget:

1. Inicie um fluxo de orcamento.
2. Confirme o consentimento LGPD.
3. Envie uma conta em PDF ou imagem.
4. Confirme que a conversa registra o anexo e que a tela `Contas` mostra `Origem: Chatbot`.
5. Confirme que `collected_data` e lead sao atualizados apos o processamento.

## Checklist de homologacao

- [ ] Testar com contas reais das principais distribuidoras atendidas.
- [ ] Validar CPFL e ao menos uma conta generica.
- [ ] Confirmar mascaramento de CPF/CNPJ.
- [ ] Confirmar que `Verde`/bandeiras tarifarias nao viram unidade consumidora.
- [ ] Confirmar que endereco institucional da distribuidora nao vira cidade do cliente.
- [ ] Confirmar que valor desconhecido aparece como `null`/`Nao identificado`, nao como `R$ 0,00`.
- [ ] Confirmar que arquivos grandes sao rejeitados.
- [ ] Confirmar que OCR desligado nao quebra o fluxo.
- [ ] Habilitar `local_tesseract` em homologacao e validar PNG/JPG/WEBP.
- [ ] Validar PDF textual sem OCR e PDF escaneado com OCR.
- [ ] Confirmar `parsed_fields.ocr_used`, `ocr_provider`, `ocr_page_count` e `ocr_error`.
- [ ] Revisar status `needs_review`.
- [ ] Confirmar que extracao com campos criticos pendentes exige confirmacao antes de aplicar ao lead.
- [ ] Aplicar extracao confirmada em lead real de teste.
- [ ] Gerar proposta e conferir kit recomendado.
- [ ] Enviar conta pelo widget e confirmar `origin=chatbot`.
- [ ] Enviar midia WhatsApp de teste e confirmar pendencia ate download privado.
- [ ] Revisar LGPD e politica de retencao.
- [ ] Definir storage privado para anexos em producao.
