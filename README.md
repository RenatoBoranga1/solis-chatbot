# Solar Soluções Solis Chatbot

Solis é um chatbot comercial e técnico para a Solar Soluções, preparado para site, WhatsApp Business API, CRM, abertura de chamados, base de conhecimento com RAG e atendimento humano assistido.

## Visao geral

O projeto esta organizado como um monorepo simples:

- `backend`: API FastAPI, PostgreSQL, Alembic, regras de atendimento, classificacao de intencao e gravidade.
- `frontend`: painel administrativo e demonstracao do widget em React.
- `widget`: script JavaScript puro embutivel em qualquer site institucional.
- `docs`: prompt de sistema, arquitetura, fluxos e orientacoes de deploy.

## Principais capacidades

- Primeiro atendimento humanizado com o Solis.
- Fluxos de orçamento, suporte técnico, app sem atualizar, cliente irritado e risco elétrico.
- Coleta progressiva de dados, uma pergunta por vez.
- Leads comerciais com status `Novo orçamento`.
- Propostas comerciais com rascunho a partir de leads, itens editáveis, PDF e envio simulado.
- Chamados técnicos com gravidade baixa, média ou alta.
- Tabela de precos configuravel para propostas e PDF comercial com visual premium.
- Transferencia para humano em casos graves, complexos, comerciais estrategicos ou sem resposta confiavel.
- Base de conhecimento administravel e pronta para RAG.
- Kits fotovoltaicos configuraveis com simulador e selecao automatica para pre-propostas revisaveis.
- Leitor Inteligente de Conta de Energia com extracao de consumo, valor, historico, confianca, dados do cliente e revisao humana.
- Parser CPFL com separacao entre cabecalho da distribuidora e bloco real do cliente, incluindo CEP, cidade/UF, endereco, unidade e historico de 12 meses.
- Base multimidia com videos oficiais, PDFs, manuais e links de apoio seguros.
- Registro de perguntas sem resposta.
- Painel com dashboard, conversas, leads, chamados e artigos.
- Análise Inteligente para conversas, leads, chamados e insights estratégicos do dashboard.
- Continuidade omnichannel do atendimento iniciado no site para o WhatsApp oficial, com contexto preservado.
- LGPD desde o inicio: consentimento, minimizacao, auditoria e endpoints para solicitacoes de dados.

## Como rodar localmente com Docker

1. Copie o arquivo de ambiente:

```bash
cp .env.example .env
```

2. Suba os servicos:

```bash
docker compose up --build
```

3. Acesse:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Painel/widget: `http://localhost:5173`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

## Rodando sem Docker

Backend:

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Usuario inicial

Em desenvolvimento, rode `python -m app.seed` apos as migrations. Isso cria:

- e-mail: `admin@solarsolucoes.com.br`
- senha: `Solar@12345`

Troque essa senha antes de qualquer ambiente compartilhado. A autenticacao usa JWT e perfis:

- `admin`
- `comercial`
- `suporte`
- `tecnico`
- `gestor`

## Prompt de sistema

O prompt oficial do Solis está em [`docs/SOLIS_SYSTEM_PROMPT.md`](docs/SOLIS_SYSTEM_PROMPT.md). Ele também é exportado pelo backend em `app/services/solis_prompt.py` para uso com OpenAI API ou outro provedor.

## Endpoints principais

Autenticacao:

- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

Chat:

- `POST /chat/message`
- `GET /chat/conversations`
- `GET /chat/conversations/{id}`
- `POST /chat/conversations/{id}/handoff`
- `POST /chat/conversations/{id}/continue-whatsapp`
- `POST /chat/conversations/{id}/assign`

Leads:

- `GET /leads`
- `POST /leads`
- `GET /leads/{id}`
- `PUT /leads/{id}`
- `PATCH /leads/{id}/status`

Propostas:

- `GET /proposals`
- `POST /proposals`
- `POST /proposals/from-lead/{lead_id}`
- `GET /proposals/{id}`
- `PUT /proposals/{id}`
- `PATCH /proposals/{id}/status`
- `POST /proposals/{id}/items`
- `PUT /proposals/{id}/items/{item_id}`
- `DELETE /proposals/{id}/items/{item_id}`
- `POST /proposals/{id}/generate-pdf`
- `POST /proposals/{id}/apply-price-table`
- `POST /proposals/{id}/send`
- `POST /proposals/{id}/share-link`
- `GET /proposals/{id}/share-links`
- `PATCH /proposals/share-links/{link_id}/revoke`
- `GET /proposals/followups`
- `POST /proposals/{id}/followups`
- `PATCH /proposals/followups/{followup_id}/complete`
- `PATCH /proposals/followups/{followup_id}/cancel`
- `GET /public/proposals/{token}`
- `POST /public/proposals/{token}/responses`
- `GET /public/proposals/{token}/pdf`
- `GET /company-settings`
- `PUT /company-settings`
- `GET /proposal-price-items`
- `POST /proposal-price-items`
- `PUT /proposal-price-items/{id}`
- `PATCH /proposal-price-items/{id}/active`
- `DELETE /proposal-price-items/{id}`
- `GET /proposal-kits`
- `POST /proposal-kits`
- `POST /proposal-kits/simulate`
- `GET /proposal-kits/{id}`
- `PUT /proposal-kits/{id}`
- `PATCH /proposal-kits/{id}/active`
- `DELETE /proposal-kits/{id}`
- `POST /proposal-kits/{id}/items`
- `PUT /proposal-kits/{id}/items/{item_id}`
- `DELETE /proposal-kits/{id}/items/{item_id}`

Chat e anexos:

- `POST /chat/message`
- `POST /chat/attachments`

Contas de energia:

- `GET /energy-bills`
- `GET /energy-bills/{extraction_id}`
- `POST /energy-bills/extract`
- `POST /energy-bills/extract-from-attachment/{attachment_id}`
- `PUT /energy-bills/{extraction_id}`
- `POST /energy-bills/{extraction_id}/confirm`
- `POST /energy-bills/{extraction_id}/apply-to-lead/{lead_id}`
- `POST /energy-bills/{extraction_id}/generate-proposal`
- `POST /energy-bills/{extraction_id}/discard`
- `POST /energy-bills/parse-text`

O leitor de contas salva campos estruturados como `customer_address`, `customer_district`, `customer_postal_code`, `customer_unit_number`, `tariff_flag`, historico mensal e `average_source`. Para CPFL, o parser prioriza o bloco `CEP CIDADE UF` do cliente e descarta cabecalhos com `CPFL`, `DANF`, `Companhia`, `CNPJ`, atendimento, ouvidoria e endereco institucional. Veja o guia em [`docs/energy-bill-extraction.md`](docs/energy-bill-extraction.md).

Tickets:

- `GET /tickets`
- `POST /tickets`
- `GET /tickets/{id}`
- `PUT /tickets/{id}`
- `PATCH /tickets/{id}/status`
- `PATCH /tickets/{id}/severity`

Base de conhecimento:

- `GET /knowledge`
- `POST /knowledge`
- `PUT /knowledge/{id}`
- `DELETE /knowledge/{id}`

Dashboard:

- `GET /dashboard/metrics`
- `GET /dashboard/intents`
- `GET /dashboard/severity`
- `GET /dashboard/resolution-rate`

`GET /dashboard/metrics` tambem retorna `proposal_metrics`, com propostas criadas, enviadas, aceitas, visualizadas, follow-ups pendentes/vencidos, valor de pipeline, ticket medio e conversao.

Análise Inteligente:

- `POST /ai/conversations/{conversation_id}/analyze`
- `GET /ai/conversations/{conversation_id}/analysis`
- `POST /ai/leads/{lead_id}/analyze`
- `GET /ai/leads/{lead_id}/analysis`
- `POST /ai/tickets/{ticket_id}/analyze`
- `GET /ai/tickets/{ticket_id}/analysis`
- `POST /ai/conversations/{conversation_id}/suggest-reply`
- `GET /ai/dashboard/insights`

## Integracao com site

Inclua o script abaixo no site institucional:

```html
<script
  src="https://seu-dominio.com/widget/solis-widget.js"
  data-api-base="https://api.seu-dominio.com"
  data-brand-name="Solar Soluções"
></script>
```

Durante o desenvolvimento, o arquivo fica em `widget/solis-widget.js`.

### Conexao real do widget

O frontend usa `VITE_API_BASE_URL` para chamar o backend. Em desenvolvimento, se a variavel nao existir, o fallback seguro e `http://localhost:8000`; em producao, configure explicitamente a URL publica da API.

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_ENABLE_DEMO_FALLBACK=true
```

O widget chama `GET /health` ao abrir e antes de liberar o atendimento real. Se a API estiver offline, ele mostra aviso visivel, bloqueia upload de conta de energia e permite clicar em `Tentar reconectar`.

`VITE_ENABLE_DEMO_FALLBACK=true` deve ser usado apenas em desenvolvimento e demonstracoes controladas. Nesse modo, a interface exibe `Modo demonstracao` e informa que mensagens, leads e anexos nao serao salvos. Em producao, use:

```env
VITE_ENABLE_DEMO_FALLBACK=false
```

O painel administrativo possui a aba `Diagnostico`, com URL da API, resposta do `/health`, ambiente, fallback demo e ultimo erro de conexao. Guia de correcao: [`docs/troubleshooting.md`](docs/troubleshooting.md).

O widget React e o script embutível mostram a mensagem do usuário imediatamente, exibem uma bolha temporária de processamento com três pontos animados, bloqueiam envio/atalhos enquanto aguardam resposta e mantêm o atraso humanizado apenas no frontend. O backend continua respondendo o mais rápido possível.

## Leitor Inteligente de Conta de Energia

A tela `Contas` do painel permite enviar PDF, imagem ou texto de conta de energia, interpretar dados comerciais e tecnicos e revisar tudo antes de aplicar ao lead.

Quando o cliente envia PDF ou imagem pelo widget durante um fluxo de orcamento com consentimento LGPD, o backend registra `Attachment`, cria automaticamente uma `EnergyBillExtraction` com `origin=chatbot`, deixa o status como `processing` e agenda a leitura em background. O painel mostra a origem da conta, o vinculo com conversa/lead e os campos extraidos para revisao. Mensagens WhatsApp com midia tambem ficam preparadas para `origin=whatsapp`; enquanto o download privado da midia Meta nao estiver habilitado, o arquivo fica como `whatsapp://media/<media_id>` para revisao operacional.

Para imagens e PDFs escaneados, o modulo possui OCR local opcional com Tesseract. PDF textual e lido com PyMuPDF primeiro sem OCR; se o texto for vazio, binario, iniciar com `%PDF` ou nao tiver pistas reais de conta de energia, o sistema tenta OCR quando `ENERGY_BILL_OCR_ENABLED=true`. O painel exibe metodo de extracao, provider OCR, paginas processadas e erro amigavel quando OCR estiver desligado ou indisponivel.

O upload de PDF tambem possui protecao contra conteudo binario gravado como texto. O backend remove bytes NUL/control characters antes de persistir `raw_text_excerpt`, `parsed_fields`, `raw_extraction`, campos de cliente/instalacao e mensagens de erro. Se a conta for PDF escaneado sem OCR habilitado, a extracao fica como `failed`/`needs_review` para revisao manual, sem retornar erro 500 ao painel.

O parser de contas e conservador: se nao houver certeza, o campo fica `null` e entra em `missing_fields`/`review_reasons`. Bandeiras tarifarias como `Verde`, `Amarela`, `Vermelha` e `Escassez hidrica` sao registradas como `tariff_flag`, nunca como unidade consumidora, cidade ou cliente. Linhas institucionais da distribuidora, agencia, atendimento, `TERREO`, sede ou ouvidoria nao sao usadas como endereco/cidade do cliente. Valor desconhecido nao aparece como `R$ 0,00`; o painel mostra `Nao identificado` e exige revisao.

Dados extraidos:

- distribuidora;
- nome/documento mascarado;
- numero da instalacao ou unidade consumidora;
- cidade/UF;
- referencia e vencimento;
- consumo atual em kWh;
- valor atual da conta;
- historico mensal de consumo;
- media, minimo e maximo de consumo;
- potencia e geracao estimadas;
- score de confianca e campos faltantes.
- detalhes da extracao em `parsed_fields`, incluindo ancoras usadas, trechos mascarados e campos descartados.

Variaveis:

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

Para habilitar OCR local em homologacao:

```env
ENERGY_BILL_OCR_ENABLED=true
ENERGY_BILL_OCR_PROVIDER=local_tesseract
```

O OCR externo/IA visual fica desligado por padrao e so deve ser usado com `ENERGY_BILL_ALLOW_EXTERNAL_AI=true`, contrato/base legal revisados e chave configurada. A extracao nao grava texto bruto completo, mascara CPF/CNPJ e gera status `needs_review` quando a confianca fica abaixo do limite. Guia completo: [`docs/energy-bill-extraction.md`](docs/energy-bill-extraction.md).

## WhatsApp Cloud API oficial

O projeto possui integracao oficial com WhatsApp Business Platform / Cloud API da Meta. O webhook recebe eventos em `/webhook/whatsapp`, valida o `verify token`, valida `X-Hub-Signature-256`, ignora duplicidades por `message_id`, chama o `ConversationService` e responde ao cliente pela Cloud API.

Variáveis necessárias:

- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_BUSINESS_ACCOUNT_ID`
- `WHATSAPP_VERIFY_TOKEN`
- `WHATSAPP_APP_SECRET`
- `WHATSAPP_API_VERSION`

URL de callback para configurar na Meta:

```text
https://seu-dominio.com/webhook/whatsapp
```

Para testar localmente, exponha o backend com ngrok:

```bash
ngrok http 8000
```

Depois use a URL HTTPS do ngrok como callback, por exemplo:

```text
https://abc123.ngrok-free.app/webhook/whatsapp
```

No painel da Meta, defina o mesmo `WHATSAPP_VERIFY_TOKEN` configurado no `.env`. A rota `GET /webhook/whatsapp` responde o `hub.challenge` quando o token estiver correto.

Checklist para ativar WhatsApp real:

- [ ] Criar app na Meta Developers.
- [ ] Adicionar o produto WhatsApp.
- [ ] Copiar `Phone Number ID`.
- [ ] Gerar `WHATSAPP_ACCESS_TOKEN`.
- [ ] Configurar `WHATSAPP_APP_SECRET`.
- [ ] Definir `WHATSAPP_VERIFY_TOKEN`.
- [ ] Subir o backend local ou em produção.
- [ ] Expor o backend com ngrok ou Cloudflare Tunnel em ambiente local.
- [ ] Configurar `https://SEU_SUBDOMINIO.ngrok-free.app/webhook/whatsapp` na Meta.
- [ ] Assinar eventos de `messages`.
- [ ] Enviar mensagem de teste.
- [ ] Confirmar criação de `WebhookEvent`.
- [ ] Confirmar resposta automática do bot.
- [ ] Confirmar registro da conversa no painel.

Mensagens iniciadas pelo cliente dentro da janela de 24 horas podem receber resposta livre. Mensagens iniciadas pela empresa fora dessa janela exigem templates aprovados pela Meta.

Eventos recebidos sao gravados pelo modelo `WebhookEvent` na tabela `webhook_events` antes do processamento. A tabela guarda `provider`, `event_id`, `payload`, `processed` e `error_message`, permitindo auditoria e reprocessamento futuro sem expor tokens em logs. Mensagens duplicadas sao bloqueadas pelo indice unico `ux_messages_provider_message_id` em `messages(provider, provider_message_id)`.

Anexos de `image`, `document` e `audio` sao registrados pelo modelo `Attachment` na tabela `attachments`, com `media_id`, `media_type`, `provider_media_id`, `message_id` e `conversation_id`. Enquanto o download definitivo de midia nao estiver ativo, o arquivo fica referenciado como `whatsapp://media/<media_id>` junto ao `provider_media_id`.

O retorno do webhook inclui `send_errors`. Esse contador aumenta quando o envio pela Graph API retorna `status="error"` ou `status="skipped"`, sem expor token, payload bruto ou telefone completo. Em producao, configure obrigatoriamente `APP_ENV=production` e `WHATSAPP_APP_SECRET`. Sem assinatura `X-Hub-Signature-256` valida, o webhook retorna `403`. O webhook deve responder rapidamente; para alto volume, a proxima evolucao recomendada e colocar o processamento em uma fila assincrona.

Antes de publicar ou atualizar ambientes, rode:

```bash
cd backend
alembic upgrade head
python -m unittest discover tests
```

Guia completo: [`docs/whatsapp-cloud-api.md`](docs/whatsapp-cloud-api.md).

### Continuidade site -> WhatsApp

Atendimentos qualificados no site podem ser continuados pelo WhatsApp oficial pelo endpoint autenticado:

```text
POST /chat/conversations/{conversation_id}/continue-whatsapp
```

O painel exibe o botão "WhatsApp" em conversas do site nos status `commercial_triage`, `technical_triage`, `handoff` ou `human_assigned`. Em desenvolvimento, se a Cloud API não estiver configurada, o envio é simulado e registrado no banco. Em produção, mensagens iniciadas pela empresa devem usar template aprovado pela Meta.

A tabela `conversation_channel_links` registra a migração:

- conversa de origem no site;
- conversa de destino no WhatsApp, quando confirmada;
- telefone normalizado;
- lead ou chamado vinculado;
- status `pending`, `invited`, `confirmed`, `expired` ou `failed`.

Quando o cliente responde `SIM`, `ok`, `confirmo` ou equivalente no WhatsApp, o webhook identifica o telefone, confirma o link, cria a conversa WhatsApp herdando `collected_data`, `summary`, `intent` e `severity`, e continua o atendimento sem pedir tudo novamente.

Guia completo: [`docs/omnichannel.md`](docs/omnichannel.md).

## Adaptadores futuros de WhatsApp

O endpoint `POST /chat/message` continua funcionando para widget, testes e integrações futuras. Ele também pode ser usado por provedores como Z-API, Twilio, WATI, Take Blip ou Evolution API convertendo o webhook recebido para o contrato:

```json
{
  "channel": "whatsapp",
  "external_id": "telefone-ou-id-do-provedor",
  "message": "Quero instalar energia solar"
}
```

## IA e RAG

O servico `KnowledgeService` recupera artigos ativos por palavras-chave e categoria. Em producao, conecte embeddings e reranking mantendo as regras:

- responder apenas com base oficial;
- não inventar preço, prazo, economia, garantia ou diagnóstico;
- registrar pergunta sem resposta;
- encaminhar para humano quando a confianca for baixa.

## Base de conhecimento multimídia

Os artigos da base podem ter resposta oficial, vídeo recomendado e material de apoio. Campos disponíveis:

- `video_title` e `video_url`;
- `resource_title`, `resource_url` e `resource_type`;
- `send_video_with_answer`;
- `send_resource_with_answer`.

O bot envia links em texto simples, compatíveis com WhatsApp e widget. No site, links do YouTube aparecem como card simples com botão "Assistir vídeo". Vídeos automáticos devem ser ativados apenas para conteúdos oficiais e seguros, como limpeza preventiva, uso do aplicativo, leitura de geração e orientações gerais.

Em risco elétrico, como cheiro de queimado, faísca, fumaça, choque ou curto, o bot não sugere vídeo de instrução e prioriza segurança com encaminhamento humano. Guia completo: [`docs/knowledge-base.md`](docs/knowledge-base.md).

## Análise Inteligente

O painel administrativo possui uma camada de análise estratégica para conversas, leads, chamados e dashboard. Ela gera resumo executivo, intenção principal, sentimento, urgência, oportunidade comercial, risco técnico, dados faltantes, próxima ação, resposta sugerida, tags e score de prioridade.

Variáveis:

- `ENABLE_GENERATIVE_AI=false`
- `OPENAI_API_KEY=`
- `AI_PROVIDER=openai`
- `AI_MODEL=gpt-4.1-mini`

Com `ENABLE_GENERATIVE_AI=false` ou sem chave de IA, o sistema usa fallback por regras e continua funcionando sem custo externo. Com IA generativa habilitada e chave configurada, o serviço tenta usar o provedor configurado e volta para regras se houver erro. As respostas sugeridas devem ser revisadas por um atendente antes do envio e não prometem preço, prazo, economia, garantia ou diagnóstico final.

## Propostas comerciais

O painel possui a área `Propostas`, onde a Solar Soluções pode criar propostas manuais ou gerar rascunhos a partir de leads captados pelo Solis. A proposta inclui dados do cliente, dados técnicos estimados, itens editáveis, subtotal, desconto, total, condições de pagamento, validade e geração de PDF.

Pontos importantes:

- propostas geradas automaticamente sempre começam como `draft`;
- itens e valores ficam editáveis para revisão humana;
- o PDF deixa claro que valores, prazos e condições dependem de validação técnica e comercial;
- em desenvolvimento, o envio é simulado;
- em produção, envio ativo pelo WhatsApp exige observar a janela de 24 horas ou templates aprovados pela Meta;
- PDFs devem ser armazenados em local seguro em produção.

Guia completo: [`docs/proposals.md`](docs/proposals.md).

### Kits fotovoltaicos configuraveis

A aba `Kits fotovoltaicos` permite cadastrar kits comerciais com faixas de consumo, faixas de potencia, potencia sugerida, geracao estimada, modulos, inversor, preco base e itens detalhados. Ao gerar proposta a partir de lead, o backend calcula potencia/geracao estimadas e tenta selecionar automaticamente o kit ativo mais adequado.

Ordem de selecao:

- faixa de potencia estimada;
- faixa de geracao/consumo mensal;
- kit imediatamente acima da potencia estimada;
- maior kit ativo;
- fallback para tabela de precos ou itens padrao zerados quando nao houver kit.

Exemplo: com conta media de R$ 350,00, o simulador estima aproximadamente 313 kWh/mes e 2,32 kWp. Se houver um kit ativo com faixa compativel, ele aparece como `kit recomendado`, mas a proposta permanece `draft` e deve ser revisada por humano antes de qualquer envio.

Guia completo: [`docs/proposal-kits.md`](docs/proposal-kits.md).

### Evolucao profissional de propostas

- A aba `Tabela de precos` permite cadastrar itens base por categoria, quantidade, unidade e valor unitario.
- A aba `Kits fotovoltaicos` permite simular e montar pre-propostas com kit recomendado.
- Propostas geradas por lead usam a tabela ativa quando existir; se nao houver tabela, os itens entram zerados para revisao manual.
- Quando ha kit recomendado, o PDF e a tela da proposta exibem nome do kit, potencia, modulos, inversor, geracao estimada, motivo da selecao e aviso de revisao tecnica/comercial.
- O bot e a IA nao definem preco final sozinhos.
- O botao `Aplicar tabela de precos` recalcula uma proposta existente com os itens ativos configurados.
- O PDF premium usa dados da empresa, capa visual, resumo tecnico, tabela de itens, resumo financeiro, avisos comerciais e rodape.
- A aba `Configuracoes comerciais` permite ajustar dados da empresa, cores, validade padrao, condicoes de pagamento e observacoes usadas no PDF.
- O envio suporta `manual`, `whatsapp`, `email` e `secure_link`.
- Em desenvolvimento, envios por WhatsApp e e-mail sao simulados.
- Envio manual nao marca como `sent` automaticamente, salvo quando `mark_as_sent=true`.
- Em producao, envio por e-mail usa SMTP (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`).
- Links seguros usam `/proposta/{token}` no frontend e `/public/proposals/{token}` no backend, com expiracao, revogacao, contagem de visualizacoes e download de PDF protegido por token.
- O cliente pode responder digitalmente: interesse, aceite, recusa, pedido de ajuste ou falar com consultor.
- A proposta registra linha do tempo em `proposal_events` e retornos comerciais em `proposal_followups`.
- Em producao, configure `FRONTEND_ORIGINS` com o dominio publico do painel/site para gerar links corretos.

## LGPD

O chatbot informa a finalidade antes de coletar dados pessoais. O backend inclui campos de consentimento, trilha de auditoria e estrutura para exclusao/alteracao sob solicitacao. Em producao, configure:

- chave forte `FIELD_ENCRYPTION_KEY`;
- HTTPS obrigatorio;
- retenção de dados por política formal;
- controle de acesso por perfil;
- backups criptografados;
- logs sem dados sensiveis desnecessarios.

## Testes

```bash
cd backend
python -m unittest discover tests

cd ../frontend
npm test
npm run build
```

Os testes cobrem classificacao de intencao, gravidade, validacao do webhook, assinatura da Meta, deduplicacao, anexos, auditoria `WebhookEvent`, continuidade site -> WhatsApp, propostas comerciais, kits fotovoltaicos, tabela de precos, link seguro, resposta digital, follow-ups, configuracoes comerciais, falhas de envio, `/health` e configuracao de conexao do widget.

## Deploy sugerido

1. Provisionar PostgreSQL gerenciado e Redis.
2. Configurar variaveis do `.env.example` no provedor.
3. Rodar `alembic upgrade head` no release.
4. Subir backend FastAPI com Gunicorn/Uvicorn workers.
5. Publicar frontend estatico em CDN/Vercel/Netlify ou servir por Nginx.
6. Servir `widget/solis-widget.js` com cache versionado.
7. Configurar dominio, HTTPS, CORS restrito e WAF/rate limit.
8. Configurar webhook oficial da Meta em `https://seu-dominio.com/webhook/whatsapp`.
9. Cadastrar base de conhecimento oficial antes de habilitar respostas generativas.
10. Configurar `FRONTEND_ORIGINS` com o dominio publico e validar `/proposta/{token}` antes de enviar propostas reais.
11. Configurar `VITE_API_BASE_URL` no frontend apontando para a API publica.
12. Manter `VITE_ENABLE_DEMO_FALLBACK=false` em producao.
