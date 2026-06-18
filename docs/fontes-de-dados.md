# Sinal Aberto Data Sources

This document summarizes the data sources considered for Sinal Aberto, focusing
on utility, access method, and validation references.

The project rule is to work only with public data, official APIs, or access
channels published by the maintainers themselves. Page scraping should be a last
resort, never the product's central source.

## Access Summary

| Source | Role in the project | Recommended access method | Scraping? |
|---|---|---|---|
| Fogo Cruzado | Primary source for recent armed occurrences | Official API with JWT authentication and prior authorization | No |
| ISP Dados RJ | Official public-safety history in RJ | Public CSV, XLS, KML, and Shapefile downloads | Not initially |
| SINESP / MJSP | Aggregate national public-safety indicators | Public XLSX, ZIP, and PDF downloads from the data portal | Not initially |
| IBGE Localidades | Official territorial normalization | Official REST API | No |
| IBGE Malhas | Official geometries for states, municipalities, and regions | Official REST API with GeoJSON, TopoJSON, or SVG | No |
| DATA.RIO | Urban layers for Rio de Janeiro city | Data portal, downloads, and geographic services | Validate per dataset |
| GTFS / transport | Routes, stops, alerts, and operational impact | GTFS/GTFS Realtime feeds when published by operators or authorities | Avoid; use official feeds only |
| Press and official social channels | Context and complementary confirmation | RSS, official APIs, or public pages when allowed | Only as a last resort and with low weight |

---

## 1. Fogo Cruzado

**Role in Sinal Aberto:** primary source for shooting, gunfire, agent presence,
police action/operation, victim, and affected-transport occurrences.

**Why it is useful:** this is the source most aligned with estimating armed or
police activity in near real time. The documentation says the API provides
updated data on shootings and gunfire in the metropolitan regions of Rio de
Janeiro, Recife, Bahia, and Para.

**Access method:**

- Official API v2.
- Requires prior authorization.
- JWT authentication.
- Login through `POST /api/v2/auth/login`.
- Refresh through `POST /api/v2/auth/refresh`.
- Main endpoint: `GET /occurrences`.
- Token sent as a bearer token in the request header.
- Last-update headers such as `X-Last-Update` and `X-Last-Update-State` support
  cache and synchronization.

**Fields relevant to scoring:**

- `date`.
- `latitude` and `longitude`.
- `state`, `city`, `neighborhood`, `subNeighborhood`, `locality`.
- `policeAction`.
- `agentPresence`.
- `contextInfo.mainReason`.
- `contextInfo.complementaryReasons`.
- `contextInfo.clippings`.
- `contextInfo.massacre`.
- `contextInfo.policeUnit`.
- `transports.interruptedTransport`.
- `transports.dateInterruption`.
- `transports.releaseDate`.
- `victims.situation`.
- `victims.personType`.

**Suggested use:**

- Recent-evidence source.
- Temporal and geographic clustering.
- Current-activity probability calculation.
- Reported-impact calculation.
- Detection of occurrences with police action/operation.

**Limitations:**

- Should not be treated as a complete radar for all police operations.
- Operations without gunfire or reports may not appear.
- Real latency between event, report, and API update must be validated.

**References:**

- API platform: https://api.fogocruzado.org.br/
- General documentation: https://api.fogocruzado.org.br/docs
- Authentication: https://api.fogocruzado.org.br/docs/auth
- Occurrences: https://api.fogocruzado.org.br/docs/endpoint/occurrences
- R/Python package cited by the platform: https://github.com/felipesbarros/crossfire

---

## 2. ISP Dados RJ

**Role in Sinal Aberto:** auxiliary base for official history, territorial
context, and prior construction in Rio de Janeiro state.

**Why it is useful:** ISPDados publishes criminal-record and police-activity
datasets for Rio de Janeiro state. The statistics are built from occurrence
reports and complementary public-safety-agency information. The portal also
contains population files, territorial division, cartographic bases,
methodological notes, and dictionaries.

**Access method:**

- Public open-data portal.
- Structured downloads in CSV, XLS, KML, and Shapefile depending on dataset.
- HTML dashboards/ISP Conecta for visual browsing.
- No initial scraping requirement because CSV and geographic files can be
  downloaded periodically.

**Relevant data:**

- Public-safety statistics by police-station area since 2003-01.
- Monthly state statistics since 1991-01.
- Monthly municipal statistics since 2014.
- Violent lethality.
- Seized firearms.
- Police officers killed on duty.
- Feminicide.
- Public-safety territorial divisions: CISP, AISP, RISP.
- Digital cartographic bases in KML and Shapefile.
- Variable dictionaries and methodological notes.

**Suggested use:**

- Local history for territorial priors.
- Area comparison.
- Lethality and recurrence context.
- CISP/AISP/RISP territorial normalization.
- Enrichment of clusters with official history.

**Limitations:**

- Not a real-time source.
- Statistics are based on occurrence-report creation date, not necessarily the
  exact event date.
- Revisions and corrections can happen.

**References:**

- ISPDados portal: https://www.ispdados.rj.gov.br/
- Public-safety statistics: https://www.ispdados.rj.gov.br/estatistica.html
- Public-safety territorial division: https://www.ispdados.rj.gov.br/Conteudo.html
- Methodological notes and dictionaries: https://www.ispdados.rj.gov.br/Notas.html
- ISP data visualization: https://www.ispvisualizacao.rj.gov.br/
- ISP Conecta: https://ispconecta.rj.gov.br/

---

## 3. SINESP / Ministry of Justice and Public Security

**Role in Sinal Aberto:** national auxiliary base for aggregate context,
municipal/state comparison, and official indicators outside RJ.

**Why it is useful:** the SINESP criminal-occurrence dataset gathers national
public-safety indicators reported by states and the Federal District. It is
useful for comparative analysis, but not real-time detection.

**Access method:**

- Public data portal from the Ministry of Justice and Public Security.
- Downloads in XLSX, ZIP, and PDF.
- Published resources include municipal data, state data, VDE database, and data
  dictionaries.
- CKAN automation can be investigated; the initially validated method is
  downloading resources from the published page.

**Relevant data:**

- National public-safety data by municipality.
- National public-safety data by state.
- VDE database in ZIP.
- Data dictionaries by municipality and state.
- Indicators such as intentional homicide, robbery followed by death,
  feminicide, death caused by state-agent intervention, drug trafficking,
  firearm seizure, missing person, and others.

**Suggested use:**

- Historical and comparative context.
- Municipal/state priors outside Rio de Janeiro.
- National benchmarks.
- Macro-level structural-risk assessment.

**Limitations:**

- Aggregate data.
- Not suitable for ongoing-event detection.
- The portal notes that data can reflect the reporting and consolidation level
  of each state at extraction time, with later updates.

**References:**

- SINESP criminal occurrences dataset: https://dados.mj.gov.br/dataset/sistema-nacional-de-estatisticas-de-seguranca-publica
- MJSP data portal: https://dados.mj.gov.br/

---

## 4. IBGE Localidades

**Role in Sinal Aberto:** official territorial normalization.

**Why it is useful:** provides official IBGE codes and territorial hierarchies
for countries, states, municipalities, districts, subdistricts, metropolitan
regions, and other divisions.

**Access method:**

- Official REST API.
- Structured JSON response.
- No scraping required.

**Relevant data:**

- States.
- Municipalities.
- Districts and subdistricts.
- Metropolitan regions.
- Immediate and intermediate geographic regions.
- Official IBGE codes.

**Suggested use:**

- Standardize municipality names and codes.
- Resolve territorial ambiguity.
- Relate occurrence, municipality, state, and region.
- Ensure interoperability with SINESP, ISP, and other public datasets.

**References:**

- Localidades API: https://servicodados.ibge.gov.br/api/docs/localidades

---

## 5. IBGE Malhas Geograficas

**Role in Sinal Aberto:** official geometries for maps, geofencing, and
territorial aggregation.

**Why it is useful:** allows simplified meshes of Brazilian
political-administrative units in formats suited for web applications.

**Access method:**

- Official REST API.
- Available formats include SVG, GeoJSON, and TopoJSON.
- No scraping required.

**Relevant data:**

- State geometry.
- Municipality geometry.
- Regional geometry.
- Simplified meshes for web use.

**Suggested use:**

- Official map overlays.
- Point-in-polygon enrichment.
- Territorial aggregation by official boundaries.
- Safe approximate areas instead of exact occurrence coordinates.

**References:**

- Malhas API: https://servicodados.ibge.gov.br/api/docs/malhas

---

## 6. DATA.RIO

**Role in Sinal Aberto:** municipal urban layers for Rio de Janeiro city.

**Why it is useful:** provides neighborhood boundaries, administrative regions,
public facilities, urban infrastructure, and other city layers that can enrich
the public-impact model.

**Access method:**

- DATA.RIO portal.
- ArcGIS REST/FeatureServer services for some datasets.
- File downloads for others.
- Validate each dataset individually before integration.

**Relevant data:**

- Neighborhood boundaries.
- Administrative regions.
- Urban facilities and infrastructure.
- Geospatial layers for city context.

**Suggested use:**

- Neighborhood and administrative-region mapping.
- Urban-context enrichment.
- Public-impact calculations around transport, facilities, and dense areas.

**Limitations:**

- Dataset access patterns vary.
- Some ArcGIS endpoints return HTTP 200 with an `error` object; validate the body,
  not only the HTTP status.

**References:**

- DATA.RIO portal: https://www.data.rio/
- ArcGIS item/services vary by dataset.

---

## 7. GTFS and Mobility Sources

**Role in Sinal Aberto:** mobility context and possible transport-impact signal.

**Why it is useful:** routes, stops, trips, alerts, and vehicle positions can
show which corridors or services may be affected by a cluster.

**Access method:**

- Official GTFS static feeds.
- GTFS Realtime feeds when published.
- Official APIs from operators or transport authorities.
- Avoid unofficial scraping.

**Relevant data:**

- Routes and stops.
- Trips and calendars.
- Realtime alerts.
- Vehicle positions.
- Service interruptions.

**Suggested use:**

- Estimate public impact around affected routes/stops.
- Detect or explain transport disruption.
- Add mobility context to clusters.

**Limitations:**

- Static GTFS is not real time.
- Realtime feeds may have rate limits, sparse coverage, or quality issues.
- GPS endpoints can be large and require tight time windows.

---

## 8. Official Channels, Journalism, and Social Media

**Role in Sinal Aberto:** complementary context and possible confirmation,
never the decisive source by default.

**Access method:**

- RSS feeds.
- Official APIs.
- Public pages when terms allow use.
- Platform APIs for social media; avoid scraping.

**Suggested use:**

- Contextual explanation.
- Official or journalistic confirmation when available.
- Low-weight supporting signal for clusters.

**Limitations:**

- Posts can lag events.
- Language can be ambiguous.
- Platform terms and licensing must be respected.
- Rumor control and verification are mandatory before any user-facing claim.

## Recommended Integration Order

1. Fogo Cruzado as the primary occurrence source.
2. IBGE Localidades for official territorial normalization.
3. IBGE Malhas for official geometries.
4. ISP Dados RJ for RJ historical priors.
5. SINESP/MJSP for national aggregate context.
6. DATA.RIO for Rio urban layers.
7. GTFS/static transport feeds.
8. GPS/realtime mobility only after queueing, cache, rate limits, and deduplication exist.
9. COR.Rio and official/news feeds as auxiliary context.
