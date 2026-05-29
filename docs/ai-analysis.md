# Análise Inteligente

A Análise Inteligente transforma conversas, leads e chamados em uma leitura estratégica para a equipe da Solar Soluções. Ela ajuda o atendente a entender rapidamente o contexto, priorizar casos críticos e responder com mais segurança.

## O que a análise gera

- resumo executivo;
- intenção principal;
- sentimento do cliente;
- nível de urgência;
- oportunidade comercial;
- chance de conversão;
- risco técnico;
- dados faltantes;
- próxima ação recomendada;
- resposta sugerida ao cliente;
- tags estratégicas;
- score de prioridade, lead ou risco.

## Endpoints

```text
POST /ai/conversations/{conversation_id}/analyze
GET /ai/conversations/{conversation_id}/analysis
POST /ai/leads/{lead_id}/analyze
GET /ai/leads/{lead_id}/analysis
POST /ai/tickets/{ticket_id}/analyze
GET /ai/tickets/{ticket_id}/analysis
POST /ai/conversations/{conversation_id}/suggest-reply
GET /ai/dashboard/insights
```

Todos os endpoints exigem usuário interno autenticado. Perfis aceitos: `admin`, `comercial`, `suporte`, `tecnico` e `gestor`.

## Variáveis

```env
ENABLE_GENERATIVE_AI=false
OPENAI_API_KEY=
AI_PROVIDER=openai
AI_MODEL=gpt-4.1-mini
```

Com `ENABLE_GENERATIVE_AI=false` ou sem `OPENAI_API_KEY`, a análise usa regras locais. Isso mantém a funcionalidade ativa sem custo externo e sem depender de rede.

Com `ENABLE_GENERATIVE_AI=true`, `AI_PROVIDER=openai` e uma chave válida, o serviço tenta gerar análise com IA generativa. Se houver erro, timeout ou resposta inválida, o fallback por regras é usado automaticamente.

## Fallback por regras

O fallback calcula:

- lead quente quando há conta média, cidade, tipo de imóvel, distribuidora, interesse em financiamento e conta de energia;
- ticket crítico quando há cheiro de queimado, faísca, fumaça, choque, disjuntor desarmando, sistema parado ou cliente irritado;
- urgência alta quando a conversa já está com gravidade alta ou handoff;
- dados faltantes conforme o fluxo de orçamento ou suporte.

## Uso no painel

No painel administrativo:

- conversas mostram resumo, sentimento, urgência, risco, dados faltantes, próxima ação e resposta sugerida;
- leads mostram score de conversão e etiqueta frio, morno ou quente;
- chamados mostram score de risco e etiqueta baixo, médio, alto ou crítico;
- dashboard mostra leads quentes, chamados críticos, clientes irritados, oportunidades de financiamento, problemas recorrentes e recomendações de gestão.

As respostas sugeridas são apoio para o atendente. Elas devem ser revisadas antes do envio ao cliente.

## LGPD e segurança

A análise mascara e minimiza dados sensíveis. Ela não deve:

- expor CPF/CNPJ completo;
- prometer preço, prazo, economia, garantia ou diagnóstico definitivo;
- orientar cliente a mexer em cabos, inversores, disjuntores ou painéis;
- substituir avaliação humana em risco elétrico.

Em casos de risco elétrico, a recomendação deve priorizar atendimento humano e orientação de segurança.

## Auditoria

Cada análise gerada cria:

- registro em `ai_analyses`;
- trilha em `audit_logs` com tipo da análise, entidade analisada, score e urgência.

Isso permite rastrear quando uma análise foi gerada e qual era o próximo passo recomendado.
