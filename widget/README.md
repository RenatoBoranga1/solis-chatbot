# Widget embutivel Solis

Inclua no site:

```html
<script
  src="/widget/solis-widget.js"
  data-api-base="https://api.seu-dominio.com"
  data-brand-name="Solar Soluções"
></script>
```

O widget envia mensagens para `POST /chat/message` com `channel=site`. Para producao, hospede este arquivo com HTTPS, CORS restrito e versao de cache.
