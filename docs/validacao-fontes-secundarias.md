# Validacao de fontes secundarias

Validado em: 2026-06-12, America/Sao_Paulo.
Revalidado em: 2026-06-17, America/Sao_Paulo, agora por testes de conexao automatizados em `tests/integration/` (um arquivo por fonte auxiliar).

Escopo: fontes secundarias citadas em `docs/fontes-de-dados.md`. A API do Fogo Cruzado fica fora deste levantamento porque ja foi validada como fonte principal.

## Revalidacao 2026-06-17

Os testes em `tests/integration/` reexecutam esta validacao a cada rodada. Sete das oito fontes responderam como em 2026-06-12. Unica mudanca observada:

- **COR.Rio passou a exigir headers de navegador.** O site agora responde `HTTP 403` a clientes sem cara de browser (esta atras de um WAF, header `server: hcdn`). Trocar apenas o `User-Agent` nao basta; e preciso enviar tambem `Accept`, `Accept-Language` e `Upgrade-Insecure-Requests`. Com esses headers, tanto o WordPress REST quanto o RSS voltam a `HTTP 200`. Detalhes em "Headers e controle de acesso".

## Resumo executivo

| Fonte | Status | Melhor forma de uso | Papel no app |
| --- | --- | --- | --- |
| ISP Dados RJ | Usavel | CKAN do Dados Abertos RJ para descoberta + downloads CSV/SHP/KML do ISP | Historico RJ, CISP/AISP/RISP, estatisticas agregadas |
| SINESP/MJSP | Usavel | CKAN do MJSP + download XLSX/ZIP | Historico nacional, comparacao e priors agregados |
| IBGE Localidades | Usavel | API REST JSON | Normalizacao de municipios, UFs, codigos oficiais |
| IBGE Malhas | Usavel | API REST GeoJSON/TopoJSON/SVG | Geometrias oficiais para mapas e joins espaciais |
| DATA.RIO geosservicos | Usavel por dataset | ArcGIS REST/FeatureServer quando existir | Bairros, regioes administrativas e camadas urbanas |
| GTFS Rio | Usavel | ZIP publico do ArcGIS/DATA.RIO | Linhas, paradas e servicos de onibus/BRT |
| GPS SPPO | Usavel com cuidado | Endpoint publico filtrado por janela curta | Contexto operacional de mobilidade, nao sinal direto de seguranca |
| COR.Rio / RSS oficiais | Usavel com baixo peso (requer headers de browser) | WordPress REST/RSS | Contexto auxiliar e eventos oficiais |
| ISP Conecta / dashboards | Nao recomendado para ingestao direta | Usar datasets de base em vez de dashboards | Visualizacao humana, nao fonte primaria de dados |
| `api.dados.rio` | Nao depender agora | Validar novamente antes de usar | Indisponivel no teste, retornando 503 |

## Formatos de resposta e pontos de normalizacao

Resumo de como cada fonte responde e do que precisa ser tratado antes de usar os dados. Serve para decidir parser, validacao e camada de ingestao, e para saber onde havera normalizacao.

| Fonte | Forma de acesso | Formato do corpo | Content-Type observado | Pontos de normalizacao |
| --- | --- | --- | --- | --- |
| IBGE Localidades | REST | JSON (lista de objetos) | `application/json` | `id` inteiro como chave; hierarquia aninhada municipio > microrregiao > mesorregiao > UF; nao usar nome livre como chave. |
| IBGE Malhas | REST | GeoJSON (`FeatureCollection`) | `application/vnd.geo+json` | Geometria pronta para GIS; so `GET` (HEAD responde 405); cachear por UF/qualidade. |
| ISP Dados RJ | CKAN + download | Metadados em JSON; dados em CSV (SHP/KML em `.rar`) | CKAN `application/json`; CSV `text/csv` ou `application/octet-stream` | Confirmar encoding e separador do CSV; datas e decimais em formato BR; versionar por `resource.id`/hash. |
| SINESP/MJSP | CKAN + download | Metadados em JSON; dados em ZIP (XLSX/CSV) + dicionarios PDF | CKAN `application/json`; download `application/zip` | Descompactar em job assincrono; ler dicionario antes de mapear colunas; `metadata_modified` em ISO 8601. |
| DATA.RIO (ArcGIS) | ArcGIS REST | JSON ou GeoJSON (`f=json` / `f=geojson`) | `text/plain` ou `application/json` | Erro logico vem com `HTTP 200` + chave `error`: status nao basta; nomes de campos variam por layer (ler metadados antes). |
| GTFS Rio | Item ArcGIS | Metadados em JSON; dados em ZIP (colecao de CSV GTFS) | JSON; download `application/zip` | ZIP contem varios CSV (`routes`, `stops`, `trips`, `stop_times`, `calendar`); ingerir por tabela. |
| GPS SPPO | REST com janela | JSON (lista de objetos) | `text/html` (corpo e JSON) | Nao confiar no Content-Type para escolher parser; lat/long como string com virgula decimal; timestamps em epoch ms; exige janela curta; deduplicar por `ordem` + `datahora`. |
| COR.Rio | WordPress REST / RSS | WP REST em JSON; feed em XML (RSS) | `application/json`; `application/rss+xml` | Exige headers de navegador (ver abaixo); tratar como contexto de baixo peso. |

## Headers e controle de acesso

Pontos relacionados a headers que afetam diretamente a integracao:

- **COR.Rio exige cara de navegador.** Sem `User-Agent`, `Accept`, `Accept-Language` e `Upgrade-Insecure-Requests` de browser, o WAF (`server: hcdn`) responde `HTTP 403`. O cliente de ingestao precisa enviar esses headers em toda requisicao a `cor.rio`.
- **GPS SPPO mente no Content-Type.** O header vem como `text/html`, mas o corpo e JSON. Parsear como JSON diretamente, sem ramificar pelo Content-Type.
- **IBGE Malhas nao aceita HEAD.** Responde `405` a HEAD; usar `GET` para checagem e download.
- **ArcGIS sinaliza erro com HTTP 200.** Tanto DATA.RIO quanto o item GTFS retornam `200` mesmo em falha logica, com o corpo `{"error": {...}}`. Validar a ausencia da chave `error`, nao apenas o status.
- Licenca/atribuicao seguem como em 2026-06-12: registrar fonte e termos antes de redistribuir bases completas.

## ISP Dados RJ

Da para usar. A melhor integracao e descobrir recursos pelo CKAN do Dados Abertos RJ e baixar os arquivos oficiais hospedados em `www.ispdados.rj.gov.br`.

Endpoints de metadados validados:

- `https://dadosabertos.rj.gov.br/api/3/action/package_show?id=isp-estatisticas-de-seguranca-publica`
- `https://dadosabertos.rj.gov.br/api/3/action/package_show?id=isp-divisao-territorial`

Arquivos testados com `HTTP 200`:

- `https://www.ispdados.rj.gov.br/Arquivos/BaseDPEvolucaoMensalCisp.csv`
- `https://www.ispdados.rj.gov.br/Arquivos/CISPshp.rar`

Outros recursos relevantes encontrados:

- `BaseMunicipioMensal.csv`
- `Relacao_RISPxAISPxCISP.csv`
- `CorrespondenciaCispAisp.csv`
- `CorrespondenciaCispMunicipioCodAoLongoDoTempo.csv`
- `RegioesKML.rar`, `RegioesSHP.rar`, `AISPkml.rar`, `AISPshp.rar`, `CISPkml.rar`, `CISPshp.rar`

Uso recomendado:

- baixar CSVs periodicamente;
- manter cache/versionamento por `resource.id`, `last_modified`, tamanho e hash;
- usar as tabelas territoriais para converter CISP/AISP/RISP em municipio/bairro quando possivel;
- tratar como dado historico/agregado, nao tempo real.

Observacao: no CKAN do RJ a licenca apareceu como nao especificada em alguns pacotes, apesar dos recursos estarem publicos. Para produto publico, registrar atribuicao e revisar termos antes de redistribuir bases completas.

## SINESP/MJSP

Da para usar. O pacote oficial esta no CKAN do Ministerio da Justica.

Endpoint validado:

- `https://dados.mj.gov.br/api/3/action/package_show?id=sistema-nacional-de-estatisticas-de-seguranca-publica`

Resultado validado:

- `success: true`
- licenca: Creative Commons Atribuicao
- `metadata_modified: 2026-04-30T18:21:15.960122`
- pacote com recursos XLSX, ZIP e dicionarios PDF

Recurso mais relevante:

- `Base de Dados VDE`, ZIP: `https://dados.mj.gov.br/dataset/210b9ae2-21fc-4986-89c6-2006eb4db247/resource/e9d6cc2b-33f1-468d-ab09-9aa8303c2eba/download/basededadosvde.zip`

O download do ZIP retornou `HTTP 200`, `application/zip`, com aproximadamente 35,8 MB.

Uso recomendado:

- usar como historico nacional/agregado;
- ingerir por rotina assincrona, nao em request de usuario;
- manter dicionarios de dados junto da ingestao;
- comparar com ISP/Fogo Cruzado apenas como camada contextual, porque granularidade e metodologia podem divergir.

## IBGE Localidades

Da para usar diretamente por API REST JSON.

Endpoint testado:

- `https://servicodados.ibge.gov.br/api/v1/localidades/estados/RJ/municipios`

Resultado validado:

- retorno JSON com 92 municipios do RJ;
- campos oficiais como `id`, `nome`, microrregiao, mesorregiao, regiao imediata/intermediaria, UF e regiao.

Uso recomendado:

- normalizar codigos de municipio e UF;
- evitar nomes livres como chave primaria;
- manter cache local porque a base e estavel.

## IBGE Malhas

Da para usar diretamente por API. O metodo `HEAD` retornou `405`, mas `GET` funcionou.

Endpoint testado:

- `https://servicodados.ibge.gov.br/api/v3/malhas/estados/33?formato=application/vnd.geo+json&qualidade=minima`

Resultado validado:

- `HTTP 200`
- `Content-Type: application/vnd.geo+json`

Uso recomendado:

- baixar e cachear geometrias oficiais;
- usar `qualidade=minima` para previews e filtros rapidos;
- usar qualidade maior apenas em renderizacao/mapas que precisem de detalhe;
- preferir GeoJSON para pipeline web e GIS comum.

## DATA.RIO e geosservicos municipais

Da para usar, mas por dataset. Nao vale depender genericamente de `api.dados.rio` neste momento: os testes em `https://api.dados.rio/`, `/docs`, `/openapi.json` e `/v2` retornaram `503 Service Temporarily Unavailable`.

O caminho mais confiavel validado foi ArcGIS REST/FeatureServer.

Camada validada:

- `https://pgeo3.rio.rj.gov.br/arcgis/rest/services/Cartografia/Limites_administrativos/FeatureServer/4?f=json`

Resultado validado:

- camada: `Limite de Bairros`
- geometria: poligonos
- capacidades: `Query,Extract`
- formatos suportados: JSON, GeoJSON, PBF
- campo de bairro: `codbairro`

Query JSON validada:

- `https://pgeo3.rio.rj.gov.br/arcgis/rest/services/Cartografia/Limites_administrativos/FeatureServer/4/query?where=1%3D1&outFields=*&returnGeometry=false&resultRecordCount=3&f=json`

Query GeoJSON validada:

- `https://pgeo3.rio.rj.gov.br/arcgis/rest/services/Cartografia/Limites_administrativos/FeatureServer/4/query?where=1%3D1&outFields=*&returnGeometry=true&outSR=4326&resultRecordCount=1&f=geojson`

Uso recomendado:

- usar para bairros, regioes administrativas e camadas urbanas oficiais;
- sempre ler metadados da layer antes de escrever queries, porque nomes de campos variam;
- cachear geometrias e metadados;
- nao assumir que todo dataset DATA.RIO tem API propria.

## GTFS Rio

Da para usar. O dataset oficial foi encontrado como item publico ArcGIS/DATA.RIO.

Metadados validados:

- `https://www.arcgis.com/sharing/rest/content/items/8ffe62ad3b2f42e49814bf941654ea6c?f=json`

Download validado:

- `https://www.arcgis.com/sharing/rest/content/items/8ffe62ad3b2f42e49814bf941654ea6c/data`

Resultado validado:

- titulo: `GTFS do Rio de Janeiro`
- tipo: `CSV Collection`
- acesso: publico
- licenca: Creative Commons Attribution 4.0
- descricao: GTFS de linhas de onibus e BRT, atualizado mensalmente pela SMTR
- download: `HTTP 200`, ZIP com aproximadamente 25,3 MB

Uso recomendado:

- ingerir rotas, paradas, viagens e calendarios;
- versionar por tamanho/hash/data de coleta;
- usar para contexto de mobilidade e impacto urbano perto de ocorrencias.

## GPS SPPO

Da para usar com cuidado. O endpoint publico responde, mas a resposta sem filtro e muito grande.

Endpoint:

- `https://dados.mobilidade.rio/gps/sppo`

Query filtrada validada:

- `https://dados.mobilidade.rio/gps/sppo?dataInicial=2026-06-12T16:00:00&dataFinal=2026-06-12T16:05:00`

Resultado validado:

- `HTTP 200`
- headers de limite: 5 requisicoes por segundo e 60 por minuto;
- resposta sem filtro testada com mais de 90 MB;
- `Content-Type` veio como `text/html`, mas o corpo e JSON;
- campos encontrados: `ordem`, `latitude`, `longitude`, `datahora`, `velocidade`, `linha`, `datahoraenvio`, `datahoraservidor`;
- latitude/longitude vieram como strings com virgula decimal;
- timestamps vieram em epoch milliseconds.

Uso recomendado:

- nunca chamar sem janela temporal;
- limitar janelas a poucos minutos;
- deduplicar por `ordem` + `datahora`;
- normalizar coordenadas e timestamps na ingestao;
- usar apenas como contexto operacional de mobilidade.

## Canais oficiais, noticias e redes sociais

Da para usar parcialmente, com peso baixo. O COR.Rio expõe WordPress REST e RSS.

Endpoints validados:

- `https://cor.rio/wp-json/wp/v2/posts?per_page=3`
- `https://cor.rio/feed/`

Resultado validado (2026-06-12):

- WordPress REST retornou `HTTP 200`, JSON;
- RSS retornou `HTTP 200`, XML.

Revalidacao (2026-06-17):

- sem headers de navegador, os dois endpoints passaram a responder `HTTP 403` (WAF, `server: hcdn`);
- com `User-Agent`, `Accept`, `Accept-Language` e `Upgrade-Insecure-Requests` de browser, voltaram a `HTTP 200`: WP REST em JSON, RSS em XML `application/rss+xml`;
- consequencia pratica: o cliente de ingestao do COR.Rio precisa enviar headers de browser.

Limites:

- API WordPress da Prefeitura do Rio testada com busca retornou `401`;
- redes sociais como X/Instagram devem ser usadas via APIs oficiais e termos das plataformas, nao scraping;
- conteudo jornalistico/oficial deve entrar como contexto auxiliar, nao fonte decisiva de ocorrencia.

## Ordem recomendada de implementacao

1. IBGE Localidades para normalizacao territorial.
2. IBGE Malhas para geometrias oficiais.
3. ISP Dados RJ via CKAN + CSV/SHP/KML.
4. SINESP/MJSP via CKAN + ZIP/XLSX.
5. DATA.RIO ArcGIS para bairros e regioes administrativas.
6. GTFS estatico do Rio.
7. GPS SPPO apenas depois de ter fila, cache, rate limit e deduplicacao.
8. COR.Rio RSS/WordPress como contexto auxiliar.

## Fontes que eu nao usaria como ingestao direta

- `api.dados.rio`, enquanto continuar retornando 503.
- Dashboards do ISP Conecta/Visualizacao, porque sao interface humana; usar os datasets de origem.
- Scraping de redes sociais ou paginas sem API/RSS/licenca clara.
- Endpoint GPS SPPO sem filtros de data.

## Sugestao de modelagem minima

Tabela `data_sources`:

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

Tabela `source_resources`:

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

Para CKAN, usar `package_show` como fonte de verdade de metadados. Para arquivos grandes, baixar em job assincrono e manter historico de hash. Para ArcGIS, salvar metadados da layer, campos e `supportedQueryFormats` antes de consultar dados.
