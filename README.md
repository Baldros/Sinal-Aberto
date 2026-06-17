# Sinal Aberto

**Sinal Aberto** is a proposal for an urban-intelligence assistant that estimates,
probabilistically and transparently, recent signs of armed or police activity in
a region and the likely public impact.

The project starts with Brazilian cities that face severe public-safety
challenges, especially Rio de Janeiro. Its core premise is simple: residents,
workers, and people in transit need contextual, traceable, and responsible
information to better understand what may be happening around them.

> Sinal Aberto is not intended to be an absolute police-operation radar or an
> official emergency source. It interprets public data and recent signals to
> indicate evidence, uncertainty, and likely impact in near real time.

## Project Documents

- [OpenAI Apps SDK](docs/openai-apps-sdk.md): summary of the official OpenAI SDK concepts, useful links, and the path to turn Sinal Aberto into a ChatGPT app and open MCP server.
- [Technical stack and hosting](docs/stack-e-hospedagem.md): current decision to start with a lightweight Python/FastMCP + SQLite MVP while keeping PostgreSQL/PostGIS and Redis as the evolution path.
- [Data sources](docs/fontes-de-dados.md): prioritized sources, access patterns, and the product role of each dataset.
- [Fogo Cruzado API](docs/fogocruzado-api.md): official API v2 baseline, authentication, prioritized endpoints, and integration tests.
- [MCP tools](docs/ferramentas-mcp.md): proposed public MCP tools, descriptions, inputs, outputs, and implementation priority.
- [Secondary source validation](docs/validacao-fontes-secundarias.md): connection-tested formats, headers, and quirks of the eight auxiliary sources.
- [Auxiliary source integration](docs/integracao-fontes-auxiliares.md): data design (three data natures), the tiered integration plan, and current status.

## Implementation Status

A working MCP server already exists (Python + FastMCP, Streamable HTTP). It is
usable today and exposes three tools backed by four integrated sources, with
source attribution, timestamps, and limitations on every response.

**Tools**

- `get_recent_activity(city, region, time_window)` — recent armed/police activity
  with evidence and confidence levels, a recent-intensity operation profile
  (massacre flag, distinct police units, spatial concentration, recency), official
  IBGE territorial context, the ISP historical baseline, and COR.Rio corroboration.
- `resolve_location(name, uf)` — resolve a city name to official IBGE candidates to
  disambiguate before querying.
- `list_data_sources()` — source catalog and live health status.

**Integrated sources**

- Fogo Cruzado (primary, live) — recent shootings/gunfire occurrences.
- IBGE Localidades (live + long cache) — territorial normalization (Tier 1).
- ISP Dados RJ (offline prepared baseline) — chronic violence intensity, RJ (Tier 2).
- COR.Rio (live) — official security-bulletin corroboration, Rio city (Tier 3).

All enrichment is currently descriptive (Phase A): it never changes the evidence or
confidence of the live signal. The full data design and tiered plan live in
[Auxiliary source integration](docs/integracao-fontes-auxiliares.md).

**Not yet started**

- Phase B: let corroboration and the historical baseline influence confidence
  through explicit, testable probabilistic rules (more math/probability).
- Tier 4: GPS SPPO experimental mobility signal.
- Cluster tools, the probabilistic score, and an OpenAI/Claude app deployment.

## Running Locally

Put Fogo Cruzado credentials in a `.env` file at the repository root
(`FOGOCRUZADO_EMAIL` / `FOGOCRUZADO_PASSWORD`, or generic `user` / `password`).

```bash
# Run the MCP server (Streamable HTTP)
./.venv/Scripts/python.exe -m sinal_aberto.server

# Offline unit tests (no network)
./.venv/Scripts/python.exe -m pytest tests/unit -q

# Rebuild the ISP baseline data (offline job, ~monthly)
./.venv/Scripts/python.exe -m sinal_aberto.ingest.build_isp_baseline
```

## Product Vision

The initial idea is to build a ChatGPT app able to answer questions such as:

- Are there recent signs of a police operation or armed activity in a city area?
- Which areas have the strongest evidence of recent activity right now?
- What is the likely public-impact level?
- Which source produced the information, when was it updated, and with what confidence level?
- Does the event look isolated or part of a cluster of nearby occurrences in time and space?

Longer term, Sinal Aberto can evolve into an open public-utility layer available
not only in ChatGPT, but also in other chatbots, civic apps, public dashboards,
and MCP integrations.

## Core Thesis

The problem should not be treated deterministically.

Instead of claiming that an operation is or is not ongoing, Sinal Aberto should
estimate:

1. **Current activity probability**
   The likelihood that recent armed or police activity is still relevant in a
   region.

2. **Likely public impact**
   The practical effect for residents, workers, and people in transit.

3. **Confidence level**
   The robustness of the answer, based on source quality, recency, consistency
   of signals, and local history.

4. **Explainability**
   The answer should show which signals led to the classification: recency,
   concentration of records, victims, police presence, transport disruption,
   local history, and related factors.

## Example Response

> There is high evidence of recent armed or police activity in the Complexo do
> Alemao area. Nearby records were identified in the last 45 minutes, including
> indications of police action and agent presence. Estimated impact is high,
> mainly because of the temporal concentration of records and the area's history.
>
> Confidence: moderate.
> Limitation: the data indicates recent occurrences, but does not officially
> confirm that an operation is still ongoing.

## Proposed Metrics

### 1. Current Activity Probability

A metric for estimating whether a recent event may still be active or relevant.

Possible signals:

- Minutes since the latest occurrence.
- Number of nearby occurrences in the last hours.
- Occurrence marked as police action or police operation.
- Agent presence.
- Identified police unit.
- Geographic and temporal cluster.
- Area history for similar occurrences.
- Historical probability of continuity after the first record.

Conceptual example:

```text
activity_score =
  recency
+ recent_cluster
+ police_operation_indicator
+ agent_presence
+ local_history
+ complementary_sources
```

The output does not need to be displayed as an exact percentage. It can be
presented in bands:

- Low evidence.
- Moderate evidence.
- High evidence.
- Very high evidence.

### 2. Likely Impact

A separate metric for estimating the severity or intensity of public impact.

Possible signals:

- Injured victims.
- Deaths.
- Multiple nearby occurrences.
- Estimated cluster duration.
- Geographic spread.
- Transport interruption.
- High-circulation time of day.
- Local history of lethality or recurrence.
- Police-operation presence.

Possible bands:

- Low reported impact.
- Medium reported impact.
- High reported impact.
- Critical.

## Analysis Unit: Clusters

Sinal Aberto should avoid interpreting isolated occurrences too literally.

The main analysis unit should be the **active cluster**, meaning a group of
occurrences related by:

- geographic proximity;
- time window;
- neighborhood, community, or locality;
- event type;
- police presence;
- signs of continuity.

This allows more useful and less fragile answers than simply listing individual
events.

## Considered Data Sources

### Primary Source

#### Fogo Cruzado

- API site: https://api.fogocruzado.org.br/
- Documentation: https://api.fogocruzado.org.br/docs

Fogo Cruzado is the source most aligned with the initial Sinal Aberto proposal.
The API provides updated data on shootings and gunfire, including metropolitan
regions such as Rio de Janeiro, Recife, Bahia, and Para. The documentation says
the API includes last-update metadata and uses Brasilia time.

Relevant points:

- Armed-violence-focused dataset.
- Georeferenced occurrences.
- Near-real-time query potential.
- Data on shootings, gunfire, agent presence, police action/operation, victims,
  and other indicators.
- Requires prior authorization for API use.

### Complementary Sources

#### ISP Dados - Rio de Janeiro Public Security Institute

- Portal: https://www.ispdados.rj.gov.br/

Official source for criminal-record and police-activity datasets in Rio de
Janeiro state. Useful for history, context, statistical validation, and
territorial priors.

#### ISP Visualizacao / ISP Conecta

- Data visualization: https://www.ispvisualizacao.rj.gov.br/
- ISP Conecta: https://ispconecta.rj.gov.br/

Useful for dashboards, territorial context, and public analysis of safety
indicators.

#### SINESP / Ministry of Justice and Public Security

- Data portal: https://dados.mj.gov.br/dataset/sistema-nacional-de-estatisticas-de-seguranca-publica

National source for public-safety indicators. Useful for aggregate analysis,
territorial comparison, and historical context, but not as a primary real-time
source.

#### DATA.RIO

- Portal: https://www.data.rio/

Relevant source for urban layers, geographic datasets, neighborhoods,
territorial boundaries, public facilities, and geospatial enrichment.

#### Other Potential Sources

- Public-transport and traffic data.
- Official communications from public agencies.
- Verified journalism sources.
- Municipal occurrence, service, and urban-infrastructure datasets.
- Public reports, only with robust verification and rumor-control methodology.

## Product Principles

1. **Probabilistic, not deterministic**
   The system estimates evidence and probability without promising absolute
   confirmation.

2. **Explainable**
   Every answer should state the main factors behind the classification.

3. **Traceable**
   Every claim should indicate source, query time, and, when possible, data
   last-update time.

4. **Conservative by default**
   When uncertain, the system should reduce confidence instead of overstating
   certainty.

5. **Useful for ordinary residents**
   Language should be clear, direct, and contextual rather than technical jargon.

6. **Responsible and non-operational**
   The project must not help users evade operations, precisely locate agents, or
   make dangerous tactical decisions.

7. **Privacy by default**
   The system should avoid storing precise user location unless clearly needed.

## Assumed Limitations

- There is no guarantee of complete coverage of all police operations.
- Occurrences may enter the source with delay.
- A recent occurrence does not prove that an event is still active.
- Collaborative data may require later validation, correction, or updates.
- Official sources can have timing lag.
- Impact classification is an estimate, not an official confirmation.

## Target Architecture

### MVP Decision

The initial MVP should prioritize **safety, lightness, and low operating cost**.

Preferred starting architecture:

- MCP server in Python with FastMCP;
- simple local persistence with SQLite;
- short cache in memory or SQLite table;
- Fogo Cruzado API calls behind an isolated adapter;
- probabilistic score and initial clustering inside application code;
- no user login in the first version, if possible.

> Note: the storage approach was refined during implementation. The server is
> currently stateless with no runtime database — live sources use in-memory caches
> and the ISP history ships as a prepared read-only JSON artifact. Spatial
> concentration is computed with a formula (Haversine), which removed the need for
> a clustering database. See
> [Auxiliary source integration](docs/integracao-fontes-auxiliares.md) for the
> refined decision. SQLite is deferred until a feature genuinely needs SQL.

PostgreSQL/PostGIS and Redis remain the natural evolution path when complex
geospatial queries, more concurrency, broad history, a public dashboard, or
multiple writer instances become necessary.

### Phase 1: ChatGPT App

- Custom GPT or ChatGPT app.
- Integration with a dedicated backend.
- External-source queries through APIs.
- Natural-language responses with source, time, confidence, and explanation.

### Phase 2: Data Backend

- Proxy for Fogo Cruzado and complementary sources.
- Lightweight cache and update control.
- SQLite in the MVP, with a migration path to PostgreSQL/PostGIS.
- Geographic normalization.
- Initial cluster detection in application code.
- Current-activity probability calculation.
- Likely-impact calculation.
- Minimal logs and privacy policy.

### Phase 3: Open MCP

Sinal Aberto should evolve into an open MCP server so other chatbots and
assistants can query the same urban-intelligence layer.

MCP tools (implemented and proposed):

- `get_recent_activity(city, region, time_window)` — implemented.
- `resolve_location(name, uf)` — implemented (disambiguation helper).
- `list_data_sources()` — implemented.
- `get_active_clusters(city, time_window)` — proposed.
- `estimate_activity_probability(location, radius, time_window)` — proposed (Phase B).
- `estimate_public_impact(cluster_id)` — proposed (Phase B).
- `explain_assessment(cluster_id)` — proposed.

### Phase 4: Multiple Channels

- ChatGPT.
- Other MCP-compatible chatbots.
- Public API.
- Web dashboard.
- Integrations with journalistic, civic, and academic projects.

## Roadmap

Done:

- [x] Use the Fogo Cruzado API (authenticated adapter with caching).
- [x] Validate access patterns and the auxiliary sources (formats, headers, quirks).
- [x] Minimal Python/FastMCP backend for recent-occurrence queries.
- [x] Map relevant API fields into a safe, normalized response (no exact coordinates).
- [x] Territorial normalization to official IBGE codes (Tier 1).
- [x] Recent-intensity operation profile: spatial concentration, units, recency (Tier 2a).
- [x] Chronic historical baseline from ISP, via an offline ingestion job (Tier 2b).
- [x] COR.Rio official corroboration with anti-bias safeguards (Tier 3).
- [x] Explainable responses with source, time, and limitations.

Next:

- [ ] Phase B: probabilistic score — let corroboration and baseline shift confidence
      through explicit, testable rules (more math/probability).
- [ ] Tier 4: GPS SPPO experimental mobility signal.
- [ ] Cluster tools (`get_active_clusters`, `explain_assessment`).
- [ ] Deploy as an OpenAI/Claude app/connector.
- [ ] Privacy policy and disclaimers for public use.

Storage note: the initial "SQLite MVP" was refined to a stateless server with a
prepared read-only data file; SQLite is deferred until a feature needs SQL.

## Disclaimer

Sinal Aberto is a public-information tool proposal. It does not replace official
channels, emergency services, or guidance from competent authorities.

In immediate-risk situations, seek safe shelter and contact official emergency
channels.

## Status

Working MVP. A usable MCP server is implemented and tested (Python + FastMCP):
three tools over four integrated sources (Fogo Cruzado, IBGE, ISP, COR.Rio), with
source attribution, timestamps, and limitations on every response. All current
enrichment is descriptive (Phase A); the probabilistic score (Phase B) and a
public deployment are the next steps. See [Implementation Status](#implementation-status).
