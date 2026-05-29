# Deploy

## Backend

1. Provisionar PostgreSQL e Redis gerenciados.
2. Configurar variaveis de ambiente do `.env.example`.
3. Definir `APP_ENV=production` e `APP_DEBUG=false`.
4. Usar `JWT_SECRET_KEY` forte e `FIELD_ENCRYPTION_KEY` forte.
5. Restringir `FRONTEND_ORIGINS` aos dominios oficiais.
6. Rodar `alembic upgrade head` no processo de release.
7. Subir FastAPI com:

```bash
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --workers 3 --bind 0.0.0.0:8000
```

## Frontend

1. Definir `VITE_API_BASE_URL=https://api.seu-dominio.com`.
2. Rodar `npm run build`.
3. Publicar `frontend/dist` em CDN, Nginx, Vercel, Netlify ou equivalente.

## Widget

1. Hospedar `widget/solis-widget.js` em dominio publico com HTTPS.
2. Inserir no site institucional:

```html
<script
  src="https://cdn.seu-dominio.com/solis-widget.v1.js"
  data-api-base="https://api.seu-dominio.com"
  data-brand-name="Solar Soluções"
></script>
```

## WhatsApp

1. Usar a WhatsApp Cloud API oficial da Meta em `POST /webhook/whatsapp`.
2. Configurar callback HTTPS: `https://seu-dominio.com/webhook/whatsapp`.
3. Definir `WHATSAPP_VERIFY_TOKEN` no backend e no painel da Meta.
4. Definir `WHATSAPP_APP_SECRET` em producao para validar `X-Hub-Signature-256`.
5. Definir `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` e `WHATSAPP_BUSINESS_ACCOUNT_ID`.
6. Monitorar `webhook_events`, `duplicates` e `send_errors`.

## Producao segura

- HTTPS obrigatorio.
- `APP_ENV=production`.
- `APP_DEBUG=false`.
- `WHATSAPP_APP_SECRET` obrigatorio.
- `WHATSAPP_ACCESS_TOKEN` configurado sem versionar segredo.
- `WHATSAPP_PHONE_NUMBER_ID` e `WHATSAPP_BUSINESS_ACCOUNT_ID` conferidos.
- `alembic upgrade head` no release.
- Credenciais padrao trocadas.
- Rate limit em borda e API.
- WAF para painel administrativo.
- CORS restrito aos dominios oficiais.
- Backups automaticos criptografados.
- Logs estruturados sem payload bruto, token ou telefone completo.
- Logs sem dados sensiveis desnecessarios.
- Storage seguro para anexos.
- Dominio real apontado e certificado renovavel.
- Monitoramento de erros e disponibilidade.
- Politica formal de retencao e exclusao de dados LGPD.
