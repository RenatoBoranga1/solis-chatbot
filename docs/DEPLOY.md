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

1. Escolher provedor: WhatsApp Cloud API, Z-API, Twilio, WATI, Take Blip ou Evolution API.
2. Criar endpoint adaptador para webhooks do provedor.
3. Validar assinatura/token do webhook.
4. Converter entrada para `POST /chat/message`.
5. Enviar a resposta do Solis de volta pelo provedor.

## Producao segura

- HTTPS obrigatorio.
- Rate limit em borda e API.
- WAF para painel administrativo.
- Backups automaticos criptografados.
- Logs sem dados sensiveis desnecessarios.
- Storage seguro para anexos.
- Monitoramento de erros e disponibilidade.
- Politica formal de retencao e exclusao de dados LGPD.
