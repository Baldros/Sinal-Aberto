# Sinal Aberto MCP Tools

Updated: **2026-06-12**.

This document describes the initial public MCP tool proposal for Sinal Aberto.
The tools should expose product capabilities, not internal Fogo Cruzado API
details.

Endpoints such as `GET /states`, `GET /cities`, and `GET /occurrences` should
remain encapsulated in the internal data adapter. MCP responses should be
oriented around context, confidence, source attribution, timestamps, and
limitations.

## Principles

- Return evidence and uncertainty, not absolute claims.
- Avoid sensitive operational precision.
- Prefer neighborhood, region, and cluster labels over exact coordinates in final responses.
- Always include source, query time, and, when available, source update time.
- Reduce confidence when data is scarce, old, or inconsistent.
- Do not suggest routes, detours, evasion, agent approach, or tactical decisions.

## Proposed Tools

The initial contract should expose **6 public tools**:

1. `get_recent_activity`
2. `get_active_clusters`
3. `estimate_activity_probability`
4. `estimate_public_impact`
5. `explain_assessment`
6. `list_data_sources`

> Implementation status (2026-06-17): `get_recent_activity` and `list_data_sources`
> are implemented, plus `resolve_location` (a disambiguation helper not in the
> original list). `get_active_clusters`, `estimate_activity_probability`,
> `estimate_public_impact`, and `explain_assessment` remain proposed; the
> probability/impact tools belong to Phase B. `get_recent_activity` already returns
> the territorial context, recent-intensity operation profile, ISP historical
> baseline, and COR.Rio corroboration described across the other documents.

## 1. `get_recent_activity`

Queries recent signs of armed or police activity in a city, neighborhood, or
region.

### Input

```text
city: string
region: string | null
time_window: string
```

Example `time_window` values:

```text
30m
1h
3h
6h
24h
```

### Output

```text
city
region
time_window
query_time
source_update_time
activity_summary
evidence_level
confidence_level
territorial_context
recent_occurrences[]
limitations[]
sources[]
```

### Description

This is the simplest MVP tool. It queries recent data, normalizes records, and
returns a traceable summary of the signals found.

It should include:

- recent occurrence count;
- recency of the newest occurrence;
- involved neighborhoods/localities;
- police-action signal;
- agent-presence signal;
- reported victims;
- affected transport;
- source and update time;
- optional official IBGE territorial context.

## 2. `get_active_clusters`

Lists recent clusters in a city within a time window.

### Input

```text
city: string
time_window: string
```

### Output

```text
city
time_window
query_time
clusters[]
sources[]
limitations[]
```

Each `clusters[]` item should contain:

```text
cluster_id
region_label
first_occurrence_time
last_occurrence_time
occurrence_count
approximate_area
evidence_level
impact_level
confidence_level
main_signals[]
```

### Description

Groups occurrences by temporal and geographic proximity to avoid answers that
overweight isolated records.

In the MVP, clustering can run in application code and be stored in SQLite to
avoid recalculating every query.

## 3. `estimate_activity_probability`

Estimates the probability band for recent armed or police activity in a region.

### Input

```text
location: string
radius: number | null
time_window: string
```

`location` should accept a neighborhood, region, or locality. Latitude/longitude
may be supported internally, but the public response should avoid sensitive
precision.

### Output

```text
location
radius
time_window
query_time
activity_probability_level
confidence_level
supporting_evidence[]
main_factors[]
limitations[]
sources[]
```

### Suggested Bands

```text
low evidence
moderate evidence
high evidence
very high evidence
```

### Description

Calculates a probabilistic classification based on recency, concentration of
occurrences, police action, agent presence, local history, and complementary
signals.

The output must not promise that an operation is ongoing. It should express
recent evidence and uncertainty.

## 4. `estimate_public_impact`

Estimates the likely public impact of a specific cluster.

### Input

```text
cluster_id: string
```

### Output

```text
cluster_id
impact_level
confidence_level
impact_summary
victim_signals
transport_signals
temporal_spread
geographic_spread
main_factors[]
limitations[]
sources[]
```

### Suggested Bands

```text
low reported impact
medium reported impact
high reported impact
critical
```

### Description

Separates public severity from current-activity probability. A cluster may have
strong evidence of recent activity and low reported impact, or the reverse.

It should consider:

- injured victims;
- deaths;
- multiple nearby occurrences;
- transport interruption;
- approximate duration;
- geographic spread;
- police-operation presence.

## 5. `explain_assessment`

Explains the classification assigned to a cluster.

### Input

```text
cluster_id: string
```

### Output

```text
cluster_id
assessment_summary
activity_probability_level
impact_level
confidence_level
positive_signals[]
negative_or_uncertain_signals[]
data_freshness
sources[]
limitations[]
```

### Description

Provides explainability for users and client models. It should show which
signals support the assessment and which factors reduce confidence.

Example signals:

- very recent occurrence;
- multiple nearby records;
- police action marked;
- agent presence;
- reported victims;
- interrupted transport;
- lack of official continuity confirmation;
- old or scarce data.

## 6. `list_data_sources`

Lists the data sources used by the system and their operational status.

### Input

```text
none
```

### Output

```text
sources[]
query_time
limitations[]
```

Each `sources[]` item should contain:

```text
name
role
access_type
status
coverage
last_query_time
last_update_time
known_limitations[]
```

### Description

Keeps traceability and transparency visible. The first version should list Fogo
Cruzado as the primary source, IBGE Localidades as integrated territorial
normalization, and ISP Dados, SINESP, IBGE Malhas, DATA.RIO, and transport
sources as planned or partially integrated according to the real system state.

## Implementation Priority

### Initial MVP

1. `list_data_sources`
2. `get_recent_activity`
3. `get_active_clusters`

### MVP With Initial Scoring

4. `estimate_activity_probability`
5. `estimate_public_impact`

### Explainable MVP

6. `explain_assessment`

## Implementation Note

The tools that use `cluster_id` depend on clustering and local persistence.
Before them, the backend must:

- authenticate against the Fogo Cruzado API;
- query states, cities, and occurrences;
- normalize occurrences into SQLite;
- store source and update metadata;
- calculate recent clusters;
- calculate initial activity and impact scores.
