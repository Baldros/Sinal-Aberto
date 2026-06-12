# Stack técnica e hospedagem do Sinal Aberto

Este documento registra as decisões de stack do projeto e os requisitos de infraestrutura, com foco especial em hospedagem do servidor MCP.

Atualizado em: **2026-06-12**.

---

## O modelo de publicação

O Sinal Aberto deve funcionar como um **servidor MCP remoto**. Isso significa:

- **Você hospeda, as plataformas consomem.** O desenvolvedor do projeto mantém o servidor online. ChatGPT e outros clientes MCP fazem requisições HTTP para o endpoint fornecido.
- O servidor MCP não é hospedado automaticamente pela OpenAI. Ele é parecido com uma API web: você é responsável por deploy, domínio, logs, segurança, custos e disponibilidade.
- Quando um usuário aciona uma ferramenta do Sinal Aberto, o cliente MCP faz uma requisição para um endpoint público, normalmente algo como `https://seudominio.com/mcp`.

```text
Usuário -> ChatGPT / cliente MCP
              |
              v
        https://seudominio.com/mcp
              |
              v
        Servidor MCP do Sinal Aberto
              |
              v
        Fogo Cruzado API / SQLite / cache leve
```

A documentação oficial do Apps SDK recomenda que, em desenvolvimento local, o servidor seja exposto com túnel como `ngrok`; para deploy, o servidor e o bundle do componente devem ficar atrás de um endpoint HTTPS estável, com baixa latência, TLS confiável, logs e métricas.

Fontes oficiais relevantes:

- OpenAI Apps SDK - Deploy: https://developers.openai.com/apps-sdk/deploy
- OpenAI Apps SDK - Set up your server: https://developers.openai.com/apps-sdk/build/server
- Model Context Protocol: https://modelcontextprotocol.io/

---

## Stack técnica pretendida

| Camada | Produção desejada | MVP gratuito / barato | Justificativa |
|--------|-------------------|-----------------------|---------------|
| Linguagem | Python 3.12+ | Python ou TypeScript | Python favorece geoprocessamento; TypeScript favorece Cloudflare Workers e exemplos de MCP serverless. |
| Framework MCP | FastMCP / SDK MCP | FastMCP, SDK MCP ou Worker MCP em TypeScript | Para MVP, o objetivo é validar ferramentas e contrato MCP antes de fechar a stack final. |
| Transporte | Streamable HTTP | Streamable HTTP | Transporte remoto atual para servidores MCP acessíveis via rede. |
| Banco de dados | PostgreSQL + PostGIS, quando a escala justificar | SQLite no MVP Python; D1 se for Worker; Postgres externo só se necessário | O MVP pode filtrar por tempo, cidade, bairro, bounding box e raio aproximado sem PostGIS. PostGIS entra quando houver geoprocessamento complexo ou concorrência maior. |
| Cache | Redis / Valkey, quando a escala justificar | Memória, tabela SQLite, Cloudflare KV ou cache da plataforma | O MVP precisa reduzir pressão sobre APIs externas, mas não precisa começar com Redis dedicado. |
| HTTP client | httpx | httpx / fetch | Consultas assíncronas, timeout e retry configuráveis. |
| Autenticação | OAuth 2.1 quando necessário | Sem login no MVP, se possível | Para o primeiro MVP, priorizar dados públicos/agregados e evitar localização precisa do usuário. |
| Observabilidade | Logs, métricas, alertas | Logs básicos da plataforma | Essencial para depurar chamadas MCP e falhas de integração. |

### Decisão prática

Para **produção ou escala**, a stack ideal continua sendo:

```text
Python + FastMCP
PostgreSQL + PostGIS
Redis / Valkey
Deploy em PaaS ou VPS
HTTPS + logs + métricas
```

Para **MVP gratuito**, a stack deve ser mais leve:

```text
Python + FastMCP
SQLite com WAL
Cache curto em memória ou SQLite
Sem login de usuário
Consulta direta à API externa autorizada
Deploy em free tier com HTTPS
```

A regra é: **validar utilidade e segurança antes de pagar o custo operacional de infraestrutura pesada**.

### Decisão de MVP: SQLite primeiro

A decisão atual é iniciar o MVP com **SQLite** no backend Python. Essa escolha reduz serviços externos, portas expostas, credenciais de banco, custo mensal e complexidade de deploy.

SQLite é suficiente para o primeiro recorte se o sistema:

- rodar como uma única instância MCP;
- tiver poucas escritas simultâneas;
- fizer ingestão periódica ou sob demanda da API do Fogo Cruzado;
- mantiver um histórico pequeno ou moderado;
- usar índices por cidade, estado, data, latitude e longitude;
- filtrar por bounding box antes de calcular distância real no Python;
- calcular score e clusters no código, salvando resultados agregados para reutilização.

O MVP deve evitar recalcular clusters pesados a cada pergunta. A abordagem preferida é pré-calcular ou cachear clusters recentes e responder as ferramentas MCP a partir de dados já normalizados.

PostgreSQL/PostGIS deixa de ser requisito inicial e vira gatilho de evolução quando houver:

- múltiplas instâncias escrevendo no mesmo banco;
- alto volume de escritas;
- histórico grande;
- consultas frequentes por polígonos, buffers, interseções e joins espaciais;
- dashboard público com maior concorrência;
- necessidade operacional de backup, réplicas, permissões e migrações mais robustas.

Redis/Valkey também não é requisito inicial. Ele entra quando cache em memória ou SQLite deixar de ser suficiente, especialmente se houver várias instâncias ou necessidade de rate limiting compartilhado.

---

## GitHub pode hospedar o MCP?

**GitHub sozinho não deve ser usado para hospedar o servidor MCP.**

GitHub é excelente para:

- versionar o código;
- documentar o projeto;
- rodar CI/CD;
- publicar documentação ou landing page estática com GitHub Pages;
- hospedar assets estáticos simples.

Mas **GitHub Pages é hospedagem estática**. Ele publica HTML, CSS e JavaScript, mas não executa um processo backend Python/Node permanente nem expõe um endpoint MCP dinâmico.

GitHub Pages também não é indicado como hospedagem gratuita de SaaS ou serviço comercial. A própria documentação descreve limites como site publicado de até 1 GB e soft limit de 100 GB/mês de banda.

Fontes oficiais:

- GitHub Pages - What is GitHub Pages: https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages
- GitHub Pages limits: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits

**Conclusão:** usar GitHub para o repositório e documentação; usar outro serviço para o backend MCP.

---

## Hospedagem gratuita para MVP

### Recomendação principal para MVP

A melhor rota gratuita depende do tipo de MVP:

| Cenário | Melhor opção gratuita | Por quê |
|--------|------------------------|---------|
| MVP Python leve com SQLite | **Render Free Web Service** | Roda Python/FastMCP diretamente, deploy fácil via GitHub, TLS e logs. Tem cold start e filesystem efêmero, então exige cuidado com persistência. |
| MCP leve, stateless, sem Python pesado | **Cloudflare Workers** | Free tier generoso, HTTPS automático, baixa latência, bom encaixe com serverless HTTP. |
| MVP pessoal em Next.js/API routes | **Vercel Hobby** | Bom para frontend e APIs curtas. Atenção a limites de duração e uso não comercial. |
| Banco Postgres/PostGIS grátis para fase posterior | **Neon Free** | Postgres serverless grátis, suporta extensões como PostGIS, bom para dados pequenos/intermitentes quando SQLite não bastar. |
| Site estático / landing page | **GitHub Pages, Cloudflare Pages ou Vercel** | Gratuito e suficiente para documentação, marketing e página pública. |

---

### Opção A — Cloudflare Workers

**Avaliação:** melhor opção gratuita para um MVP MCP leve.

Cloudflare Workers é uma boa escolha quando o servidor MCP:

- é stateless;
- faz chamadas HTTP para APIs externas;
- usa cache simples;
- não precisa rodar bibliotecas Python/geoespaciais pesadas;
- não precisa manter conexão longa complexa;
- pode ser implementado em TypeScript/JavaScript.

Pontos fortes:

- HTTPS automático.
- Baixa latência global.
- Free tier com 100.000 requests por dia.
- Boa opção para testar ferramentas MCP simples.
- Cloudflare KV pode servir como cache leve.

Limitações para o Sinal Aberto:

- Não é a melhor plataforma para Python geoespacial pesado.
- D1 é SQLite gerenciado no ecossistema Cloudflare, mas não é o mesmo fluxo de um arquivo SQLite local em Python.
- Se a lógica de clustering exigir PostGIS, o banco deve ficar fora do Worker, por exemplo Neon, Supabase ou outro Postgres.
- O limite de CPU do plano gratuito pode ser apertado para processamento pesado.

Fonte oficial:

- Cloudflare Workers pricing: https://developers.cloudflare.com/workers/platform/pricing/

**Quando usar:** MVP inicial stateless, sem bibliotecas Python pesadas, focado em consultar dados, aplicar regras simples e retornar respostas explicáveis.

---

### Opção B — Render Free Web Service

**Avaliação:** melhor opção gratuita para MVP em Python tradicional.

Render Free permite rodar web services em Node.js, Python, Rails etc. É simples para começar com FastMCP/FastAPI e deploy via GitHub.

Pontos fortes:

- Roda Python de forma mais natural do que Workers.
- Deploy simples a partir do GitHub.
- TLS gerenciado e domínio público.
- Logs acessíveis.
- Pode usar SQLite no próprio app para desenvolvimento e protótipos pequenos.

Limitações importantes:

- O serviço gratuito dorme após 15 minutos sem tráfego.
- Ao receber nova requisição, pode levar cerca de 1 minuto para acordar.
- O filesystem é efêmero.
- Render Postgres gratuito expira após 30 dias.
- Não deve ser usado para produção.
- Se a persistência SQLite precisar sobreviver a deploys/restarts, será necessário volume persistente, banco externo ou outra plataforma.

Fonte oficial:

- Render Free instances: https://render.com/docs/free

**Quando usar:** MVP em Python para validar tools MCP e arquitetura SQLite, sem compromisso de disponibilidade contínua.

---

### Opção C — Vercel Hobby

**Avaliação:** boa opção para MVP pessoal com frontend e APIs curtas; menos ideal para servidor MCP Python persistente.

Pontos fortes:

- Excelente para landing page, Next.js e componentes web.
- Free tier para projetos pessoais.
- 1.000.000 de function invocations incluídas no Hobby.
- Deploy via GitHub muito simples.

Limitações:

- O plano Hobby é voltado a uso pessoal e não comercial.
- Funções têm duração limitada: default de 10s e configurável até 60s no Hobby.
- Não é a melhor escolha se o MCP precisar de streaming longo, processamento pesado ou servidor Python tradicional.

Fonte oficial:

- Vercel Hobby Plan: https://vercel.com/docs/plans/hobby

**Quando usar:** site, frontend, UI do app ou API muito simples e curta.

---

### Opção D — Neon Free para banco

**Avaliação:** boa opção gratuita para Postgres serverless quando o MVP superar SQLite.

Neon pode ser usado como banco Postgres externo enquanto o MCP roda em Cloudflare Workers, Render, Vercel ou outro host. Na decisão atual, ele não é requisito para o primeiro MVP; é uma rota de migração quando Postgres/PostGIS passar a resolver um problema real.

Pontos fortes:

- Plano gratuito sem cartão.
- 0,5 GB de storage por projeto.
- 100 CU-hours mensais por projeto.
- Scale to zero quando inativo.
- Suporte a extensões como PostGIS.

Limitações:

- O free tier é adequado para desenvolvimento, demos e protótipos, não para alta disponibilidade de produção.
- Pode haver cold start quando o compute escala para zero.
- O tamanho gratuito é pequeno para histórico amplo de ocorrências.

Fonte oficial:

- Neon pricing: https://neon.com/pricing

**Quando usar:** fase posterior com dados pequenos, consultas geoespaciais iniciais e necessidade real de Postgres/PostGIS sem custo mensal.

---

### Opção E — Railway Free / Trial

**Avaliação:** bom developer experience, mas o gratuito é limitado.

Railway continua sendo uma opção confortável para deploy de app + banco, mas o plano gratuito atual é pequeno: a documentação lista o Free como $0/mês, com $1 de crédito grátis por mês. O Hobby custa $5/mês.

Pontos fortes:

- Deploy simples via GitHub.
- Suporte natural a serviços backend.
- Banco e serviços no mesmo projeto.
- Boa experiência para migrar para plano pago.

Limitações:

- O free tier é pouco para um backend sempre ligado.
- Para algo minimamente estável, provavelmente entra no Hobby de $5/mês.

Fonte oficial:

- Railway pricing plans: https://docs.railway.com/pricing/plans

**Quando usar:** se a prioridade for simplicidade e houver abertura para migrar rapidamente para $5/mês.

---

## Combinações recomendadas para MVP

### MVP Python leve recomendado

```text
GitHub
  -> repositório e documentação

Render Free Web Service, Railway Hobby ou VPS barato
  -> servidor MCP em Python/FastMCP
  -> SQLite com WAL
  -> cache em memória ou tabela SQLite

Volume persistente ou backup periódico
  -> necessário se o SQLite virar fonte persistente relevante

GitHub Pages / Cloudflare Pages
  -> landing page e documentação pública
```

**Por que essa combinação:** menor número de serviços, menos segredos, menor superfície operacional e caminho mais direto para validar o produto em Python.

**Trade-off:** SQLite depende de disco persistente se os dados não puderem ser reconstruídos. Em free tiers com filesystem efêmero, o banco deve ser reconstruível a partir das fontes externas ou migrado para volume/banco externo.

---

### MVP serverless gratuito

```text
GitHub
  -> repositório

Cloudflare Workers
  -> servidor MCP leve em TypeScript
  -> cache simples em KV, D1 ou memória

Neon Free, Supabase Free ou D1
  -> apenas se houver necessidade de persistência gerenciada
```

**Por que essa combinação:** custo zero, HTTPS automático e boa latência para um MCP simples.

**Trade-off:** exige adaptar a implementação para TypeScript/serverless ou manter a lógica Python fora do Worker.

---

### MVP com melhor caminho para produção barata

```text
GitHub
  -> repositório

Railway Hobby ou Render pago básico
  -> servidor MCP Python
  -> SQLite com volume persistente no começo
  -> Postgres/PostGIS e Redis/Key Value se necessário

Cloudflare Pages ou Vercel
  -> site estático / UI pública
```

**Por que essa combinação:** menor atrito operacional e migração simples para produção.

**Trade-off:** deixa de ser gratuito; custo inicial típico entre US$5 e US$10/mês.

---

## Comparativo de hospedagem

| Opção | Custo inicial | Serve para MCP? | Python fácil? | PostGIS? | Principal limitação |
|------|---------------|-----------------|---------------|----------|--------------------|
| GitHub Pages | R$0 | Não | Não | Não | Apenas estático. |
| Cloudflare Workers | R$0 | Sim, para MVP leve | Limitado | Não local | CPU curta e runtime serverless. |
| Render Free | R$0 | Sim | Sim | Via externo, se necessário | Dorme após 15 min; cold start; filesystem efêmero. |
| Vercel Hobby | R$0 | Parcial | Limitado | Via externo | Funções curtas e uso pessoal/não comercial. |
| Neon Free | R$0 | Não hospeda MCP | N/A | Sim | Banco pequeno e serverless; usar quando SQLite não bastar. |
| Railway Free | R$0, crédito baixo | Sim, mas limitado | Sim | Via Postgres | $1/mês de crédito é pouco. |
| Railway Hobby | US$5/mês | Sim | Sim | Via Postgres | Não é gratuito. |
| VPS barato | ~US$4-6/mês | Sim | Sim | Sim, instalado por você | Mais DevOps. |

---

## Recomendação atual

Para o Sinal Aberto, a recomendação atual é:

1. **Desenvolvimento local:** Python + FastMCP + SQLite + `ngrok` para testar no ChatGPT Developer Mode.
2. **MVP Python leve:** Python/FastMCP + SQLite + cache curto, hospedado em Render, Railway ou VPS barato conforme necessidade de persistência.
3. **MVP serverless gratuito:** Cloudflare Workers + KV/D1 se o objetivo for custo zero e lógica simples em TypeScript.
4. **Primeiro deploy estável:** Railway Hobby, Render pago ou VPS barato quando houver usuários reais, necessidade de uptime e menos cold start.
5. **Produção ou escala:** Postgres/PostGIS persistente, Redis/Valkey se necessário, logs, métricas, domínio próprio, política de privacidade e revisão de segurança.

**Decisão para agora:** começar gratuito é possível. A escolha mais pragmática é:

```text
MVP Python leve: Python/FastMCP + SQLite
MVP serverless gratuito: Cloudflare Workers + KV/D1
Site/docs: GitHub Pages ou Cloudflare Pages
```

Se o MVP confirmar valor, migrar para PaaS pago barato ou VPS. Postgres/PostGIS deve entrar quando houver demanda concreta de escala ou geoprocessamento avançado, não como dependência inicial.

---

## Publicação nos diretórios

### ChatGPT App Directory

1. Construir o servidor MCP com endpoint HTTPS público.
2. Testar em Developer Mode.
3. Garantir que o endpoint `/mcp` responde com baixa latência e suporte ao transporte esperado.
4. Configurar metadados, permissões e segurança do app.
5. Servir política de privacidade pública.
6. Submeter para revisão quando houver estabilidade.

Para desenvolvimento, túnel local como `ngrok` é suficiente. Para publicação, usar endpoint HTTPS estável; endpoint local ou temporário não deve ser tratado como produção.

### Outros clientes MCP

O mesmo servidor MCP pode ser consumido por outros clientes compatíveis, desde que:

- o transporte seja compatível;
- a autenticação seja suportada;
- as ferramentas sejam descritas de forma clara;
- o servidor não exponha ações perigosas ou dados sensíveis.

---

## Cuidados específicos do Sinal Aberto

Por lidar com segurança pública, o deploy deve considerar mais do que custo:

- Não armazenar localização precisa do usuário sem necessidade clara.
- Evitar respostas que ajudem a contornar operações, localizar agentes ou tomar decisões táticas perigosas.
- Mostrar fontes, horário de consulta, limitações e nível de confiança.
- Usar cache para reduzir instabilidade e pressão sobre fontes externas.
- Registrar logs suficientes para depuração, mas sem coletar dados pessoais sensíveis desnecessários.
- Preferir respostas por região/bairro/cluster, não coordenadas sensíveis em tempo real.

---

## Resumo executivo

O Sinal Aberto precisa de um **backend MCP hospedado em HTTPS**. GitHub é adequado para código, documentação e site estático, mas não para rodar o servidor MCP.

Para um **MVP gratuito**, há duas rotas boas:

1. **Python/FastMCP + SQLite**: melhor para validar o produto com baixa complexidade e manter a lógica em Python.
2. **Cloudflare Workers + KV/D1**: melhor para MVP serverless, leve e barato desde o início, se a implementação puder ser TypeScript/serverless.

Para produção ou escala, a stack pode evoluir para PostgreSQL/PostGIS persistente, Redis/Valkey, logs, métricas, domínio próprio e hospedagem sem cold start relevante.
