# Roteiro E2E do Solis

Este roteiro valida o fluxo completo:

```text
Chatbot -> orcamento -> LGPD -> coleta de dados -> upload da conta de energia -> leitura inteligente/OCR -> tela Contas -> aplicacao ao lead -> recomendacao de kit -> geracao de proposta -> link seguro da proposta
```

Use este teste antes de demonstracoes comerciais, homologacao interna ou entrega para a Solar Solucoes.

## 1. Preparar ambiente

No PowerShell:

```powershell
cd C:\Users\USER\Documents\Playground\solar-solis-chatbot
docker compose down
docker compose up --build
```

Em outro PowerShell:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Resultado esperado:

```json
{
  "status": "ok",
  "service": "Solar Solucoes Solis",
  "environment": "development"
}
```

Abrir:

```text
http://localhost:5173
```

Credenciais seed de desenvolvimento:

```text
E-mail: admin@solarsolucoes.com.br
Senha: Solar@12345
```

Troque essa senha antes de qualquer ambiente compartilhado.

## 2. Teste de diagnostico

No painel administrativo, acessar a aba:

```text
Diagnostico
```

Validar:

- API Base URL exibida corretamente;
- API online;
- resposta do `/health`;
- ambiente `development`;
- fallback demo ativo/inativo;
- ultimo erro vazio ou controlado.

Resultado esperado: a aba Diagnostico deve indicar que a API esta online.

## 3. Teste do widget online

Abrir o widget no site local.

Verificar:

- nao deve aparecer `API offline`;
- nao deve aparecer `Modo demonstracao` se o backend estiver online;
- o botao `Quero um orcamento` deve iniciar atendimento real.

Mensagem inicial do cliente:

```text
Ola, quero fazer um orcamento de energia solar para minha casa.
```

Resultado esperado: o bot deve iniciar fluxo de orcamento e pedir consentimento LGPD antes de coletar dados pessoais.

## 4. Teste de LGPD

Responder:

```text
Sim, autorizo o uso dos meus dados para orcamento.
```

Resultado esperado: o bot deve continuar o atendimento e comecar a coletar dados uma pergunta por vez.

## 5. Teste de coleta de dados do cliente

Responder no fluxo, como cliente:

```text
Meu nome e Renato de Oliveira Boranga.
```

Depois:

```text
O imovel fica em Chavantes SP.
```

Depois:

```text
E uma residencia.
```

Depois:

```text
Minha conta media vem em torno de R$ 350,00.
```

Depois:

```text
Tenho a conta de energia em PDF.
```

Resultado esperado: o sistema deve manter a conversa real, sem cair em modo demonstracao, e deve criar ou preparar lead de orcamento.

## 6. Teste de upload da conta de energia

Enviar pelo widget um arquivo de conta de energia:

- PDF textual CPFL;
- ou imagem/foto da conta;
- ou PDF escaneado.

Resultado esperado no widget para PDF/texto:

```text
Recebi sua conta de energia. Vou analisar os principais dados para ajudar na simulacao do sistema solar. A equipe da Solar Solucoes revisara as informacoes antes da proposta final.
```

Resultado esperado no widget para imagem com OCR habilitado:

```text
Recebi a imagem da sua conta de energia. Vou tentar ler os dados automaticamente. A equipe revisara as informacoes antes da proposta final.
```

Resultado esperado de seguranca: o upload nao pode ser permitido se a API estiver offline.

## 7. Teste da tela Contas de energia

Acessar no painel:

```text
Contas de energia
```

Clicar em:

```text
Atualizar
```

Validar que aparece uma nova conta com:

- origem: `chatbot`;
- status: `processing`, `extracted` ou `needs_review`;
- distribuidora;
- cliente;
- consumo atual;
- consumo medio;
- meses detectados;
- valor da conta, se encontrado;
- confianca;
- metodo de extracao;
- OCR usado, se aplicavel.

Resultado esperado: a conta enviada no widget deve aparecer na tela Contas.

## 8. Teste do parser CPFL

Se a conta for CPFL, validar:

- nao usar endereco da CPFL como endereco do cliente;
- nao usar Jaguariuna do cabecalho como cidade do cliente, exceto se for realmente o cliente;
- extrair nome do cliente, se presente;
- extrair endereco do cliente, se presente;
- extrair bairro, CEP, cidade e UF, se presentes;
- classificar `Bandeira Verde` como `tariff_flag`;
- nao usar `Verde` como unidade consumidora;
- extrair historico de consumo, se presente;
- calcular media de consumo pelo historico.

Resultado esperado: campos duvidosos devem ficar vazios/null e entrar em revisao. O sistema nao pode preencher dados por chute.

## 9. Teste de historico e media

Na conta processada, verificar:

- `months_detected`;
- `average_source`;
- `average_consumption_kwh`;
- historico mensal.

Resultado esperado quando houver historico de 12 meses:

```text
average_source = history_12_months
months_detected >= 12
average_consumption_kwh calculado pela media do historico
```

Resultado esperado quando houver historico parcial:

```text
average_source = history_partial
```

Resultado esperado quando nao houver historico:

```text
average_source = current_consumption_only
```

## 10. Teste de revisao humana

Se a conta tiver campos faltando, validar que aparecem motivos de revisao:

- Valor da conta nao encontrado;
- Cidade/endereco precisa de revisao;
- Unidade consumidora nao identificada com seguranca;
- confianca abaixo de 80%.

Resultado esperado: o sistema deve exigir revisao antes de aplicar ao lead quando houver pendencias criticas.

## 11. Teste de aplicacao ao lead

Na tela Contas, revisar os dados.

Se necessario, corrigir manualmente:

- consumo medio;
- valor medio;
- cidade;
- UF;
- unidade consumidora;
- endereco;
- CEP.

Depois clicar em:

```text
Confirmar dados
```

Depois:

```text
Aplicar ao lead
```

Resultado esperado: os dados da conta devem ser aplicados ao lead sem erro.

O lead deve receber:

- nome;
- cidade;
- UF;
- consumo medio;
- valor medio;
- distribuidora;
- unidade;
- endereco;
- CEP;
- meses detectados;
- origem da media.

## 12. Teste de recomendacao de kit

A partir do lead, gerar ou simular proposta.

Validar:

- sistema usa `average_consumption_kwh` se disponivel;
- se nao houver consumo medio, usa conta media;
- kit recomendado aparece;
- motivo de selecao do kit aparece;
- proposta fica como rascunho;
- proposta nao e enviada automaticamente.

Exemplo esperado:

```text
Conta media: R$ 350,00
Consumo medio extraido: aproximadamente X kWh/mes
Kit recomendado: Kit Solar compativel com a faixa de consumo
Status: rascunho
```

## 13. Teste de geracao da proposta

Gerar proposta a partir do lead.

Validar:

- proposta criada;
- cliente vinculado;
- kit recomendado exibido;
- itens da proposta criados;
- valores editaveis;
- observacoes preenchidas;
- status `draft`;
- PDF gerado.

Resultado esperado: a proposta deve ser criada como rascunho para revisao humana.

## 14. Teste do link seguro

Na proposta, criar link seguro.

Validar:

- link gerado;
- token nao previsivel;
- link tem expiracao;
- link pode ser copiado;
- pagina publica abre em `/proposta/{token}`;
- PDF pode ser baixado;
- resposta do cliente pode ser registrada.

Resultado esperado: a proposta publica deve abrir corretamente e permitir aceite, recusa, interesse ou solicitacao de ajuste.

## 15. Teste do modo offline

Parar o backend:

```powershell
docker compose stop backend
```

Voltar ao widget e tentar enviar uma mensagem.

Resultado esperado:

- widget deve mostrar `API offline`;
- nao deve prometer atendimento real;
- se demo fallback estiver ativo, deve mostrar badge `Modo demonstracao`;
- se demo fallback estiver desativado, deve bloquear envio fake;
- upload de arquivo deve ficar bloqueado.

Depois religar:

```powershell
docker compose start backend
```

Clicar no botao:

```text
Tentar reconectar
```

Resultado esperado: widget deve voltar ao atendimento real.

## 16. Teste de logs

Rodar:

```powershell
docker compose logs backend --tail=120
docker compose logs frontend --tail=80
```

Validar:

- sem erro 500;
- sem erro de CORS;
- sem erro de banco;
- sem erro de coluna faltando;
- sem erro de upload;
- sem erro de OCR nao tratado;
- sem erro de `NUL (0x00)`.

## 17. Checklist de resultado

- [ ] Backend responde `/health`;
- [ ] Frontend abre em `localhost:5173`;
- [ ] Diagnostico mostra API online;
- [ ] Widget nao cai em modo demonstracao com backend online;
- [ ] LGPD e solicitada;
- [ ] Dados do cliente sao coletados;
- [ ] Upload da conta funciona;
- [ ] Conta aparece em Contas de energia;
- [ ] Parser CPFL separa cliente e distribuidora;
- [ ] Historico e extraido;
- [ ] Media e calculada;
- [ ] Lead e atualizado;
- [ ] Kit e recomendado;
- [ ] Proposta e criada;
- [ ] PDF e gerado;
- [ ] Link seguro abre;
- [ ] Modo offline e exibido corretamente.

## 18. Automacao parcial

O roteiro manual continua obrigatorio para validar a experiencia visual, upload real e decisao humana. Para automatizar a parte repetitiva, rode:

```powershell
.\scripts\e2e-smoke.ps1
```

Esse script:

- sobe o Docker Compose em background;
- valida `/health`;
- valida que o frontend responde em `localhost:5173`;
- roda testes automatizados do backend no container;
- gera SQL de migrations com Alembic;
- roda testes estaticos do frontend no container.

Cobertura automatizada ja existente:

- `/health`;
- parse de texto CPFL;
- upload de conta por endpoint sem erro 500;
- criacao de extracao a partir de anexo do chatbot;
- processamento de extracao pendente;
- confirmacao da extracao;
- aplicacao ao lead;
- geracao de proposta com selecao de kit por consumo medio;
- configuracao de `VITE_API_BASE_URL`;
- healthcheck do widget;
- bloqueio/aviso de modo offline e demo fallback.

## 19. Validacoes finais

Rodar no backend:

```powershell
python -m compileall app tests
python -m unittest discover tests
python -m alembic upgrade head --sql
```

Rodar no frontend:

```powershell
npm test
npm run build
```

Com Docker:

```powershell
docker compose down
docker compose up -d --build
docker compose ps -a
Invoke-RestMethod http://localhost:8000/health
```

## Riscos pendentes

- OCR de imagem e PDF escaneado depende de qualidade do arquivo, idioma e disponibilidade do Tesseract.
- Midia WhatsApp ainda precisa de download privado da Meta para leitura automatica completa de contas enviadas pelo WhatsApp.
- Proposta deve permanecer como rascunho e passar por revisao humana antes de envio real.
- Links de proposta e PDFs devem usar storage privado em producao.
- A senha seed `Solar@12345` nunca deve ser usada em ambiente compartilhado ou de producao.
