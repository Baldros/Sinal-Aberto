# Stack técnica e hospedagem do Sinal Aberto

Este documento registra as decisões de stack do projeto e os requisitos de infraestrutura, com foco especial em hospedagem. As decisões foram validadas por pesquisa direta na documentação oficial da OpenAI, Anthropic, Cloudflare e na especificação do MCP (Model Context Protocol).

---

## O modelo de publicação

O Sinal Aberto é um **servidor MCP remoto**. Isso significa:

- **Você hospeda, as plataformas consomem.** O desenvolvedor do projeto mantém o servidor online. ChatGPT e Claude fazem requisições HTTP para o endpoint fornecido.
- Não existe hospedagem na infraestrutura da OpenAI ou Anthropic. O servidor é como qualquer API REST — você é responsável por uptime, segurança e custos.
- Quando um usuário do ChatGPT ou do Claude aciona uma ferramenta do Sinal Aberto, a plataforma faz um POST para `https://seudominio.com/mcp`, aguarda a resposta e repassa ao usuário.

```
Usuário → ChatGPT / Claude
              ↓  HTTP POST
        https://seudominio.com/mcp   ← você mantém isso online
              ↓
        Servidor MCP (Python)
              ↓
        Fogo Cruzado API / PostgreSQL
```

---

## Stack técnica

| Camada | Tecnologia | Justificativa |
|--------|-----------|---------------|
| Linguagem | Python 3.12+ | Ecossistema geoespacial maduro (shapely, scikit-learn, psycopg) |
| Framework MCP | **FastMCP 3.x** (`pip install fastmcp`) | Alto nível, ~1M downloads/dia, ~70% dos servidores MCP em produção; suporte nativo a Streamable HTTP e OAuth 2.1 |
| Transporte | **Streamable HTTP** | Único transporte remoto ativo na especificação (HTTP+SSE foi depreciado em março/2025) |
| Banco de dados | **PostgreSQL + PostGIS** | Queries geoespaciais (clustering DBSCAN, proximidade, buffers); necessário para os casos de uso centrais do projeto |
| Cache | **Redis** | TTL nas respostas da Fogo Cruzado API; reduz latência e pressão sobre a API externa |
| HTTP client | **httpx** | Assíncrono, suporta timeout e retry configuráveis |
| Autenticação | **OAuth 2.1 com PKCE** via `authlib` | Obrigatório para publicação nos diretórios do ChatGPT (Apps) e Claude (Connectors); PKCE é mandatório pela especificação MCP desde novembro/2025 |

### Por que não o SDK oficial `mcp`?

O FastMCP 1.0 foi absorvido pelo SDK oficial (`pip install mcp`). O projeto standalone evoluiu para FastMCP 2.x/3.x, mantido separadamente em [gofastmcp.com](https://gofastmcp.com). A versão standalone oferece API de alto nível, suporte a OAuth 2.1 nativo e HTTP deployment mais simples. Para um servidor de produção, o FastMCP standalone é a escolha mais pragmática.

### Por que não Cloudflare Workers?

Cloudflare Workers é a plataforma mais citada para servidores MCP e tem excelente suporte a Streamable HTTP. Porém, para este projeto:

- **PostGIS não está disponível** no D1 (banco SQLite do Workers)
- O suporte a Python no Workers é recente e mais limitado
- As ferramentas de scaffolding OAuth (workers-oauth-provider) são TypeScript-first

Para um projeto com requisitos geoespaciais sérios, uma plataforma com PostgreSQL completo é mais adequada.

---

## Transporte: Streamable HTTP

O protocolo MCP define dois transportes oficiais:

| Transporte | Uso | Status |
|-----------|-----|--------|
| **stdio** | Local: servidor é subprocesso do cliente | Ativo — apenas para uso local (Claude Desktop, Claude Code) |
| **Streamable HTTP** | Remoto: servidor acessível via rede | **Padrão atual** (spec 2025-03-26) |
| HTTP+SSE | Remoto: modelo antigo com dois endpoints | **Depreciado** desde março/2025 |

Streamable HTTP usa um único endpoint que aceita POST e GET. O servidor pode responder com JSON simples (request/response) ou abrir um stream SSE por requisição. Funciona naturalmente com load balancers, API gateways e infraestrutura serverless — ao contrário do modelo SSE antigo, que exigia sessão persistente e sticky sessions.

O endpoint do servidor segue a convenção: `https://seudominio.com/mcp`.

---

## Autenticação: OAuth 2.1

Para publicação nos diretórios públicos, OAuth 2.1 é obrigatório. A especificação MCP trata o servidor MCP como um **OAuth Resource Server**.

**Endpoints obrigatórios:**
- `/.well-known/oauth-authorization-server` — discovery (RFC 8414)
- `/.well-known/oauth-protected-resource` — resource metadata (RFC 9728)
- `/oauth/authorize`
- `/oauth/token`
- `/oauth/register` — Dynamic Client Registration (DCR), exigido pelo Claude

**Particularidades por plataforma:**
- **ChatGPT**: usa CIMD (Client ID Metadata Document) — envia uma URL como `client_id`; o servidor valida o documento. Suporta também DCR e clientes pré-configurados.
- **Claude**: exige DCR; o cliente se registra automaticamente na primeira conexão.
- **Callback OAuth do Claude**: `https://claude.ai/api/mcp/auth_callback`

**Implementação:** `authlib` cobre o essencial. Alternativamente, Auth0 ou Stytch delegam a complexidade para um serviço externo.

---

## Hospedagem

### O problema com hospedagem compartilhada tradicional

Hostinger, Locaweb e similares servem PHP e arquivos estáticos. Um servidor MCP é um **processo Python persistente** — precisa de uma plataforma que execute processos de longa duração. Hospedagem compartilhada não funciona para este caso.

---

### Opções recomendadas

#### Opção A — VPS (melhor custo-benefício a longo prazo)

Uma máquina virtual onde você controla tudo. Sobe o servidor MCP e um site profissional no mesmo host.

| Provedor | Plano | Custo | Specs |
|---------|-------|-------|-------|
| **Hetzner** | CX22 | ~€4/mês (~R$25) | 2 vCPU, 4 GB RAM, 40 GB SSD |
| **DigitalOcean** | Basic Droplet | $6/mês | 1 vCPU, 1 GB RAM |
| **Oracle Cloud** | Always Free | **R$0** | 2 VMs ARM, 1 GB RAM cada |

No VPS você gerencia o servidor (nginx, Docker, systemd), mas tem liberdade total para rodar PostgreSQL + Redis + servidor MCP + site no mesmo host.

**Oracle Cloud Free Tier** é uma opção real para começar sem custo, mas exige mais familiaridade com Linux e configuração de servidor.

---

#### Opção B — Railway (melhor para simplicidade)

PaaS gerenciado. Deploy via git push, PostgreSQL incluso, sem gerenciar servidor.

- **Plano Hobby**: $5/mês (~R$30)
- Múltiplos serviços no mesmo projeto (MCP server + site na mesma conta)
- PostgreSQL gerenciado incluso no plano
- Redis disponível como add-on
- TLS automático, domínio customizado incluso

É a opção mais rápida para ir do zero ao deploy sem experiência em DevOps.

---

#### Opção C — Híbrido (site estático + MCP separado)

Separa as responsabilidades:

| Serviço | Plataforma | Custo |
|---------|-----------|-------|
| Site profissional (portfólio, landing page) | **Cloudflare Pages** | Gratuito |
| Servidor MCP | **Railway** $5/mês | ~R$30 |

Funciona bem se o site for estático (HTML/CSS/JS, Next.js export, Astro, etc.). O site fica em CDN global sem custo; o MCP server fica num serviço dedicado.

---

### Comparativo

| Opção | Custo/mês | Gerenciamento | Site junto? | PostgreSQL |
|-------|-----------|---------------|-------------|-----------|
| Oracle Cloud Free | R$0 | Alto (você gerencia tudo) | Sim | Você instala |
| Hetzner VPS | ~R$25 | Alto | Sim | Você instala |
| Railway Hobby | ~R$30 | Baixo | Sim (como serviço) | Gerenciado |
| Cloudflare Pages + Railway | ~R$30 | Baixo | Site separado | Gerenciado |

**Recomendação para começar:** Railway Hobby ($5/mês) ou o híbrido Cloudflare Pages + Railway. Simples, PostgreSQL gerenciado, sem overhead de DevOps. Se o projeto crescer e os custos começarem a pesar, migrar para um VPS Hetzner é direto.

---

## Publicação nos diretórios

### ChatGPT App Directory

1. Construir o servidor MCP com endpoint HTTPS público
2. Criar o App no painel do ChatGPT (Settings → Apps → Create)
3. Testar em Developer Mode
4. Verificar propriedade de domínio (OpenAI fornece um token para servir na raiz do domínio)
5. Submeter para revisão via dashboard — OpenAI revisa manualmente
6. Após aprovação, o App aparece no ChatGPT App Directory para usuários Pro, Team, Enterprise e Edu

Para uso via **Responses API** (acesso programático), nenhum registro é necessário — basta passar o `server_url` diretamente na chamada da API.

### Claude Connectors Directory

1. Endpoint HTTPS público com suporte a Streamable HTTP
2. Adicionar como conector customizado em Claude.ai (Settings → Connectors) — disponível instantaneamente para sua org
3. Para publicação pública: submeter via painel admin do Claude.ai (requer conta Team ou Enterprise, papel de Owner/Primary Owner)
4. Anthropic revisa e aprova; servidor aparece no diretório em [claude.com/connectors](https://claude.com/connectors)

Requisitos adicionais para o diretório Claude: política de privacidade pública, conta de teste com dados de exemplo, 3+ prompts de exemplo funcionando, anotações de ferramentas (somente leitura vs. destrutiva).

---

## Resumo executivo

O Sinal Aberto é um servidor HTTP público que você hospeda e mantém. As plataformas de IA (ChatGPT, Claude) fazem requisições para ele quando usuários acionam as ferramentas. O servidor precisa de Python, PostgreSQL, Redis e um endpoint HTTPS com OAuth 2.1. Para começar, Railway ($5/mês) é a opção mais simples — PostgreSQL gerenciado incluso, deploy por git push, sem gerenciar servidor. Se quiser hospedar um site profissional junto, o mesmo plano comporta os dois serviços.
