# Fontes de dados do Sinal Aberto

Este documento resume as fontes de dados consideradas para o Sinal Aberto, com foco em utilidade, forma de acesso e referências de validação.

A regra geral do projeto é trabalhar apenas com dados públicos, APIs oficiais ou canais de acesso publicados pelos próprios mantenedores. Raspagem de páginas deve ser tratada como último recurso, nunca como fonte central do produto.

## Resumo das formas de acesso

| Fonte | Papel no projeto | Forma de acesso recomendada | Scraping? |
|---|---|---|---|
| Fogo Cruzado | Fonte principal de ocorrências armadas recentes | API oficial com autenticação JWT e autorização prévia | Não |
| ISP Dados RJ | Histórico oficial de segurança pública no RJ | Downloads públicos em CSV, XLS, KML e Shapefile | Não inicialmente |
| SINESP / MJSP | Indicadores nacionais agregados de segurança pública | Downloads públicos em XLSX, ZIP e PDF no portal de dados | Não inicialmente |
| IBGE Localidades | Normalização territorial oficial | API REST oficial | Não |
| IBGE Malhas | Geometrias oficiais de UFs, municípios e regiões | API REST oficial com GeoJSON, TopoJSON ou SVG | Não |
| DATA.RIO | Camadas urbanas do município do Rio | Portal de dados, downloads e eventuais serviços geográficos | Validar dataset por dataset |
| GTFS / transporte | Rotas, paradas, alertas e impacto operacional | Feeds GTFS/GTFS Realtime quando publicados por operadores/autoridades | Evitar; usar apenas feeds oficiais |
| Imprensa e redes sociais oficiais | Contexto e confirmação complementar | RSS, API oficial ou páginas públicas, quando permitido | Só como último recurso e com baixo peso |

---

## 1. Fogo Cruzado

**Papel no Sinal Aberto:** fonte primária para ocorrências de tiroteios, disparos de arma de fogo, presença de agentes, ação/operação policial, vítimas e transporte afetado.

**Por que é útil:** é a fonte mais alinhada com a proposta de estimar atividade armada/policial em tempo quase real. A documentação informa que a API fornece dados atualizados sobre tiroteios e disparos nas regiões metropolitanas do Rio de Janeiro, Recife, Bahia e Pará.

**Forma de acesso:**

- API oficial v2.
- Requer autorização prévia de uso.
- Autenticação via JWT.
- Login por `POST /api/v2/auth/login`.
- Refresh por `POST /api/v2/auth/refresh`.
- Endpoint principal: `GET /occurrences`.
- O token deve ser enviado como Bearer Token no header da requisição.
- A API informa headers de última atualização, como `X-Last-Update` e `X-Last-Update-State`, úteis para cache e sincronização.

**Dados relevantes para o score:**

- `date`.
- `latitude` e `longitude`.
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

**Uso sugerido:**

- Fonte de evidência recente.
- Clusterização temporal e geográfica.
- Cálculo de probabilidade de atividade atual.
- Cálculo de impacto reportado.
- Detecção de ocorrências com ação/operação policial.

**Limitações:**

- Não deve ser tratada como radar completo de todas as operações policiais.
- Operações sem disparos ou sem registro podem não aparecer.
- É necessário validar latência real entre fato, registro e atualização na API.

**Referências:**

- Plataforma da API: https://api.fogocruzado.org.br/
- Documentação geral: https://api.fogocruzado.org.br/docs
- Autenticação: https://api.fogocruzado.org.br/docs/auth
- Ocorrências: https://api.fogocruzado.org.br/docs/endpoint/occurrences
- Pacote R/Python citado pela plataforma: https://github.com/felipesbarros/crossfire

---

## 2. ISP Dados RJ

**Papel no Sinal Aberto:** base auxiliar para histórico oficial, contexto territorial e construção de priors no estado do Rio de Janeiro.

**Por que é útil:** o portal ISPDados publica bases de registros criminais e atividade policial do estado do Rio de Janeiro. As estatísticas são construídas a partir de Registros de Ocorrência e informações complementares de órgãos de segurança. Também há arquivos auxiliares como população, divisão territorial, bases cartográficas, notas metodológicas e dicionários.

**Forma de acesso:**

- Portal público de dados abertos.
- Downloads estruturados em CSV, XLS, KML e Shapefile, dependendo do conjunto.
- Painéis HTML/ISP Conecta para consulta visual.
- Não há necessidade inicial de scraping: os links de CSV e arquivos geográficos podem ser baixados periodicamente.

**Dados relevantes:**

- Estatísticas de segurança por área de delegacia desde 01/2003.
- Estatísticas mensais no estado desde 01/1991.
- Estatísticas mensais por município desde 2014.
- Letalidade violenta.
- Armas apreendidas.
- Policiais mortos em serviço.
- Feminicídio.
- Divisão territorial de segurança: CISP, AISP, RISP.
- Bases cartográficas digitais em KML e Shapefile.
- Dicionários de variáveis e notas metodológicas.

**Uso sugerido:**

- Histórico local para calibrar o prior territorial.
- Comparação entre áreas.
- Contexto de letalidade e recorrência.
- Normalização territorial por CISP/AISP/RISP.
- Enriquecimento de clusters com histórico oficial.

**Limitações:**

- Não é fonte de tempo real.
- As estatísticas se baseiam na data de confecção do Registro de Ocorrência, não necessariamente na data exata do fato.
- Revisões e retificações podem ocorrer.

**Referências:**

- Portal ISPDados: https://www.ispdados.rj.gov.br/
- Estatísticas de Segurança Pública: https://www.ispdados.rj.gov.br/estatistica.html
- Divisão Territorial de Segurança Pública: https://www.ispdados.rj.gov.br/Conteudo.html
- Notas Metodológicas e Dicionários: https://www.ispdados.rj.gov.br/Notas.html
- Visualização de Dados do ISP: https://www.ispvisualizacao.rj.gov.br/
- ISP Conecta: https://ispconecta.rj.gov.br/

---

## 3. SINESP / Ministério da Justiça e Segurança Pública

**Papel no Sinal Aberto:** base auxiliar nacional para contexto agregado, comparação municipal/estadual e indicadores oficiais fora do RJ.

**Por que é útil:** o dataset de Ocorrências Criminais do SINESP reúne indicadores nacionais de segurança pública informados pelos estados e pelo Distrito Federal. É útil para análise comparativa, mas não para tempo real.

**Forma de acesso:**

- Portal de dados públicos do Ministério da Justiça e Segurança Pública.
- Downloads em XLSX, ZIP e PDF.
- Recursos publicados incluem dados por município, dados por UF, base VDE e dicionários.
- Pode-se investigar automação via padrão CKAN do portal, mas a forma validada inicialmente é o download dos recursos publicados na própria página.

**Dados relevantes:**

- Dados Nacionais de Segurança Pública por município.
- Dados Nacionais de Segurança Pública por UF.
- Base de Dados VDE em ZIP.
- Dicionário de Dados por município e UF.
- Indicadores como homicídio doloso, roubo seguido de morte, feminicídio, morte por intervenção de agente do Estado, tráfico de drogas, apreensão de arma de fogo, pessoa desaparecida, entre outros.

**Uso sugerido:**

- Contexto histórico e comparativo.
- Priors municipais/estaduais fora do Rio de Janeiro.
- Benchmarks nacionais.
- Avaliação macro de risco estrutural.

**Limitações:**

- Dados são agregados.
- Não serve para detecção de eventos em andamento.
- A própria página informa que os dados podem refletir o nível de alimentação e consolidação das UFs na data de extração, com atualizações posteriores.

**Referências:**

- Dataset Ocorrências Criminais - SINESP: https://dados.mj.gov.br/dataset/sistema-nacional-de-estatisticas-de-seguranca-publica
- Portal de Dados MJSP: https://dados.mj.gov.br/

---

## 4. IBGE Localidades

**Papel no Sinal Aberto:** normalização territorial oficial.

**Por que é útil:** fornece códigos e hierarquias territoriais oficiais do IBGE para países, UFs, municípios, distritos, subdistritos, regiões metropolitanas e outras divisões.

**Forma de acesso:**

- API REST oficial.
- Retorno estruturado em JSON.
- Não requer scraping.

**Dados relevantes:**

- UFs.
- Municípios.
- Distritos e subdistritos.
- Regiões metropolitanas.
- Regiões geográficas imediatas e intermediárias.
- Códigos oficiais IBGE.

**Uso sugerido:**

- Padronizar nomes e códigos de municípios.
- Resolver ambiguidades territoriais.
- Relacionar ocorrência, município, UF e região.
- Garantir interoperabilidade com SINESP, ISP e outras bases públicas.

**Referências:**

- API de Localidades: https://servicodados.ibge.gov.br/api/docs/localidades

---

## 5. IBGE Malhas Geográficas

**Papel no Sinal Aberto:** geometrias oficiais para mapas, geofencing e agregação territorial.

**Por que é útil:** permite obter malhas simplificadas de unidades político-administrativas do Brasil em formatos adequados para aplicações web.

**Forma de acesso:**

- API REST oficial.
- Formatos disponíveis incluem SVG, GeoJSON e TopoJSON.
- Não requer scraping.

**Dados relevantes:**

- Malhas de municípios.
- Malhas de UFs.
- Malhas de regiões e outras divisões disponíveis.
- Geometrias simplificadas para visualização e análise espacial.

**Uso sugerido:**

- Converter coordenadas em município/UF.
- Criar mapas e polígonos de referência.
- Agregar clusters por limites oficiais.
- Construir camadas de visualização.

**Referências:**

- API de Malhas Geográficas: https://servicodados.ibge.gov.br/api/docs/malhas?versao=3

---

## 6. DATA.RIO

**Papel no Sinal Aberto:** enriquecimento urbano da cidade do Rio de Janeiro.

**Por que é útil:** o portal DATA.RIO reúne dados públicos municipais que podem apoiar camadas urbanas, limites de bairros, equipamentos públicos, infraestrutura, serviços e contexto local.

**Forma de acesso:**

- Portal público de dados da Prefeitura do Rio.
- A forma exata de acesso varia por dataset.
- Priorizar downloads estruturados, APIs ou serviços geográficos quando publicados pelo próprio portal.
- Validar dataset por dataset antes de automatizar.
- Raspagem só deve ser considerada se não houver download/API oficial e se os termos permitirem.

**Dados relevantes esperados:**

- Limites de bairros e regiões administrativas.
- Equipamentos públicos.
- Unidades de saúde, escolas e serviços públicos.
- Camadas urbanas e geográficas.
- Eventuais bases de mobilidade e infraestrutura.

**Uso sugerido:**

- Converter coordenada em bairro ou região administrativa.
- Identificar equipamentos públicos próximos a um cluster.
- Enriquecer respostas com contexto urbano.
- Melhorar visualização em mapa.

**Limitações:**

- Nem todo dataset terá API.
- A documentação e os formatos podem variar entre conjuntos.
- É necessário validar atualização, licença, formato e estabilidade dos links por dataset.

**Referências:**

- Portal DATA.RIO: https://www.data.rio/

---

## 7. GTFS e dados oficiais de transporte

**Papel no Sinal Aberto:** estimar impacto operacional em transporte público e circulação urbana.

**Por que é útil:** interrupções de transporte, desvios, atrasos e bloqueios são bons sinais de impacto público. O Fogo Cruzado já possui campos próprios sobre transporte afetado, mas feeds de transporte podem complementar a análise.

**Forma de acesso:**

- GTFS Schedule: arquivo ZIP com arquivos texto sobre rotas, viagens, paradas, horários e calendário.
- GTFS Realtime: feed em Protocol Buffers com atualizações de viagem, alertas de serviço e posições de veículos.
- Usar apenas feeds publicados oficialmente por operadores, consórcios ou autoridades públicas.
- Evitar scraping de apps, sites ou redes sociais de operadores, salvo autorização/termos claros.

**Dados relevantes:**

- `routes.txt`.
- `stops.txt`.
- `trips.txt`.
- `stop_times.txt`.
- `calendar.txt`.
- GTFS Realtime Service Alerts.
- GTFS Realtime Trip Updates.
- GTFS Realtime Vehicle Positions.

**Uso sugerido:**

- Identificar linhas, estações e paradas próximas a clusters.
- Medir impacto potencial em deslocamento.
- Detectar alertas de serviço causados por atividade policial, acidente, manifestação, desvio ou interrupção.
- Cruzar cluster armado com rede de transporte afetada.

**Limitações:**

- Disponibilidade varia por cidade e operador.
- GTFS Schedule é programado, não tempo real.
- GTFS Realtime depende de publicação oficial e qualidade operacional.
- Nem todo transporte do Rio pode ter feed aberto e documentado.

**Referências:**

- Visão geral GTFS: https://gtfs.org/documentation/overview/
- GTFS Realtime Service Alerts: https://gtfs.org/documentation/realtime/feed-entities/service-alerts/

---

## 8. Imprensa, canais oficiais e redes sociais

**Papel no Sinal Aberto:** confirmação contextual e sinais complementares, nunca fonte central de decisão.

**Por que pode ser útil:** comunicados oficiais, reportagens e publicações verificadas podem ajudar a confirmar contexto, extensão territorial, impactos e encerramento de eventos.

**Forma de acesso:**

- Preferir RSS, APIs oficiais, páginas institucionais e canais públicos com termos claros.
- Evitar scraping como fonte automática de decisão.
- Se usado, atribuir baixo peso probabilístico e marcar como fonte complementar.

**Dados relevantes:**

- Comunicados oficiais.
- Alertas de órgãos públicos.
- Informações de operadores de transporte.
- Reportagens verificadas.
- Atualizações sobre interdições, escolas fechadas, transporte interrompido ou atendimento emergencial.

**Uso sugerido:**

- Explicar contexto.
- Confirmar impacto urbano.
- Adicionar fonte textual à resposta.
- Validar ou reduzir incerteza de clusters detectados por outras fontes.

**Limitações:**

- Alto risco de ruído, duplicidade e atraso.
- Termos de uso variam por plataforma.
- Redes sociais podem conter boatos ou relatos não verificados.
- Nunca deve substituir fontes estruturadas e oficiais.

---

## Priorização recomendada

### MVP sem scraping

1. Fogo Cruzado via API.
2. ISP Dados via downloads CSV/KML/Shapefile.
3. IBGE Localidades via API.
4. IBGE Malhas via API.
5. SINESP/MJSP via downloads públicos.
6. DATA.RIO apenas para datasets com download/API/serviço geográfico claro.

### Armazenamento no MVP

O MVP deve começar com SQLite, mantendo o banco pequeno, auditável e reconstruível a partir das fontes externas autorizadas.

Uso recomendado:

- armazenar ocorrências recentes normalizadas da API do Fogo Cruzado;
- guardar metadados de fonte, horário de consulta e horário de última atualização;
- manter cache curto para reduzir pressão sobre a API externa;
- salvar clusters recentes já calculados para evitar processamento repetido a cada pergunta;
- usar índices por data, cidade, bairro, latitude e longitude;
- filtrar por janela temporal e bounding box antes de aplicar cálculo de distância no Python.

PostgreSQL/PostGIS deve ser adotado depois se houver necessidade de histórico amplo, consultas por polígonos, interseções espaciais, múltiplas instâncias ou dashboard público com maior concorrência.

### Fase posterior

1. Feeds oficiais de transporte, se disponíveis.
2. Comunicados oficiais e RSS de imprensa, se houver termos claros.
3. Scraping somente como último recurso, com governança, baixo peso no modelo e validação jurídica/técnica.

## Observação técnica

Separar as fontes por função:

- **Evidência atual:** Fogo Cruzado e, quando disponível, feeds oficiais de transporte.
- **Histórico e priors:** ISP Dados e SINESP.
- **Geografia:** IBGE e DATA.RIO.
- **Contexto textual:** comunicados oficiais e imprensa verificada.

Essa separação evita misturar uma fonte histórica com uma fonte de tempo quase real e reduz o risco de respostas determinísticas demais.
