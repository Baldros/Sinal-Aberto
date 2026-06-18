# Auxiliary Source Integration

Designed on: **2026-06-17**.

This document defines how Sinal Aberto should integrate the already validated
auxiliary sources (`docs/validacao-fontes-secundarias.md`) into the query MCP,
without betraying the product shape: it is a **text- and numeric-data-oriented
query tool**, not a map server or file server.

Today only Fogo Cruzado contributes data to responses. Auxiliary sources are
cataloged in `list_data_sources`, but most are marked as
`validated, not integrated`. This is the plan to close that gap incrementally
and safely.

## Central Principle

**Do not ingest artifacts into responses. Distill each source into compact text
and numeric facts, then expose those as small attributed fields that enrich the
JSON response.**

Direct consequences:

- The client agent never receives CSV, ZIP, GeoJSON, or shapefile content, and it
  never "talks to a database". It only calls a tool and receives JSON, as it does
  today. Internal storage (cache, file, database) is a private server detail.
- Heavy work, such as downloading and cleaning large files, never happens inside
  a user-query path.
- Every auxiliary fact is optional and carries its own source and timestamp.

### Source Input Is Not MCP Output

A recurring confusion: the **format published by the source** is not the
**format returned by Sinal Aberto**. They are opposite ends of the pipe.

```text
published source      our code              MCP response
(CSV/ZIP/JSON)   ->   clean and distill  ->  always JSON  ->  agent
their choice                                our choice
```

ISP publishes CSV, SINESP publishes ZIP/XLSX, and IBGE/COR.Rio already publish
JSON. We read each source in the format it offers and **always** return JSON.
The agent receives JSON in 100% of cases; CSV, when present, is only an internal
read detail.

## Functional Roles

An auxiliary source enters `get_recent_activity` only if it serves one of these
three roles:

| Role | Question it answers | Sources |
|---|---|---|
| **A. Normalize** | "Which official place/code is this?" | IBGE Localidades |
| **B. Baseline** | "Is this unusual here, or normal?" | ISP Dados RJ, SINESP/MJSP, population (IBGE/SIDRA) |
| **C. Corroborate** | "Does another official source mention something now?" | COR.Rio text, GPS SPPO as weak signal |

### Sources Excluded From This MCP Layer

Geographic/file-centered sources conflict with the text/numeric objective:

- **IBGE Malhas** (GeoJSON): pure geometry.
- **GTFS Rio** (static ZIP): transport geographic reference; Fogo Cruzado already
  provides `transport_interrupted`.
- **DATA.RIO ArcGIS**: geographic urban layers; reconsider only if a specific
  textual attribute proves necessary.

Excluding them here does not mean "never". It means serving geometry to an agent
that wants text and numbers is the wrong integration for this layer.

## Architecture: Three Data Natures, Three Mechanisms

Avoid forcing **one** mechanism onto **all** data. Each source has a nature, and
the mechanism should follow it. There is no "ETL + database for everything":
most sources are queried live, exactly as Fogo Cruzado is today.

| Nature | Change frequency | How to obtain | Offline job? | Database? | Freshness |
|---|---|---|---|---|---|
| **Critical live data** - Fogo Cruzado, COR.Rio, GPS SPPO | every minute/hour | live API + short TTL cache | no | no | always fresh |
| **Stable reference** - IBGE territory | almost never | live API + long cache | no | no | freshness is irrelevant |
| **Aggregate history** - ISP, SINESP | about monthly | file prepared by job | yes | optional | as fresh as the source |

Consequences:

- Offline preparation appears only for ISP/SINESP historical data.
- IBGE needs neither a job nor a database. It is an adapter with a long cache,
  like the city cache already kept by `FogoCruzadoClient`.
- Freshness is protected where it matters. Data where "being updated" is vital
  is always live. Only data that sources publish slowly becomes a prepared file.

### Why This Does Not Create Stale Data

Only aggregate historical data goes into a prepared file. ISP publishes
statistics about monthly; there is no fresher version to chase. If preparation
runs monthly, the project is as fresh as the source. Even occasional delay has
little effect because a 12-24 month baseline barely changes from one missing
month.

### What the Preparation Job Is

ETL means *Extract, Transform, Load*. Here it is just **a Python script we write**
under `sinal_aberto/ingest/` and run **outside the server**:

- **Who triggers it:** during development, a person manually. In production, a
  scheduler such as host cron, scheduled GitHub Action, or another controlled
  runner.
- **When it runs:** manually or on schedule, **never** when a user asks a
  question. If it ran per query, each question would download megabytes and
  parse CSV files.
- **What it produces:** small numeric reference rows such as
  `(3304557, "ISP", "gunfire", 2024, 3, 87.0)` instead of a multi-MB CSV.

```text
PREPARATION JOB (offline, about monthly)       MCP SERVER (online, per query)
person/scheduler triggers                      user/agent triggers
extract -> transform -> load  -------------->  read prepared result -> JSON response
slow and heavy is fine                          fast, light, read-only
```

## Storage: Start Without a Database, Add One When Needed

Persistence follows the data nature. SQLite is **delayed until something really
needs SQL**:

1. **Critical live data and stable references** -> per-instance memory cache.
   This is already how Fogo Cruzado works. No file, no database. Cache absorbs
   repeated requests and protects the source API. Shared cache such as Redis
   enters only after multiple instances and measured need.
2. **Aggregate history (ISP/SINESP)** -> file prepared by the job. The format can
   be packaged JSON for simplicity or SQLite when SQL queries become useful.
3. **SQLite actually enters** when the cluster layer arrives
   (`get_active_clusters`, `estimate_*` in `docs/ferramentas-mcp.md`), because it
   benefits from indexed queries and persisted computed state. Runtime can still
   be read-only: written by the job, read by the server, bundled into the
   deployment.

> If shared mutable state across instances becomes necessary later, Turso/libSQL
> provides managed cloud SQLite. That is a future problem, not a current need.

### Reference Schema for Prepared Data

When baseline and cluster storage exist, the reference storage should look like
this. It applies both to packaged JSON and SQLite tables; SQL is shown for
clarity.

```sql
-- Aggregate history from ISP/SINESP, prepared by the offline job.
CREATE TABLE monthly_baseline (
    ibge_city_code  INTEGER NOT NULL,     -- universal join key
    source          TEXT NOT NULL,         -- "ISP" | "SINESP"
    indicator       TEXT NOT NULL,         -- example: "gunfire"
    year            INTEGER NOT NULL,
    month           INTEGER,               -- NULL = annual aggregate
    value           REAL NOT NULL,
    unit            TEXT NOT NULL,         -- example: "occurrences"
    PRIMARY KEY (ibge_city_code, source, indicator, year, month)
);

-- Job traceability and idempotence.
CREATE TABLE ingestion_meta (
    source            TEXT NOT NULL,
    resource_id       TEXT NOT NULL,
    hash              TEXT,
    downloaded_at     TEXT NOT NULL,       -- ISO 8601 UTC
    metadata_modified TEXT,
    row_count         INTEGER,
    PRIMARY KEY (source, resource_id)
);
```

IBGE territory does not need a table. It comes live from the API and stays in
memory cache. Materialize it only if an offline fallback becomes valuable.

Baseline statistics, such as mean and dispersion per municipality/indicator over
12-24 months, can be calculated from `monthly_baseline` on demand. Materialize a
`baseline_stats` table only if cost appears.

## Universal Join Key: IBGE City Code

All historical/reference data joins through the **seven-digit IBGE city code**.
That is why territorial normalization (Tier 1) comes before everything else:
without it, ISP/SINESP/population cannot reliably match the city requested by
the user.

## Optional Enrichment Layer

`get_recent_activity` gains an enrichment step **after** the main Fogo Cruzado
query. Each enrichment is independent and failure-tolerant: if a source is down,
the field is null and a limitation is recorded. The main response never breaks.

```text
city/region
   -> resolve territory (Tier 1, live IBGE + cache)       -> territorial_context
   -> Fogo Cruzado (already present)                      -> recent_occurrences, evidence
   -> historical baseline (Tier 2, prepared file)         -> historical_baseline
   -> COR.Rio corroboration (Tier 3, live + cache)        -> corroborating_reports
   -> traffic anomaly (Tier 4, live, experimental)        -> experimental_signals
   -> build response + limitations + sources
```

## Data Model Direction

New Pydantic submodels should live in `sinal_aberto/models.py`. New fields in
`RecentActivityResult` should be **optional** by default to preserve
compatibility.

Suggested additions:

```python
class TerritorialContext(BaseModel):
    ibge_city_code: int | None = None
    resolved_name: str | None = None
    uf: str | None = None
    macro_region: str | None = None
    population: int | None = None
    match_quality: str


class HistoricalBaseline(BaseModel):
    source: str
    indicator: str
    window_months: int
    local_value: float | None = None
    local_average: float | None = None
    comparison: str | None = None


class CorroboratingReport(BaseModel):
    source: str
    title: str
    published_at: datetime | None = None
    url: str | None = None
    relevance: str
```

The current implementation already includes `TerritorialContext`.

## Tiered Integration Plan

### Tier 1 - IBGE Localidades

Goal: official territorial normalization.

Implementation:

- Add `IbgeLocalidadesClient` with a long in-memory catalog cache.
- Resolve city name and state to IBGE city code.
- Add `territorial_context` to `RecentActivityResult`.
- Add `IBGE Localidades` to `sources` when enrichment succeeds.
- Degrade gracefully when IBGE is unavailable.

This tier is already implemented.

### Tier 2 - Violence Intensity (decided 2026-06-17)

Goal: answer "is this area prohibitively intense / operation-prone?" with two
complementary lenses on different time scales. Both are descriptive (Phase A):
they never change `evidence_level` or `confidence_level`.

The product's core question is *"is there a police operation here, is it too
dangerous to leave home?"*. The live answer is Fogo Cruzado + COR.Rio; this tier
adds the *intensity/risk context* around it.

**2a - Fogo Cruzado recent intensity (no new infra).** Mine the live data we
already fetch but currently discard:

- `contextInfo.massacre` -> per-occurrence massacre flag (high severity).
- `contextInfo.policeUnit` -> count of *distinct* units in the window (a large,
  coordinated operation shows several units), never exposing the unit itself.
- `latitude`/`longitude` -> spatial concentration via the Haversine formula,
  computed in memory (no geospatial API, no clustering DB). Output is coarse
  (a level plus an approximate, rounded spread and the neighborhood label),
  never raw coordinates or a centroid. Because Fogo Cruzado approximates
  coordinates, "dispersed" is trustworthy but "concentrated" may be a geocoding
  artifact: tight clusters are reported with lower confidence.
- Recency decay: intensity "now" fades with the age of the most recent
  occurrence (we cannot know when an operation ends, only that staleness raises
  the chance it has subsided). Kept distinct from feed freshness (`x-last-update`).

Keep the deaths count as a single total (no civilian/agent split). Aggregated
spatial concentration via a formula removes the need for the heavy clustering /
SQLite tier for this goal.

**2b - ISP chronic baseline (offline job).** Characterize an area's structural
violence intensity, normalized and ranked across RJ municipalities:

- Primary lens: police lethality (`hom_por_interv_policial`), per 100k, percentile.
- Context / cross-check: violent lethality (`letalidade_violenta`), per 100k,
  percentile. High violence with near-zero recorded police lethality flags
  under-reporting; police lethality is treated as a floor, not the truth.
- Drop attempted homicide. No opaque single composite: two transparent axes, with
  an optional documented weighted level (e.g. 60% police / 40% violent) that
  always shows its components.
- Windows: typical = trailing 12 months (territorial control shifts faster than
  24 months in Rio); recent = 6 months for trend. The truly-recent signal comes
  from 2a, not here.
- Source: ISP `BaseDPEvolucaoMensalCisp.csv` (monthly, has `munic` and `ano/mes`,
  so it aggregates to municipality directly). Population for per-100k via SIDRA,
  offline, inside the job. Prepared file as packaged JSON (SQLite only if a later
  cluster layer needs SQL). ISP/RJ first; SINESP national later.
- Under-reporting near communities is a first-class limitation in the response.

Status: implemented. 2a (Fogo Cruzado recent intensity) and 2b (ISP offline
baseline) are live; the prepared file ships at `sinal_aberto/data/isp_baseline.json`,
rebuilt by `python -m sinal_aberto.ingest.build_isp_baseline`.

### Tier 3 - COR.Rio Corroboration

Goal: weak official-context corroboration.

Implementation:

- Query WordPress REST/RSS with browser-like headers.
- Cache recent results briefly.
- Match city/region terms conservatively.
- Add `corroborating_reports` only when relevance is clear.
- Never treat a text post as decisive evidence of an occurrence.

Status: implemented (Phase A). Anti-bias safeguards: a geographic gate (Rio city
only), a security-topic relevance filter (traffic/public-works bulletins are
rejected), and honest framing in the response (context, not confirmation).

### Tier 4 - GPS SPPO Experimental Signal

Goal: weak mobility anomaly context.

Implementation:

- Query only very short windows.
- Normalize coordinates and timestamps.
- Deduplicate samples.
- Use only aggregate anomalies, not raw vehicle positions.
- Keep this behind an experimental flag until quality is proven.

Status: not started (optional/experimental).

## Safety Rules

- Exact coordinates stay internal unless explicitly safe and necessary.
- Auxiliary facts must not raise certainty beyond what the evidence supports.
- If an enrichment source fails, return the main result and record a limitation.
- Every auxiliary field must have source attribution.
- Heavy downloads and parsing never run during user requests.
- Baseline data informs context, not operational advice.

## Current Status and Next Steps

As of 2026-06-17, Tiers 1, 2 (a and b), and 3 are implemented, all in **Phase A**
(descriptive enrichment: `territorial_context`, `operation_profile`,
`historical_baseline`, and `corroborating_reports` are added to responses, but none
of them changes `evidence_level` or `confidence_level`). A `resolve_location` tool
was added for disambiguation, and the agent-facing contract (enums, field
descriptions, instructions) was hardened so the calling model can act on the
fields. 126 offline unit tests pass.

### Phase B - probabilistic influence (next)

Phase B is where the accumulated context starts to **refine the assessment**, not
just describe it. Each rule must be explicit and unit-tested, like the current
`_assess`:

- COR.Rio corroboration in the same area/window raises `confidence_level` one step.
- The ISP baseline produces its own `relative_level` axis; it must not inflate
  `evidence_level`.
- The recency decay and spatial concentration feed the "is it still happening"
  estimate.
- The intent is to introduce more explicit probability/statistics (e.g. calibrated
  bands, priors from the chronic baseline) rather than the current heuristic bands.

### Other next steps

- Tier 4 (GPS SPPO) as a flagged experimental signal.
- Cluster tools (`get_active_clusters`, `explain_assessment`).
- Deployment as an OpenAI/Claude app/connector (stateless server, bundled data).
