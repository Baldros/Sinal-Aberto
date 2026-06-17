# Sinal Aberto Technical Stack and Hosting

This document records stack decisions and infrastructure requirements, with
special focus on hosting the MCP server.

Updated: **2026-06-12**.

---

## Publication Model

Sinal Aberto should run as a **remote MCP server**. This means:

- **We host; platforms consume.** The project developer keeps the server online.
  ChatGPT and other MCP clients send HTTP requests to the configured endpoint.
- The MCP server is not automatically hosted by OpenAI. It behaves like a web
  API: the project is responsible for deployment, domain, logs, security, cost,
  and availability.
- When a user invokes a Sinal Aberto tool, the MCP client calls a public endpoint
  such as `https://yourdomain.com/mcp`.

```text
User -> ChatGPT / MCP client
              |
              v
        https://yourdomain.com/mcp
              |
              v
        Sinal Aberto MCP server
              |
              v
        Fogo Cruzado API / SQLite / lightweight cache
```

The Apps SDK documentation recommends exposing the local server through a tunnel
such as `ngrok` during development. For deployment, the server and any component
bundle should sit behind a stable HTTPS endpoint with low latency, reliable TLS,
logs, and metrics.

Relevant official sources:

- OpenAI Apps SDK - Deploy: https://developers.openai.com/apps-sdk/deploy
- OpenAI Apps SDK - Set up your server: https://developers.openai.com/apps-sdk/build/server
- Model Context Protocol: https://modelcontextprotocol.io/

---

## Target Stack

| Layer | Desired production stack | Free/cheap MVP | Rationale |
|---|---|---|---|
| Language | Python 3.12+ | Python or TypeScript | Python helps geoprocessing; TypeScript fits Cloudflare Workers and many serverless MCP examples. |
| MCP framework | FastMCP / MCP SDK | FastMCP, MCP SDK, or Worker MCP in TypeScript | Validate tools and MCP contract before locking the final stack. |
| Transport | Streamable HTTP | Streamable HTTP | Current remote transport for network-accessible MCP servers. |
| Database | PostgreSQL + PostGIS when scale justifies it | SQLite in Python MVP; D1 for Worker; external Postgres only when needed | The MVP can filter by time, city, neighborhood, bounding box, and approximate radius without PostGIS. |
| Cache | Redis / Valkey when scale justifies it | Memory, SQLite table, Cloudflare KV, or platform cache | The MVP must reduce pressure on external APIs but does not need dedicated Redis at the start. |
| HTTP client | httpx | httpx / fetch | Async queries, explicit timeout, and configurable retry. |
| Authentication | OAuth 2.1 when needed | No user login in the MVP if possible | Prefer public/aggregate data and avoid precise user location at first. |
| Observability | Logs, metrics, alerts | Basic platform logs | Essential for debugging MCP calls and integration failures. |

### Practical Decision

For **production or scale**, the ideal stack remains:

```text
Python + FastMCP
PostgreSQL + PostGIS
Redis / Valkey
PaaS or VPS deployment
HTTPS + logs + metrics
```

For a **free MVP**, keep the stack lighter:

```text
Python + FastMCP
SQLite with WAL
Short cache in memory or SQLite
No user login
Direct authorized external API calls
Free-tier HTTPS deployment
```

Rule: **validate usefulness and safety before paying the operational cost of
heavier infrastructure**.

### MVP Decision: SQLite First

The current decision is to start the MVP with **SQLite** in the Python backend.
This reduces external services, exposed ports, database credentials, monthly
cost, and deployment complexity.

SQLite is sufficient for the first slice if the system:

- runs as a single MCP instance;
- has few simultaneous writes;
- ingests Fogo Cruzado data periodically or on demand;
- keeps a small or moderate history;
- uses indexes by city, state, date, latitude, and longitude;
- filters by bounding box before calculating real distance in Python;
- calculates scores and clusters in code, storing aggregate results for reuse.

The MVP should avoid recalculating heavy clusters for every question. The
preferred approach is to precompute or cache recent clusters and answer MCP
tools from normalized data.

PostgreSQL/PostGIS becomes an evolution trigger when there are:

- multiple instances writing to the same database;
- high write volume;
- broad history;
- frequent polygon, buffer, intersection, and spatial-join queries;
- a public dashboard with higher concurrency;
- operational needs for backup, replicas, permissions, and stronger migrations.

Redis/Valkey is also not an initial requirement. It enters when memory or SQLite
cache is no longer enough, especially with multiple instances or shared rate
limiting.

---

## Can GitHub Host the MCP Server?

**GitHub alone should not host the MCP server.**

GitHub is excellent for:

- versioning code;
- documenting the project;
- running CI/CD;
- publishing documentation or a static landing page with GitHub Pages;
- hosting simple static assets.

But **GitHub Pages is static hosting**. It publishes HTML, CSS, and JavaScript,
but it does not run a permanent Python/Node backend process or expose a dynamic
MCP endpoint.

GitHub Pages is also not intended as free hosting for a SaaS or commercial
service. The documentation describes limits such as published sites up to 1 GB
and a soft limit of 100 GB/month bandwidth.

Official sources:

- GitHub Pages - What is GitHub Pages: https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages
- GitHub Pages limits: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits

**Conclusion:** use GitHub for repository and documentation; use another service
for the MCP backend.

---

## Free Hosting for the MVP

### Main MVP Recommendation

The best free route depends on the MVP shape:

| Scenario | Best free option | Why |
|---|---|---|
| Lightweight Python MVP with SQLite | **Render Free Web Service** | Runs Python/FastMCP directly, easy GitHub deploy, TLS, and logs. Has cold starts and ephemeral filesystem, so persistence needs care. |
| Lightweight stateless MCP without heavy Python | **Cloudflare Workers** | Generous free tier, automatic HTTPS, low latency, good fit for serverless HTTP. |
| Personal Next.js/API-routes MVP | **Vercel Hobby** | Good for frontend and short APIs. Watch duration limits and non-commercial scope. |
| Free Postgres/PostGIS for a later phase | **Neon Free** | Free serverless Postgres with extension support such as PostGIS, good for small/intermittent data when SQLite is not enough. |
| Static site / landing page | **GitHub Pages, Cloudflare Pages, or Vercel** | Free and sufficient for docs, marketing, and a public page. |

---

### Option A - Cloudflare Workers

**Assessment:** best free option for a lightweight MCP MVP.

Cloudflare Workers is a good choice when the MCP server:

- is stateless;
- calls external HTTP APIs;
- uses simple cache;
- does not need heavy Python/geospatial libraries;
- does not need complex long-lived connections;
- can be implemented in TypeScript/JavaScript.

Strengths:

- Automatic HTTPS.
- Global low latency.
- Free tier with 100,000 requests per day.
- Good for testing simple MCP tools.
- Cloudflare KV can act as lightweight cache.

Limitations for Sinal Aberto:

- Not the best platform for heavy Python geospatial logic.
- D1 is managed SQLite in the Cloudflare ecosystem, but it is not the same flow
  as a local SQLite file in Python.
- If clustering requires PostGIS, the database should live outside the Worker,
  such as Neon, Supabase, or another Postgres.
- Free-plan CPU limits may be tight for heavy processing.

Official source:

- Cloudflare Workers pricing: https://developers.cloudflare.com/workers/platform/pricing/

**Use when:** the initial MVP is stateless, avoids heavy Python libraries, and
focuses on querying data, applying simple rules, and returning explainable
responses.

---

### Option B - Render Free Web Service

**Assessment:** best free option for a traditional Python MVP.

Render Free can run web services in Node.js, Python, Rails, and similar stacks.
It is simple for FastMCP/FastAPI and GitHub deployment.

Strengths:

- Runs Python more naturally than Workers.
- Easy deploy from GitHub.
- Managed TLS and public domain.
- Accessible logs.
- Can use SQLite inside the app for development and small prototypes.

Important limitations:

- Free service sleeps after 15 minutes without traffic.
- Waking after a new request can take about 1 minute.
- Filesystem is ephemeral.
- Free Render Postgres expires after 30 days.
- Not for production.
- If SQLite persistence must survive deploys/restarts, use persistent volume,
  external database, or another platform.

Official source:

- Render Free instances: https://render.com/docs/free

**Use when:** validating Python MCP tools and the SQLite architecture without
continuous-availability commitments.

---

### Option C - Vercel Hobby

**Assessment:** good for a personal MVP with frontend and short APIs; less ideal
for a persistent Python MCP server.

Strengths:

- Excellent for landing pages, Next.js, and web components.
- Free tier for personal projects.
- 1,000,000 function invocations included in Hobby.
- Very simple GitHub deploy.

Limitations:

- Hobby is aimed at personal, non-commercial use.
- Functions have limited duration: 10s default and configurable up to 60s on Hobby.
- Not ideal for long streaming, heavy processing, or a traditional Python server.

Official source:

- Vercel Hobby Plan: https://vercel.com/docs/plans/hobby

**Use when:** building the site, frontend, app UI, or a very small short-lived API.

---

### Option D - Neon Free for Database

**Assessment:** good free option for serverless Postgres once the MVP outgrows
SQLite.

Neon can be used as an external Postgres database while the MCP server runs on
Cloudflare Workers, Render, Vercel, or another host. In the current decision, it
is not required for the first MVP; it is a migration route when
Postgres/PostGIS solves a real problem.

Strengths:

- Free plan without card.
- 0.5 GB storage per project.
- 100 monthly CU-hours per project.
- Scale to zero when inactive.
- Extension support such as PostGIS.

Limitations:

- Free tier is suitable for development, demos, and prototypes, not high-availability production.
- Cold start can happen when compute scales to zero.
- Free size is small for broad occurrence history.

Official source:

- Neon pricing: https://neon.com/pricing

---

### Option E - Railway Free / Trial

**Assessment:** good developer experience and migration path to paid hosting,
but the free/trial model is limited for an always-on backend.

Strengths:

- Simple deploy through GitHub.
- Natural backend-service support.
- Database and services in one project.
- Smooth upgrade path to a paid plan.

Limitations:

- Free/trial resources are small for an always-on backend.
- A minimally stable service likely moves to Hobby at about US$5/month.

Official source:

- Railway pricing plans: https://docs.railway.com/pricing/plans

---

## Recommended MVP Combinations

### Recommended Lightweight Python MVP

```text
Python + FastMCP
SQLite with WAL
In-memory short cache
Render Free or Railway Trial for early tests
ngrok for local ChatGPT Developer Mode
```

Use this when the priority is validating product behavior in Python and keeping
the future PostGIS path open.

### Free Serverless MVP

```text
TypeScript MCP server
Cloudflare Workers
Cloudflare KV / D1 for lightweight cache
External API calls to Fogo Cruzado
```

Use this when zero cost and low latency matter more than Python/geospatial
libraries.

### Better Path to Cheap Production

```text
Python + FastMCP
Small VPS / paid Render / Railway Hobby
SQLite first
Neon Postgres/PostGIS when needed
Optional Redis/Valkey later
```

Use this when real users, uptime, or lower cold-start risk become important.

## Hosting Comparison

| Option | Best for | Main risk |
|---|---|---|
| GitHub Pages | Static docs/landing page | Cannot run MCP backend |
| Cloudflare Workers | Stateless serverless MCP | TypeScript/serverless constraints |
| Render Free | Python MCP prototype | Sleep, cold start, ephemeral filesystem |
| Vercel Hobby | Frontend and short APIs | Function duration and personal-use limits |
| Neon Free | External Postgres/PostGIS prototype | Cold start and small free storage |
| Railway | Backend deployment with easy upgrade | Free tier is limited for always-on use |

## Current Recommendation

1. **Local development:** Python + FastMCP + SQLite + `ngrok` to test in ChatGPT Developer Mode.
2. **Lightweight Python MVP:** Python/FastMCP + SQLite + short cache, hosted on Render, Railway, or a cheap VPS depending on persistence needs.
3. **Free serverless MVP:** Cloudflare Workers + KV/D1 if the goal is zero cost and simple TypeScript logic.
4. **First stable deploy:** Railway Hobby, paid Render, or cheap VPS once there are real users, uptime needs, and less tolerance for cold starts.
5. **Production or scale:** persistent Postgres/PostGIS, Redis/Valkey when needed, logs, metrics, custom domain, privacy policy, and security review.

## Directory Publication

### ChatGPT App Directory

1. Build the MCP server with a public HTTPS endpoint.
2. Test in Developer Mode.
3. Ensure `/mcp` responds with low latency and supports the expected transport.
4. Configure app metadata, permissions, and security.
5. Serve a public privacy policy.
6. Submit for review once the service is stable.

### Other MCP Clients

Other clients can use the same server as long as:

- the transport is compatible;
- authentication is supported;
- tools are described clearly;
- the server does not expose dangerous actions or sensitive data.

## Sinal Aberto-Specific Care

- Do not store precise user location without clear need.
- Avoid answers that help users evade operations, locate agents, or make dangerous tactical decisions.
- Show sources, query time, limitations, and confidence level.
- Use cache to reduce instability and pressure on external sources.
- Log enough for debugging, without collecting unnecessary sensitive personal data.
- Prefer region/neighborhood/cluster answers instead of sensitive real-time coordinates.

## Executive Summary

1. **Python/FastMCP + SQLite** is best for validating the product with low complexity while keeping the logic in Python.
2. **Cloudflare Workers + KV/D1** is best for a lightweight, cheap serverless MVP if the implementation can be TypeScript/serverless.
3. **PostgreSQL/PostGIS and Redis** should be added only when measured needs justify their operational cost.
