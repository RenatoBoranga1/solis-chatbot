# Deployment checklist

Use este checklist antes de homologar ou publicar o Solis Chatbot com WhatsApp Cloud API oficial.

## Ambiente

- Configurar HTTPS no dominio real.
- Configurar `APP_ENV=production`.
- Configurar `APP_DEBUG=false`.
- Restringir `FRONTEND_ORIGINS` aos dominios oficiais.
- Configurar `VITE_API_BASE_URL` no frontend com a URL publica da API.
- Configurar `VITE_ENABLE_DEMO_FALLBACK=false` em producao.
- Trocar credenciais padrao do usuario admin.
- Usar `JWT_SECRET_KEY` forte.
- Usar `FIELD_ENCRYPTION_KEY` forte.

## WhatsApp Cloud API

- Configurar `WHATSAPP_ACCESS_TOKEN`.
- Configurar `WHATSAPP_PHONE_NUMBER_ID`.
- Configurar `WHATSAPP_BUSINESS_ACCOUNT_ID`.
- Configurar `WHATSAPP_VERIFY_TOKEN`.
- Configurar `WHATSAPP_APP_SECRET`.
- Criar e aprovar template `continuar_atendimento_site` no WhatsApp Manager para convites iniciados pela empresa.
- Configurar callback `https://seu-dominio.com/webhook/whatsapp` na Meta.
- Assinar o campo `messages`.
- Validar `GET /webhook/whatsapp` no painel da Meta.
- Confirmar que assinatura ausente ou invalida retorna `403` em producao.

## Análise Inteligente

- Configurar `ENABLE_GENERATIVE_AI=false` para usar apenas fallback por regras.
- Configurar `OPENAI_API_KEY` somente em ambientes que usarão IA generativa.
- Configurar `AI_PROVIDER=openai`.
- Configurar `AI_MODEL` conforme política de custo e qualidade.
- Confirmar que análises mascaram dados sensíveis.
- Orientar atendentes a revisar respostas sugeridas antes do envio.

## Banco e migrations

```bash
cd backend
alembic upgrade head
```

Confirmar tabelas:

- `messages` com `provider` e `provider_message_id`;
- indice unico `ux_messages_provider_message_id`;
- `webhook_events`;
- `attachments`.
- `ai_analyses`.
- `knowledge_base_articles` com campos de vídeo e material de apoio.
- `conversation_channel_links`.
- `proposals`.
- `proposal_items`.
- `proposal_price_items`.
- `proposal_kits`.
- `proposal_kit_items`.
- `proposal_share_links`.
- `proposal_customer_responses`.
- `proposal_events`.
- `proposal_followups`.
- `company_settings`.
- `energy_bill_extractions`.
- `energy_bill_consumption_history`.

## Saude da API e widget

- Confirmar que `GET /health` retorna `status=ok`, `service` e `environment`.
- Confirmar que o backend possui healthcheck no Docker Compose.
- Confirmar que o frontend recebeu `VITE_API_BASE_URL` e nao `API_BASE_URL`.
- Confirmar que o painel `Diagnostico` mostra a API online.
- Confirmar que o widget bloqueia upload quando a API esta offline.
- Confirmar que `VITE_ENABLE_DEMO_FALLBACK=false` bloqueia atendimento simulado em producao.
- Usar [`docs/troubleshooting.md`](troubleshooting.md) quando aparecer `API offline` ou `Modo demonstracao`.

## Omnichannel

- Testar `POST /chat/conversations/{conversation_id}/continue-whatsapp`.
- Confirmar que casos de alta gravidade exigem revisão humana.
- Confirmar que telefones estão normalizados apenas com dígitos.
- Confirmar que resposta `SIM` no WhatsApp cria conversa vinculada ao atendimento do site.
- Monitorar links com status `failed`, `expired` ou `pending` antigo.

## Propostas comerciais

- Configurar `PROPOSAL_STORAGE_PATH`.
- Configurar `FRONTEND_ORIGINS` com o dominio publico que servira `/proposta/{token}`.
- Configurar dados da empresa para o PDF: `COMPANY_NAME`, `COMPANY_PHONE`, `COMPANY_EMAIL`, `COMPANY_WEBSITE`, `COMPANY_ADDRESS`, `COMPANY_LOGO_PATH`, `COMPANY_PRIMARY_COLOR` e `COMPANY_SECONDARY_COLOR`.
- Revisar a aba `Configuracoes comerciais` no painel antes da primeira proposta real.
- Configurar SMTP para envio real por e-mail: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME` e `SMTP_USE_TLS`.
- Cadastrar e revisar a tabela de precos antes de gerar propostas reais a partir de lead.
- Cadastrar kits fotovoltaicos reais antes de usar recomendacao automatica em propostas.
- Confirmar que kits demonstrativos do seed estao com `base_price=0` ou foram substituidos por valores revisados.
- Validar o simulador de kits com uma conta media, por exemplo R$ 350,00.
- Confirmar que proposta gerada por lead com kit recomendado permanece `draft`.
- Conferir que o PDF mostra a secao `Kit fotovoltaico recomendado`.
- Confirmar que propostas sem tabela ativa continuam com valores zerados para revisao manual.
- Nao enviar caminho local do PDF ao cliente.
- Validar envio manual, WhatsApp, e-mail e link seguro em ambiente de homologacao.
- Validar pagina publica `https://seu-dominio.com/proposta/{token}`.
- Validar download protegido em `/public/proposals/{token}/pdf`.
- Validar resposta digital do cliente: interessado, aceite, recusa, ajuste e consultor.
- Validar revogacao e expiracao de link seguro.
- Validar criacao e conclusao de follow-ups comerciais.
- Garantir que a pasta de PDFs tenha backup e controle de acesso.
- Revisar permissões dos perfis `admin`, `comercial` e `gestor`.
- Validar geração de PDF antes da homologação.
- Em produção, armazenar PDFs em storage privado, como S3 ou Cloudflare R2.
- Para envio por WhatsApp fora da janela de 24 horas, criar template aprovado pela Meta.
- Reforçar processo interno de revisão humana antes de enviar proposta ao cliente.

## Leitor Inteligente de Conta de Energia

- Configurar `ENERGY_BILL_EXTRACTION_ENABLED=true`.
- Manter `ENERGY_BILL_OCR_ENABLED=false` ate homologar OCR com seguranca.
- Para habilitar OCR local, configurar `ENERGY_BILL_OCR_ENABLED=true` e `ENERGY_BILL_OCR_PROVIDER=local_tesseract`.
- Configurar `ENERGY_BILL_OCR_MAX_PAGES=3` e `ENERGY_BILL_MIN_TEXT_LENGTH=80` como ponto de partida.
- Manter `ENERGY_BILL_ALLOW_EXTERNAL_AI=false` ate revisar LGPD, contrato e politica de privacidade.
- Configurar `ENERGY_BILL_MAX_FILE_SIZE_MB` conforme limite operacional.
- Configurar `ENERGY_BILL_STORE_RAW_TEXT=false` em producao, salvo necessidade formal e base legal.
- Configurar `ENERGY_BILL_STORAGE_PATH` em volume persistente ou storage privado.
- Configurar `CHAT_ATTACHMENT_STORAGE_PATH` em volume persistente ou storage privado para arquivos enviados pelo widget.
- Testar upload de PDF/TXT/imagem pelo painel `Contas`.
- Confirmar que a imagem Docker instalou `tesseract-ocr`, `tesseract-ocr-por` e `tesseract-ocr-eng`.
- Testar PNG/JPG/WEBP e PDF escaneado com OCR local em homologacao.
- Confirmar que PDF textual nao usa OCR quando a extracao direta for suficiente.
- Confirmar que PDF binario/escaneado sem OCR retorna `failed`/`needs_review` com mensagem amigavel, sem erro 500.
- Confirmar que nenhum retorno do painel contem `NUL (0x00)` em `raw_text_excerpt`, `parsed_fields`, `raw_extraction` ou `error_message`.
- Confirmar que bandeiras tarifarias (`Verde`, `Amarela`, `Vermelha`) aparecem como `tariff_flag` e nao como unidade/instalacao.
- Confirmar que endereco institucional da distribuidora, agencia, atendimento, `TERREO` ou ouvidoria nao aparece como cidade/endereco do cliente.
- Confirmar que valor desconhecido aparece como `Nao identificado` no painel, nao como `R$ 0,00`.
- Confirmar que `Detalhes da extracao` mostra ancoras, trechos mascarados e campos descartados.
- Confirmar que o painel mostra metodo de extracao, OCR usado, provider, paginas processadas e erro amigavel.
- Testar envio de PDF/imagem pelo widget em fluxo de orcamento e confirmar `origin=chatbot`.
- Confirmar que `conversation.collected_data` e `lead.extra` recebem consumo, valor, distribuidora, confianca e status da leitura.
- Para WhatsApp, baixar midia da Meta para storage privado antes de habilitar leitura automatica completa de `origin=whatsapp`.
- Confirmar que CPF/CNPJ aparece mascarado.
- Confirmar que extracoes de baixa confianca ficam como `needs_review`.
- Confirmar que extracoes com valor/cidade/unidade pendentes ou confianca abaixo de 80% precisam ser confirmadas antes de aplicar ao lead.
- Confirmar que aplicar extracao ao lead preenche `average_consumption_kwh` e `utility_company`.
- Confirmar que proposta gerada usa consumo medio extraido para recomendar kit.
- Definir rotina de limpeza/retencao de anexos conforme LGPD.

## Base multimídia

- Substituir placeholders de vídeos do seed por links oficiais.
- Revisar artigos antes de ativar `send_video_with_answer`.
- Não ativar vídeo automático para instruções com risco elétrico.
- Conferir preview da resposta no painel.

## Testes

```bash
cd backend
python -m unittest discover tests
```

Os testes devem cobrir webhook, assinatura, deduplicacao, anexos, auditoria, `send_errors`, continuidade omnichannel, propostas, kits fotovoltaicos, tabela de precos, link seguro, resposta digital, follow-ups, configuracoes comerciais, classificacao de gravidade e handoff.
Também devem cobrir análise por regras, lead quente, chamado crítico, resposta sugerida e endpoints de IA.

## Observabilidade e seguranca

- Ativar logs estruturados.
- Nao registrar token, payload bruto, documentos ou telefone completo em logs.
- Monitorar `send_errors`.
- Monitorar eventos `webhook_events.processed=false`.
- Configurar backup do PostgreSQL.
- Configurar politica de retencao LGPD.
- Configurar WAF/rate limit no dominio publico.

## Proximas evolucoes recomendadas

- Processar webhooks em fila/worker com Redis.
- Armazenar midias em S3, R2 ou storage equivalente.
- Armazenar PDFs de propostas em storage privado com URL temporária.
- Criar templates oficiais para mensagens fora da janela de 24 horas.
- Adicionar CI/CD com testes e migrations em release.
