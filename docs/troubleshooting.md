# Troubleshooting local

Use este guia quando o widget indicar API offline, modo demonstracao ou quando arquivos enviados pelo chat nao aparecerem no painel.

## Verificar backend

```powershell
docker compose ps -a
Invoke-RestMethod http://localhost:8000/health
docker compose logs backend --tail=120
```

O endpoint `/health` deve retornar algo neste formato:

```json
{
  "status": "ok",
  "service": "Solar Solucoes Solis",
  "environment": "development"
}
```

Se a chamada falhar, o widget nao consegue registrar atendimento real, leads, chamados ou uploads.

## Verificar frontend

```powershell
docker compose logs frontend --tail=80
```

No frontend Vite, use sempre `VITE_API_BASE_URL`. A variavel `API_BASE_URL` e do backend e nao e injetada automaticamente no navegador.

Valores locais recomendados:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_ENABLE_DEMO_FALLBACK=true
```

Em producao:

```env
VITE_API_BASE_URL=https://api.seu-dominio.com
VITE_ENABLE_DEMO_FALLBACK=false
```

## Modo demonstracao

Em desenvolvimento, o modo demonstracao existe apenas para demonstrar o fluxo quando a API esta offline. Ele mostra badge visivel e informa que as mensagens nao serao salvas no painel.

Em producao, deixe `VITE_ENABLE_DEMO_FALLBACK=false`. Se a API cair, o widget deve bloquear o envio fake e mostrar erro claro para o cliente.

## Upload bloqueado

O upload de conta de energia depende do backend online. Se o widget mostrar a mensagem abaixo, valide `/health` antes de tentar novamente:

```text
Para enviar conta de energia, o servidor precisa estar conectado. Verifique se o backend esta ativo.
```

## Reconectar

No widget, clique em `Tentar reconectar`. O bot chama `/health` novamente. Se voltar `status=ok`, o atendimento real e liberado.

## Reiniciar ambiente

```powershell
docker compose down
docker compose up --build
```

Depois abra:

```text
http://localhost:5173
```

## Checklist rapido

- [ ] Backend responde em `http://localhost:8000/health`.
- [ ] Frontend esta com `VITE_API_BASE_URL=http://localhost:8000`.
- [ ] `VITE_ENABLE_DEMO_FALLBACK=false` em producao.
- [ ] O painel `Diagnostico` mostra API online.
- [ ] Upload fica bloqueado quando a API esta offline.
- [ ] Atendimento real so e prometido quando a API esta online.
