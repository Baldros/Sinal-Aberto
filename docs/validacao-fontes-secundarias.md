# Secondary Source Validation

Validated on: 2026-06-12, America/Sao_Paulo.
Revalidated on: 2026-06-17, America/Sao_Paulo, now through automated connection
tests in `tests/integration/` with one file per auxiliary source.

Scope: secondary sources listed in `docs/fontes-de-dados.md`. The Fogo Cruzado
API is outside this survey because it has already been validated as the primary
source.

## Revalidation 2026-06-17

The tests in `tests/integration/` rerun this validation. Seven of the eight
sources responded as they did on 2026-06-12. The only observed change:

- **COR.Rio now requires browser-like headers.** The site returns `HTTP 403` to
  clients that do not look like browsers. It sits behind a WAF (`server: hcdn`).
  Changing only `User-Agent` is not enough; `Accept`, `Accept-Language`, and
  `Upgrade-Insecure-Requests` are also needed. With those headers, both
  WordPress REST and RSS return `HTTP 200`.

## Executive Summary

| Source | Status | Best use | Role in the app |
|---|---|---|---|
| ISP Dados RJ | Usable | Open Data RJ CKAN discovery + ISP CSV/SHP/KML downloads | RJ history, CISP/AISP/RISP, aggregate statistics |
| SINESP/MJSP | Usable | MJSP CKAN + XLSX/ZIP downloads | National history, comparison, aggregate priors |
| IBGE Localidades | Usable | REST JSON API | Municipality/state normalization and official codes |
| IBGE Malhas | Usable | REST GeoJSON/TopoJSON/SVG API | Official geometries for maps and spatial joins |
| DATA.RIO geoservices | Usable per dataset | ArcGIS REST/FeatureServer when available | Neighborhoods, administrative regions, urban layers |
| GTFS Rio | Usable | Public ArcGIS/DATA.RIO ZIP | Bus/BRT routes, stops, and services |
| GPS SPPO | Usable with care | Public endpoint filtered by short window | Operational mobility context, not a direct safety signal |
| COR.Rio / official RSS | Usable with low weight; requires browser headers | WordPress REST/RSS | Auxiliary context and official events |
| ISP Conecta / dashboards | Not recommended for direct ingestion | Use source datasets instead of dashboards | Human visualization, not a primary data source |
| `api.dados.rio` | Do not depend on it now | Revalidate before use | Unavailable in test, returning 503 |

## Response Formats and Normalization Points

| Source | Access method | Body format | Observed Content-Type | Normalization points |
|---|---|---|---|---|
| IBGE Localidades | REST | JSON list of objects | `application/json` | Use integer `id` as key; nested hierarchy municipality > micro-region > meso-region > state; do not use free-text name as primary key. |
| IBGE Malhas | REST | GeoJSON `FeatureCollection` | `application/vnd.geo+json` | Ready for GIS; use `GET` only because HEAD returns 405; cache by state/quality. |
| ISP Dados RJ | CKAN + download | Metadata JSON; data CSV; SHP/KML in `.rar` | CKAN `application/json`; CSV `text/csv` or `application/octet-stream` | Confirm CSV encoding and separator; Brazilian date/decimal formats; version by `resource.id`/hash. |
| SINESP/MJSP | CKAN + download | Metadata JSON; ZIP with XLSX/CSV; PDF dictionaries | CKAN `application/json`; download `application/zip` | Unpack in async/offline job; read dictionary before mapping columns; `metadata_modified` is ISO 8601. |
| DATA.RIO (ArcGIS) | ArcGIS REST | JSON or GeoJSON (`f=json` / `f=geojson`) | `text/plain` or `application/json` | Logical errors arrive as `HTTP 200` plus `error`; status is not enough; field names vary by layer. |
| GTFS Rio | ArcGIS item | Metadata JSON; ZIP with GTFS CSV collection | JSON; download `application/zip` | ZIP contains several CSV files (`routes`, `stops`, `trips`, `stop_times`, `calendar`); ingest per table. |
| GPS SPPO | REST with window | JSON list of objects | `text/html` while body is JSON | Do not choose parser by Content-Type; lat/long as decimal-comma strings; timestamps in epoch ms; short window required; deduplicate by `ordem` + `datahora`. |
| COR.Rio | WordPress REST / RSS | WP REST JSON; RSS XML | `application/json`; `application/rss+xml` | Requires browser headers; treat as low-weight context. |

## Headers and Access Control

- **COR.Rio requires browser-like headers.** Without browser `User-Agent`,
  `Accept`, `Accept-Language`, and `Upgrade-Insecure-Requests`, the WAF returns
  `HTTP 403`. The ingestion client must send these headers on every `cor.rio`
  request.
- **GPS SPPO lies in Content-Type.** The header is `text/html`, but the body is
  JSON. Parse the body as JSON directly.
- **IBGE Malhas does not accept HEAD.** It returns `405`; use `GET` for checks
  and downloads.
- **ArcGIS signals errors with HTTP 200.** DATA.RIO and the GTFS item can return
  `200` even on logical failure, with `{"error": {...}}` in the body. Validate
  absence of `error`, not only status.
- License/attribution remains as in 2026-06-12: record source and terms before
  redistributing complete datasets.

## ISP Dados RJ

Usable. The best integration is to discover resources through Open Data RJ CKAN
and download official files hosted at `www.ispdados.rj.gov.br`.

Validated metadata endpoints:

- `https://dadosabertos.rj.gov.br/api/3/action/package_show?id=isp-estatisticas-de-seguranca-publica`
- `https://dadosabertos.rj.gov.br/api/3/action/package_show?id=isp-divisao-territorial`

Files tested with `HTTP 200`:

- `https://www.ispdados.rj.gov.br/Arquivos/BaseDPEvolucaoMensalCisp.csv`
- `https://www.ispdados.rj.gov.br/Arquivos/CISPshp.rar`

Other relevant resources found:

- `BaseMunicipioMensal.csv`
- `Relacao_RISPxAISPxCISP.csv`
- `CorrespondenciaCispAisp.csv`
- `CorrespondenciaCispMunicipioCodAoLongoDoTempo.csv`
- `RegioesKML.rar`, `RegioesSHP.rar`, `AISPkml.rar`, `AISPshp.rar`, `CISPkml.rar`, `CISPshp.rar`

Recommended use:

- download CSVs periodically;
- keep cache/versioning by `resource.id`, `last_modified`, size, and hash;
- use territorial tables to convert CISP/AISP/RISP into municipality/neighborhood when possible;
- treat as historical/aggregate data, not real time.

Note: in RJ CKAN, some package licenses appeared unspecified although resources
were public. For a public product, record attribution and review terms before
redistributing complete datasets.

## SINESP/MJSP

Usable. The official package is in the Ministry of Justice CKAN.

Validated endpoint:

- `https://dados.mj.gov.br/api/3/action/package_show?id=sistema-nacional-de-estatisticas-de-seguranca-publica`

Validated result:

- `success: true`
- license: Creative Commons Attribution
- `metadata_modified: 2026-04-30T18:21:15.960122`
- package with XLSX, ZIP, and PDF dictionary resources

Most relevant resource:

- `Base de Dados VDE`, ZIP: `https://dados.mj.gov.br/dataset/210b9ae2-21fc-4986-89c6-2006eb4db247/resource/e9d6cc2b-33f1-468d-ab09-9aa8303c2eba/download/basededadosvde.zip`

The ZIP returned `HTTP 200`, `application/zip`, at about 35.8 MB.

Recommended use:

- use as aggregate national history;
- ingest through an async/offline routine, not during user requests;
- keep data dictionaries alongside ingestion;
- compare with ISP/Fogo Cruzado only as context because granularity and
  methodology can differ.

## IBGE Localidades

Usable directly through REST JSON API.

Tested endpoint:

- `https://servicodados.ibge.gov.br/api/v1/localidades/estados/RJ/municipios`

Validated result:

- JSON return with 92 RJ municipalities;
- official fields such as `id`, `nome`, `microrregiao`, `mesorregiao`,
  immediate/intermediate region, state, and region.

Recommended use:

- normalize municipality and state codes;
- avoid free-text names as primary keys;
- keep local cache because the base is stable.

## IBGE Malhas

Usable directly by API. `HEAD` returned `405`, but `GET` worked.

Tested endpoint:

- `https://servicodados.ibge.gov.br/api/v3/malhas/estados/33?formato=application/vnd.geo+json&qualidade=minima`

Validated result:

- `HTTP 200`
- `Content-Type: application/vnd.geo+json`

Recommended use:

- download and cache official geometries;
- use `qualidade=minima` for previews and fast filters;
- use higher quality only for rendering/maps that need detail;
- prefer GeoJSON for web and common GIS pipelines.

## DATA.RIO and Municipal Geoservices

Usable per dataset. Do not generically depend on `api.dados.rio` now: tests at
`https://api.dados.rio/`, `/docs`, `/openapi.json`, and `/v2` returned
`503 Service Temporarily Unavailable`.

The most reliable validated path was ArcGIS REST/FeatureServer.

Validated layer:

- `https://pgeo3.rio.rj.gov.br/arcgis/rest/services/Cartografia/Limites_administrativos/FeatureServer/4?f=json`

Validated result:

- layer: `Limite de Bairros`
- geometry: polygons
- capabilities: `Query,Extract`
- supported formats: JSON, GeoJSON, PBF
- neighborhood field: `codbairro`

Validated JSON query:

- `https://pgeo3.rio.rj.gov.br/arcgis/rest/services/Cartografia/Limites_administrativos/FeatureServer/4/query?where=1%3D1&outFields=*&returnGeometry=false&resultRecordCount=3&f=json`

Validated GeoJSON query:

- `https://pgeo3.rio.rj.gov.br/arcgis/rest/services/Cartografia/Limites_administrativos/FeatureServer/4/query?where=1%3D1&outFields=*&returnGeometry=true&outSR=4326&resultRecordCount=1&f=geojson`

Recommended use:

- use for neighborhoods, administrative regions, and official urban layers;
- always read layer metadata before writing queries because field names vary;
- cache geometries and metadata;
- do not assume every DATA.RIO dataset has its own API.

## GTFS Rio

Usable. The official dataset was found as a public ArcGIS/DATA.RIO item.

Validated metadata:

- `https://www.arcgis.com/sharing/rest/content/items/8ffe62ad3b2f42e49814bf941654ea6c?f=json`

Validated download:

- `https://www.arcgis.com/sharing/rest/content/items/8ffe62ad3b2f42e49814bf941654ea6c/data`

Validated result:

- title: `GTFS do Rio de Janeiro`
- type: `CSV Collection`
- access: public
- license: Creative Commons Attribution 4.0
- description: GTFS for bus and BRT lines, updated monthly by SMTR
- download: `HTTP 200`, ZIP of about 25.3 MB

Recommended use:

- ingest routes, stops, trips, and calendars;
- version by size/hash/collection date;
- use for mobility and urban-impact context near occurrences.

## GPS SPPO

Usable with care. The public endpoint responds, but the unfiltered response is
very large.

Endpoint:

- `https://dados.mobilidade.rio/gps/sppo`

Validated filtered query:

- `https://dados.mobilidade.rio/gps/sppo?dataInicial=2026-06-12T16:00:00&dataFinal=2026-06-12T16:05:00`

Validated result:

- `HTTP 200`
- rate-limit headers: 5 requests per second and 60 per minute
- unfiltered response tested above 90 MB
- `Content-Type` was `text/html`, but the body was JSON
- fields found: `ordem`, `latitude`, `longitude`, `datahora`, `velocidade`,
  `linha`, `datahoraenvio`, `datahoraservidor`
- latitude/longitude arrived as strings with decimal comma
- timestamps arrived in epoch milliseconds

Recommended use:

- never call without a time window;
- limit windows to a few minutes;
- deduplicate by `ordem` + `datahora`;
- normalize coordinates and timestamps during ingestion;
- use only as operational mobility context.

## Official Channels, News, and Social Media

Validated COR.Rio endpoints:

- `https://cor.rio/wp-json/wp/v2/posts?per_page=3`
- `https://cor.rio/feed/`

Initial result:

- WordPress REST returned `HTTP 200`, JSON;
- RSS returned `HTTP 200`, XML.

Revalidation 2026-06-17:

- without browser-like headers, both endpoints started returning `HTTP 403`
  (WAF, `server: hcdn`);
- with browser `User-Agent`, `Accept`, `Accept-Language`, and
  `Upgrade-Insecure-Requests`, both returned `HTTP 200`: WP REST as JSON and RSS
  as `application/rss+xml`;
- practical consequence: the COR.Rio ingestion client must send browser-like
  headers.

Additional notes:

- Rio City Hall WordPress API tested with search returned `401`;
- social networks such as X/Instagram should be used only through official APIs
  and platform terms, not scraping;
- journalistic/official content should be auxiliary context, not decisive
  occurrence evidence.

## Recommended Implementation Order

1. IBGE Localidades for territorial normalization.
2. IBGE Malhas for official geometries.
3. ISP Dados RJ through CKAN + CSV/SHP/KML.
4. SINESP/MJSP through CKAN + ZIP/XLSX.
5. DATA.RIO ArcGIS for neighborhoods and administrative regions.
6. Rio static GTFS.
7. GPS SPPO only after queueing, cache, rate limiting, and deduplication exist.
8. COR.Rio RSS/WordPress as auxiliary context.

## Sources Not Recommended for Direct Ingestion

- `api.dados.rio` while it keeps returning 503.
- ISP Conecta/Visualizacao dashboards, because they are human interfaces; use
  source datasets instead.
- Social-media or page scraping without clear API/RSS/license.
- GPS SPPO endpoint without date filters.

## Minimal Modeling Suggestion

`data_sources`:

- `id`
- `name`
- `access_kind`: `ckan`, `rest_json`, `arcgis_feature_server`, `file_download`, `rss`
- `metadata_url`
- `download_url`
- `license`
- `last_checked_at`
- `remote_last_modified`
- `status`
- `notes`

`data_source_resources`:

- `source_id`
- `remote_resource_id`
- `name`
- `format`
- `url`
- `content_type`
- `size_bytes`
- `hash`
- `last_modified`
- `ingested_at`
