# Base de conhecimento multimídia

A base de conhecimento do Solis aceita texto oficial, vídeo e material de apoio. A ideia é que a equipe da Solar Soluções cadastre respostas confiáveis e, quando for seguro, complemente com um vídeo oficial ou link útil.

## Campos disponíveis

- `title`: título interno do artigo.
- `question`: pergunta ou situação principal.
- `answer`: resposta oficial escrita.
- `category`: categoria do conteúdo.
- `keywords`: palavras-chave para recuperação.
- `video_title`: título amigável do vídeo.
- `video_url`: link HTTPS do YouTube ou vídeo oficial.
- `resource_title`: título do material de apoio.
- `resource_url`: link HTTPS para PDF, manual, artigo ou página oficial.
- `resource_type`: `youtube`, `pdf`, `manual`, `artigo`, `site` ou `outro`.
- `send_video_with_answer`: envia o vídeo automaticamente junto com a resposta.
- `send_resource_with_answer`: envia o material automaticamente junto com a resposta.

## Links permitidos

O backend aceita apenas URLs com `https://`. Links com `javascript:`, `data:`, sem protocolo, com credenciais ou apontando para hosts locais são rejeitados.

Use preferencialmente:

- vídeos oficiais no YouTube da Solar Soluções;
- PDFs oficiais;
- manuais do fabricante;
- páginas oficiais da Solar Soluções;
- artigos técnicos aprovados pela equipe.

## Quando ativar envio automático

Ative `Enviar vídeo junto com a resposta` apenas quando:

- o vídeo é oficial ou aprovado pela Solar Soluções;
- o conteúdo é educativo e seguro;
- a orientação não incentiva o cliente a abrir equipamentos, mexer em cabos, quadros elétricos, disjuntores ou painéis;
- a equipe revisou a resposta no preview do painel.

Bons exemplos:

- limpeza preventiva das placas com alerta de segurança;
- uso do aplicativo de monitoramento;
- leitura de geração;
- explicação de créditos de energia;
- dúvidas gerais sobre economia.

## Cuidados técnicos

Para limpeza das placas, a resposta inclui alerta:

```text
Faça a limpeza apenas em condições seguras e, se houver risco de altura, telhado molhado ou dificuldade de acesso, solicite equipe especializada.
```

Para ligar ou desligar inversor, a resposta inclui alerta:

```text
Siga apenas orientações oficiais e não abra equipamentos, quadros elétricos ou cabos. Em caso de erro, cheiro de queimado, faísca ou choque, não mexa no equipamento e acione a equipe técnica.
```

Em risco elétrico, como cheiro de queimado, faísca, fumaça, choque, curto ou inversor queimado, o bot não sugere vídeo e encaminha para atendimento humano.

## Como aparece para o cliente

No WhatsApp, os links são enviados em texto simples:

```text
Vídeo recomendado:
Como limpar placas solares com segurança
https://youtu.be/...
```

No widget do site, links HTTPS ficam clicáveis. Links do YouTube aparecem em um card simples com botão "Assistir vídeo" e abrem em nova aba.

## Seed inicial

O seed inclui exemplos com placeholders seguros:

- limpeza das placas solares;
- aplicativo de monitoramento;
- ligar e desligar inversor com segurança.

Esses links devem ser substituídos pelos vídeos oficiais da Solar Soluções antes de ativar `send_video_with_answer`.
