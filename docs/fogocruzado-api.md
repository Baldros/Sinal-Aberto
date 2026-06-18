# Fogo Cruzado API

Updated: **2026-06-12**.

This document summarizes the official Fogo Cruzado API v2 documentation for the
Sinal Aberto implementation. Treat the API as a critical external integration:
every access path needs authentication, timeouts, error handling, short caching,
and source-metadata recording.

Official references:

- Introduction: https://api.fogocruzado.org.br/docs
- Authentication: https://api.fogocruzado.org.br/docs/auth
- Endpoints: https://api.fogocruzado.org.br/docs/endpoint
- States: https://api.fogocruzado.org.br/docs/endpoint/states
- Cities: https://api.fogocruzado.org.br/docs/endpoint/cities
- Occurrences: https://api.fogocruzado.org.br/docs/endpoint/occurrences

## API Base

The official v2.0 documentation uses this base URL:

```text
https://api-service.fogocruzado.org.br/api/v2
```

The endpoint page documents three data endpoints:

- `GET /states`
- `GET /cities`
- `GET /occurrences`

The authentication page documents:

- `POST /auth/login`
- `POST /auth/refresh`

## Territorial Coverage and Time

According to the official introduction, the API provides updated data about
shootings and gunfire in metropolitan regions monitored by Fogo Cruzado,
including Rio de Janeiro, Recife, Bahia, and Para, with different historical
start dates by region.

The documentation also states that:

- returned dates and times should be interpreted in Brasilia time (`America/Sao_Paulo`, UTC-3);
- the API returns last-update metadata in HTTP headers;
- `X-Last-Update` indicates the latest general occurrence update;
- `X-Last-Update-State` indicates the state-specific latest update when applicable.

Persist these headers with queried data for traceability and cache control.

## Authentication

### `POST /auth/login`

Purpose: obtain a JWT access token.

Request:

```json
{
  "email": "your@email",
  "password": "your password"
}
```

Expected response:

- HTTP `201`;
- `code: 201`;
- `data.accessToken`;
- `data.expiresIn`, in seconds.

Send the returned token to other endpoints as a bearer token:

```text
Authorization: Bearer <accessToken>
```

### `POST /auth/refresh`

Purpose: refresh a token before expiration.

Request:

- method `POST`;
- header `Authorization: Bearer <accessToken>` with a still-valid token;
- in practical API validation on 2026-06-12, the token also had to be sent in
  the body as `{"accessToken": "<accessToken>"}`. Implement the client with
  this body to match observed behavior.

Expected response:

- HTTP `201`;
- `code: 201`;
- new `data.accessToken`;
- new `data.expiresIn`.

### Implementation Rules

- Never log email, password, or token values.
- Load credentials only from environment variables or a secret manager.
- Refresh the token before `expiresIn` when possible.
- On `401` or expired token, try refresh once; if that fails, perform a new login.
- On repeated authentication failures, return a controlled error to the MCP
  layer without leaking sensitive details.

## Data Endpoints

All data endpoints must be called with a bearer token.

### `GET /states`

Purpose: list monitored states.

Documented parameters: none.

Expected response:

```text
msg
msgCode
code
data[]
```

Each `data` item should contain at least:

```text
id
name
```

Sinal Aberto usage:

- discover `idState` for occurrence calls;
- keep a local table of monitored states;
- relate cache and metadata by state.

### `GET /cities`

Purpose: list monitored cities.

Documented filters:

```text
cityId
cityName
stateId
```

Expected response:

```text
msg
msgCode
code
data[]
```

Each `data` item should contain at least:

```text
id
name
state.id
state.name
```

Sinal Aberto usage:

- map city names to `id`;
- filter occurrences by city;
- build a local cache of cities and states;
- avoid ambiguity in name-based queries.

### `GET /occurrences`

Purpose: query occurrences. This is the main MVP endpoint.

Filters and parameters documented in official examples:

```text
order
page
take
idState
idCities
initialdate
finaldate
typeOccurrence
```

Practical notes:

- `idState` appears in official examples and was required during local
  validation. Treat `idState` as required in the MVP.
- `idCities` may appear repeatedly in the query string to filter multiple cities.
- `initialdate` and `finaldate` use `YYYY-MM-DD` in official examples.
- `order` should be treated as temporal ordering; use `DESC` for recent queries.
- `page` and `take` control pagination.

Expected response:

```text
msg
msgCode
code
pageMeta
data[]
```

`pageMeta` should contain:

```text
page
take
itemCount
pageCount
hasPreviousPage
hasNextPage
```

Each `data` item represents an occurrence and may contain:

```text
id
documentNumber
state
city
neighborhood
subNeighborhood
locality
latitude
longitude
date
policeAction
agentPresence
contextInfo
transports
victims
animalVictims
```

High-priority fields for Sinal Aberto:

- `date`: occurrence recency;
- `latitude` and `longitude`: spatial grouping, kept out of public responses when sensitive;
- `state`, `city`, `neighborhood`, `subNeighborhood`, `locality`: territorial normalization;
- `policeAction`: police-action signal;
- `agentPresence`: agent-presence signal;
- `contextInfo.mainReason`: main reason;
- `contextInfo.complementaryReasons`: complementary reasons;
- `contextInfo.clippings`: relevant clippings;
- `contextInfo.massacre`: critical-occurrence signal;
- `contextInfo.policeUnit`: involved police unit, when provided;
- `transports`: transport impact;
- `victims`: human victims;
- `animalVictims`: animal victims.

## `contextInfo` Structure

`contextInfo` should be treated as the main semantic container for the
occurrence. In observed responses it can include:

```text
mainReason
complementaryReasons
clippings
massacre
policeUnit
```

Use these fields carefully:

- `mainReason` and `complementaryReasons` help separate police action, police
  operation, disputes, executions, attempted robbery, and other contexts.
- `clippings` help identify specific labels such as feminicide, chase, prison,
  shopping mall, continuous shooting, and others.
- `massacre` increases severity and reduces room for generic answers.
- `policeUnit` can indicate official involvement but should not be exposed with
  sensitive precision in public-facing answers.

## Response Handling

The client should normalize API responses into internal records before any MCP
tool builds natural-language output.

Minimum normalization:

- parse dates into timezone-aware datetimes;
- keep source update headers;
- normalize city/state/neighborhood labels;
- count victims and deaths defensively;
- detect transport interruption;
- keep raw IDs for traceability;
- avoid exposing exact coordinates in public MCP responses.

## Error and Cache Strategy

- Use explicit HTTP timeouts.
- Cache city and state catalogs for a short period.
- Cache occurrence queries by city, state, date range, and page where useful.
- Store `X-Last-Update` to explain data freshness.
- Surface source failures as limitations when the tool can still return partial context.
- Fail closed on authentication problems and do not expose secrets.

## Integration Tests

The integration tests in `tests/integration/test_fogocruzado_api.py` validate:

- login returns a bearer token;
- refresh returns a new bearer token;
- `/states` contract;
- `/cities` contract and filters;
- `/occurrences` contract, pagination, date filters, multiple city filters, and `typeOccurrence`;
- expected nested structures in `contextInfo`, `transports`, `victims`, and `animalVictims`.

These tests are marked `integration` and require credentials through
`FOGOCRUZADO_EMAIL` and `FOGOCRUZADO_PASSWORD`, or compatible `.env` values.
