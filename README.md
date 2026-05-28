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
- Chamados técnicos com gravidade baixa, média ou alta.
- Transferencia para humano em casos graves, complexos, comerciais estrategicos ou sem resposta confiavel.
- Base de conhecimento administravel e pronta para RAG.
- Registro de perguntas sem resposta.
- Painel com dashboard, conversas, leads, chamados e artigos.
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
- `POST /chat/conversations/{id}/assign`

Leads:

- `GET /leads`
- `POST /leads`
- `GET /leads/{id}`
- `PUT /leads/{id}`
- `PATCH /leads/{id}/status`

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

## WhatsApp Cloud API oficial

O projeto possui integração oficial com WhatsApp Business Platform / Cloud API da Meta. O webhook recebe eventos em `/webhook/whatsapp`, valida o `verify token`, valida `X-Hub-Signature-256` quando `WHATSAPP_APP_SECRET` estiver configurado, ignora duplicidades por `message_id`, chama o `ConversationService` e responde ao cliente pela Cloud API.

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

Mensagens iniciadas pelo cliente dentro da janela de 24 horas podem receber resposta livre. Mensagens iniciadas pela empresa fora dessa janela exigem templates aprovados pela Meta.

Guia completo: [`docs/whatsapp-cloud-api.md`](docs/whatsapp-cloud-api.md).

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
```

Os testes iniciais cobrem classificacao de intencao e gravidade. Amplie com testes de API, autenticacao e fluxos conversacionais antes de producao.

## Deploy sugerido

1. Provisionar PostgreSQL gerenciado e Redis.
2. Configurar variaveis do `.env.example` no provedor.
3. Rodar `alembic upgrade head` no release.
4. Subir backend FastAPI com Gunicorn/Uvicorn workers.
5. Publicar frontend estatico em CDN/Vercel/Netlify ou servir por Nginx.
6. Servir `widget/solis-widget.js` com cache versionado.
7. Configurar dominio, HTTPS, CORS restrito e WAF/rate limit.
8. Integrar webhook do WhatsApp ao adaptador escolhido.
9. Cadastrar base de conhecimento oficial antes de habilitar respostas generativas.
