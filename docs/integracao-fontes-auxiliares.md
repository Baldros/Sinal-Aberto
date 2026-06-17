# Integração das fontes auxiliares

Desenhado em: **2026-06-17**.

Este documento define como o Sinal Aberto vai integrar as fontes auxiliares já
validadas (`docs/validacao-fontes-secundarias.md`) ao MCP de consulta, sem
trair sua natureza: é uma ferramenta de **consulta orientada a texto e dados
numéricos**, não um servidor de mapas ou de arquivos.

Hoje apenas o Fogo Cruzado entrega dados nas respostas. As oito fontes
auxiliares estão catalogadas em `list_data_sources`, mas marcadas como
`validada, nao integrada`. Este é o plano para fechar essa lacuna de forma
incremental e segura.

## Princípio central

**Não ingerir artefatos. Destilar cada fonte em fatos compactos de texto e
número, e expô-los como campos pequenos e atribuídos que enriquecem a resposta
em JSON.**

Consequências diretas:

- O agente cliente nunca recebe CSV, ZIP, GeoJSON ou shapefile, nem "conversa
  com um banco". Ele só chama uma tool e recebe JSON, como já acontece hoje. O
  armazenamento interno (cache, arquivo, banco) é detalhe privado do servidor.
- Trabalho pesado (baixar e limpar arquivos grandes) nunca acontece no caminho
  de uma consulta de usuário.
- Toda informação auxiliar é opcional e carrega sua própria fonte e horário.

### Entrada da fonte ≠ saída do MCP

Um ponto que causa confusão: o **formato em que a fonte publica** não é o
**formato em que respondemos**. São pontas opostas do cano.

```
fonte publica       nosso código          MCP responde
(CSV/ZIP/JSON)  →   limpa e destila   →   sempre JSON   →  agente
 escolha deles                            escolha nossa
```

O ISP publica CSV, o SINESP publica ZIP/XLSX, o IBGE e o COR.Rio já publicam
JSON. Lemos cada um no formato que ele oferece e **sempre** devolvemos JSON. O
agente recebe JSON em 100% dos casos; o CSV, quando existe, é só um detalhe de
leitura interna.

## Papéis funcionais das fontes

Uma fonte auxiliar só entra se cumprir um destes três papéis no
`get_recent_activity`:

| Papel | Pergunta que responde | Fontes |
| --- | --- | --- |
| **A. Normalizar** | "Que lugar é esse, em código oficial?" | IBGE Localidades |
| **B. Linha de base** | "Isso é muito, ou é normal aqui?" | ISP Dados RJ, SINESP/MJSP, população (IBGE/SIDRA) |
| **C. Corroborar** | "Outra fonte oficial menciona algo agora?" | COR.Rio (texto), GPS SPPO (sinal fraco) |

### Fontes descartadas para este MCP

Geográficas/arquivo-cêntricas, conflitam com o objetivo texto/número:

- **IBGE Malhas** (GeoJSON) — geometria pura.
- **GTFS Rio** (ZIP estático) — referência geográfica de transporte; o Fogo
  Cruzado já fornece `transport_interrupted`.
- **DATA.RIO ArcGIS** — camadas urbanas geográficas; reavaliar apenas se algum
  atributo textual específico se provar necessário.

Descartar aqui não é "nunca": é reconhecer que servir geometria a um agente que
quer texto e número é a integração errada.

## Arquitetura: três naturezas de dado, três mecanismos

O erro a evitar é impor **um** mecanismo a **todo** dado. Cada fonte tem uma
natureza, e o mecanismo segue a natureza. Não há "ETL + banco para tudo": a
maior parte das fontes é consultada ao vivo, exatamente como o Fogo Cruzado é
hoje.

| Natureza | Muda com que frequência? | Como obter | Job offline? | Banco? | Frescor |
| --- | --- | --- | --- | --- | --- |
| **Vivo crítico** — Fogo Cruzado, COR.Rio, GPS SPPO | a cada minuto/hora | API ao vivo + cache curto (TTL) | não | não | sempre fresco |
| **Referência estável** — IBGE território | quase nunca | API ao vivo + cache longo | não | não | irrelevante (não muda) |
| **Histórico agregado** — ISP, SINESP | ~mensal | arquivo preparado por job | sim | opcional | tão fresco quanto a fonte |

Observações que decorrem da tabela:

- **O preparo offline ("ETL") aparece numa única linha**: a dos dados históricos
  do ISP/SINESP. Todo o resto é ao vivo.
- **O IBGE não precisa de job nem de banco.** É só mais um adaptador com cache
  longo, no mesmo molde do cache de cidades que o `FogoCruzadoClient` já mantém.
  A malha municipal praticamente não muda, então um cache de horas/dias basta.
- **Frescor é protegido onde importa.** O dado em que "estar atualizado" é vital
  (*"tem tiroteio agora?"*) nunca vai para arquivo: é sempre ao vivo. Só vira
  arquivo o dado que a própria fonte não atualiza mais rápido que nosso ciclo.

### Por que isso não gera "dado desatualizado"

O único dado que vai para um arquivo preparado é histórico agregado. O ISP
publica suas estatísticas ~uma vez por mês; não existe versão "mais fresca" para
ficarmos atrás. Se o job de preparo rodar mensalmente, estamos tão atualizados
quanto a fonte. E mesmo um atraso eventual quase não afeta o resultado, porque o
baseline é uma média de 12–24 meses — um mês a mais ou a menos mal move o número.

### O que é o job de preparo ("ETL") e quem o roda

ETL = *Extract, Transform, Load* (extrair, transformar, carregar). No nosso
contexto é apenas **um script Python que nós escrevemos** (`sinal_aberto/ingest/`)
e que roda **fora do servidor**:

- **Quem dispara:** no desenvolvimento, você, na mão, quando quiser atualizar os
  dados. Em produção, um agendador (cron da hospedagem, GitHub Action agendada,
  ou sua máquina) na frequência em que a fonte muda (ex.: mensal para o ISP).
- **Quando roda:** por agendamento/manual, **nunca** no momento em que o usuário
  faz uma pergunta. Se rodasse por consulta, cada pergunta baixaria megabytes e
  parsearia CSV — lento e frágil. O servidor só lê o resultado já pronto.
- **O que produz:** linhas pequenas e numéricas no armazenamento de referência
  (ex.: `(3304557, "ISP", "disparos_arma_fogo", 2024, 3, 87.0)`), no lugar de um
  CSV de megabytes.

```
JOB DE PREPARO (offline, ~mensal)         SERVIDOR MCP (online, por consulta)
você/agendador dispara                    usuário/agente dispara
extrai → transforma → carrega   ───────►  lê o resultado pronto → responde JSON
lento, pesado, tudo bem                   rápido, leve, só leitura
```

## Armazenamento: comece sem banco, adicione quando precisar

A decisão de persistência segue a natureza do dado, e o SQLite é **adiado até
algo realmente precisar de SQL**:

1. **Vivo crítico e referência estável** → cache em memória por instância. É o
   que o projeto já faz com o Fogo Cruzado. Sem arquivo, sem banco. Cache não é
   fraqueza para demanda: quando muitos usuários perguntam da mesma cidade no
   mesmo minuto, o cache absorve o pico e protege a API de origem (1 chamada em
   vez de N). Cache compartilhado (ex.: Redis) só quando rodarmos muitas
   instâncias e **medirmos** necessidade — não antes.
2. **Histórico agregado (ISP/SINESP)** → arquivo preparado pelo job. O formato
   pode ser **JSON empacotado** no deploy (mais simples) ou **SQLite** (quando
   quisermos consultas SQL). Começamos pelo mais simples.
3. **SQLite entra de fato** quando chegar a camada de clusters
   (`get_active_clusters`, `estimate_*` em `docs/ferramentas-mcp.md`), que se
   beneficia de consultas indexadas e de estado computado persistido. Aí o banco
   ganha seu lugar — e como será **só leitura em runtime** (escrito pelo job,
   lido pelo servidor), continua sendo um **arquivo embutido no deploy**, sem
   servidor de banco gerenciado, sem volume persistente, custo ~zero.

> Se um dia surgir necessidade de estado mutável compartilhado entre instâncias,
> existe o **Turso/libSQL** (SQLite gerenciado na nuvem, free tier generoso) sem
> virar Postgres. É problema futuro; hoje não precisamos.

### Esquema de referência (quando o arquivo preparado existir)

Quando chegarmos ao baseline (e, depois, aos clusters), o armazenamento de
referência terá esta forma. Vale tanto para JSON empacotado quanto para tabelas
SQLite; abaixo na forma SQL por clareza.

```sql
-- Histórico agregado (de ISP/SINESP), preparado pelo job offline
CREATE TABLE baseline_mensal (
    ibge_municipio   INTEGER NOT NULL,     -- chave de junção universal
    fonte            TEXT NOT NULL,         -- "ISP" | "SINESP"
    indicador        TEXT NOT NULL,         -- ex.: "disparos_arma_fogo"
    ano              INTEGER NOT NULL,
    mes              INTEGER,               -- NULL = agregado anual
    valor            REAL NOT NULL,
    unidade          TEXT NOT NULL,         -- ex.: "ocorrencias"
    PRIMARY KEY (ibge_municipio, fonte, indicador, ano, mes)
);

-- Rastreabilidade do job (idempotência: pular se nada mudou)
CREATE TABLE ingestao_meta (
    fonte             TEXT NOT NULL,
    recurso_id        TEXT NOT NULL,
    hash              TEXT,
    baixado_em        TEXT NOT NULL,        -- ISO 8601 UTC
    metadata_modified TEXT,                 -- da própria fonte, quando houver
    linhas            INTEGER,
    PRIMARY KEY (fonte, recurso_id)
);
```

O **IBGE território não tem tabela**: vem ao vivo da API e fica num cache em
memória (estrutura por slug de município e UF para resolução). Só seria
materializado se quiséssemos um fallback offline — decisão para depois.

A estatística de base (média e dispersão por município/indicador numa janela de
12–24 meses) é calculada a partir de `baseline_mensal`, sob demanda. Materializar
numa `baseline_stats` só se o custo aparecer.

## Chave de junção universal: código IBGE do município

Tudo que é histórico/referência se liga pelo **código IBGE de 7 dígitos**. Por
isso a normalização (Tier 1) vem antes de tudo: sem ela, ISP/SINESP/população não
casam de forma confiável com a cidade que o usuário pediu.

## Camada de enriquecimento opcional

O fluxo do `get_recent_activity` ganha uma etapa de enriquecimento **depois** da
consulta principal ao Fogo Cruzado. Cada enriquecimento é independente e
tolerante a falha: se a fonte estiver fora, o campo vem nulo e uma limitação é
registrada — a resposta principal nunca quebra.

```
city/region
   -> resolver território (Tier 1, IBGE ao vivo + cache)  -> territorial_context
   -> Fogo Cruzado (já existe)                             -> recent_occurrences, evidence
   -> baseline histórico (Tier 2, arquivo preparado)       -> historical_baseline
   -> corroboração COR.Rio (Tier 3, ao vivo + cache)       -> corroborating_reports
   -> anomalia de trânsito (Tier 4, ao vivo, exp.)         -> experimental_signals
   -> montar resposta + limitações + fontes
```

## Modelo de dados

Novos submodelos Pydantic em `sinal_aberto/models.py`. Todos os campos novos no
`RecentActivityResult` são **opcionais** (default `None`/vazio), preservando
compatibilidade.

```python
class TerritorialContext(BaseModel):
    ibge_city_code: int | None = None
    resolved_name: str | None = None       # nome canônico do município
    uf: str | None = None
    macro_region: str | None = None        # ex.: "Sudeste"
    population: int | None = None
    match_quality: str                     # "exato" | "aproximado" | "ambiguo"

class HistoricalBaseline(BaseModel):
    indicator: str                         # ex.: "disparos de arma de fogo"
    period_label: str                      # ex.: "média mensal 2023-2024"
    monthly_average: float | None = None
    current_window_count: int = 0          # mesma métrica, comparável
    relative_level: str                    # "abaixo" | "tipico" | "acima" | "muito acima" | "indeterminado"
    per_100k: float | None = None          # normalizado por população
    source: str
    as_of: datetime | None = None

class CorroboratingReport(BaseModel):
    title: str
    area: str | None = None
    summary: str | None = None
    published_at: datetime | None = None
    source: str = "COR.Rio"
    url: str | None = None

class TransitAnomaly(BaseModel):           # experimental, baixo peso
    area: str | None = None
    expected_vehicles: int | None = None
    observed_vehicles: int | None = None
    deviation_level: str                   # "normal" | "reduzido" | "ausente" | "indeterminado"
    note: str
```

Campos adicionados a `RecentActivityResult`:

```python
    territorial_context: TerritorialContext | None = None
    historical_baseline: HistoricalBaseline | None = None
    corroborating_reports: list[CorroboratingReport] = Field(default_factory=list)
    experimental_signals: list[TransitAnomaly] = Field(default_factory=list)
```

## Detalhamento por tier

### Tier 1 — IBGE Localidades (normalizar) — sem infra nova

- **Mecanismo:** API ao vivo + cache longo em memória. **Sem job, sem banco.**
  Mesmo molde do cache de cidades do `FogoCruzadoClient`.
- **Formato:** JSON REST, `application/json`. Chave inteira `id`; hierarquia
  município > microrregião > mesorregião > UF.
- **O que entrega:** `territorial_context` na resposta; resolve e desambigua a
  cidade pedida, devolvendo nome canônico, UF, macrorregião e (quando houver)
  população.
- **Corrige um bug atual:** a desambiguação de cidade hoje é frágil
  (`recent_activity.py` casa por substring sobre o catálogo do Fogo Cruzado). Com
  o território oficial, casamos por slug normalizado + UF.
- **Efeito na saída:** descritivo. Não altera evidência nem confiança.

### Tier 2 — Baseline histórico (linha de base) — arquivo preparado

- **Mecanismo:** job offline (`ingest_baseline_isp.py`, depois
  `ingest_baseline_sinesp.py`) produz `baseline_mensal`; o servidor só lê.
- **Fontes:** ISP Dados RJ (CSV) para o Rio; SINESP/MJSP (XLSX) para o recorte
  nacional. População (IBGE/SIDRA, no job) para normalizar por 100 mil
  habitantes.
- **O que entrega:** `historical_baseline` — média mensal histórica do indicador
  comparável, nível relativo da janela atual e taxa por 100k.
- **Comparabilidade (cuidado central):** o Fogo Cruzado conta
  tiroteios/disparos reportados; o indicador histórico precisa ser escolhido para
  casar conceitualmente. A janela atual é de minutos/horas; o baseline é mensal.
  Comparação honesta só é significativa em **janelas longas (>= 24h)**. Para
  janelas curtas, apresentar o baseline como contexto mensal, não como afirmação
  de "elevado agora". Documentar como limitação explícita na resposta.
- **Efeito na saída:** introduz um eixo novo — `relative_level` (anomalia) —
  separado de `evidence_level` (existência do sinal). Não inflar evidência com
  base em histórico.
- **Natureza:** dado histórico/agregado, nunca tempo real.

### Tier 3 — COR.Rio (corroborar, texto) — ao vivo

- **Mecanismo:** API ao vivo + cache curto. **Sem job, sem banco.**
- **Formato:** WordPress REST em JSON; RSS em XML. Exige **headers de
  navegador** (WAF `server: hcdn` responde 403 sem eles) — já resolvido e testado
  em `tests/integration/test_cor_rio.py`.
- **O que entrega:** `corroborating_reports` — boletins oficiais recentes
  (operação, fechamento de via) que mencionem a região/horário consultados.
- **Casamento:** filtrar posts por recência e por correspondência textual com a
  cidade/região (e, quando possível, bairro). Resumo curto, sem reproduzir o
  texto inteiro.
- **Efeito na saída:** corroboração independente do Fogo Cruzado **sobe a
  confiança** (não a evidência), porque reduz a incerteza de que o sinal é real.
- **Peso:** baixo; é contexto oficial complementar.

### Tier 4 — GPS SPPO (sinal fraco, experimental) — ao vivo

- **Mecanismo:** API ao vivo, atrás de flag. **Sem job, sem banco.**
- **Formato:** JSON (Content-Type `text/html`, parsear como JSON mesmo assim);
  exige janela temporal curta; lat/long como string com vírgula decimal;
  timestamps em epoch ms.
- **O que entrega:** `experimental_signals` — ausência/redução anômala de ônibus
  numa área pode correlacionar com via fechada/incidente.
- **Ressalvas:** ruidoso; requer binning espacial para ser útil (mapear posição
  -> região), o que beira o geográfico — manter mínimo e marcado como
  experimental.
- **Efeito na saída:** nunca move o score sozinho; no máximo é nota de desempate.
- **Status:** opcional, pode ficar para depois sem prejuízo.

## Efeito no score: separação em duas fases

Para não misturar enriquecimento descritivo com lógica de avaliação:

**Fase A — enriquecimento descritivo (sem mexer no score).**
Adicionar os campos novos preenchidos, sem alterar `evidence_level` nem
`confidence_level`. O `_assess` atual continua dirigido só pelo Fogo Cruzado.
Baixo risco, entrega valor imediato, fácil de testar.

**Fase B — influência no score (regras explícitas e testáveis).**
Depois de A estabilizar:

- Corroboração COR.Rio na mesma região/janela -> sobe `confidence_level` um
  degrau.
- Baseline produz `relative_level` próprio; **não** altera `evidence_level`.
- Anomalia de trânsito entra apenas como sinal de desempate, com peso mínimo.

Cada regra vira teste unitário com entradas controladas, como o `_assess` atual.

## Degradação graciosa e atribuição

- Todo enriquecimento é try/except isolado: falha vira campo nulo + limitação,
  nunca erro da tool.
- Todo campo auxiliar carrega `source` e `as_of`/horário, mantendo a
  rastreabilidade exigida em `docs/ferramentas-mcp.md`.
- `list_data_sources` passa a refletir o estado real por tier: fontes promovidas
  de `validada, nao integrada` para `integrada` conforme entram.

## Hospedagem (resumo)

O servidor é **sem estado**: cada instância é idêntica e descartável. Os dados
de referência (quando existirem em arquivo) são só leitura e viajam embutidos no
deploy; quando os dados mudam, o job gera um arquivo novo e redeployamos. Não há
servidor de banco gerenciado, nem volume persistente, nem estado por usuário.
Isso torna o serviço o mais barato e escalável possível para um connector pesado
em leitura. Plataformas adequadas: container Python em Render/Fly/Railway
(always-on, ~US$5-7/mês, latência previsível) ou Cloud Run (escala a zero,
pague-por-uso, com cold start). Evitar Cloudflare Workers para Python+SQLite por
imaturidade. Decisão de plataforma fica para a hora do deploy; o código já é
agnóstico (FastMCP, Streamable HTTP).

## Roadmap de implementação

Ordem por valor/custo, cada passo entregável e testável de forma isolada
(unitários offline + integração quando tocar a rede):

1. **Tier 1 — território (normalização). Zero infra nova.**
   Adaptador IBGE com cache longo, `TerritorialContext`, resolução de
   cidade/região, campo na resposta. Corrige a ambiguidade atual. Sem job, sem
   banco, sem efeito no score.
   *Pronto quando:* a cidade pedida resolve para código IBGE + UF e a ambiguidade
   some nos testes.

2. **Tier 2 — baseline (ISP, depois SINESP). Estreia o arquivo preparado.**
   Job `ingest_baseline_isp.py`, `baseline_mensal` (JSON empacotado ou SQLite),
   `HistoricalBaseline`, eixo `relative_level`. Em seguida SINESP (nacional) e
   população para `per_100k`.
   *Pronto quando:* janela >= 24h reporta média histórica e nível relativo
   atribuídos, com limitação clara para janelas curtas.

3. **Tier 3 — COR.Rio (corroboração textual). Ao vivo.**
   Cliente com headers de navegador, casamento por região/recência,
   `CorroboratingReport`. Fase B: corroboração sobe confiança.
   *Pronto quando:* boletins relevantes aparecem atribuídos e a regra de
   confiança tem teste.

4. **Tier 4 — GPS SPPO (experimental). Ao vivo, atrás de flag.** Opcional.

Em paralelo, `list_data_sources` é atualizada a cada promoção de fonte. O SQLite
só é introduzido de fato no Tier 2 (se preferirmos a ele em vez de JSON) ou na
posterior camada de clusters.

## Decisões em aberto

- **Indicador histórico do Tier 2:** qual indicador do ISP/SINESP melhor casa com
  "tiroteios/disparos" do Fogo Cruzado (ex.: disparos de arma de fogo vs.
  homicídio doloso). Decidir ao inspecionar o dicionário de dados.
- **Formato do arquivo preparado do Tier 2:** JSON empacotado (mais simples) vs.
  SQLite (SQL desde já). Recomendação: começar por JSON e migrar para SQLite
  quando a camada de clusters chegar.
- **População via SIDRA:** usar apenas **offline**, no job, para gerar a coluna
  `populacao`; sem dependência de outro serviço na consulta.
- **Plataforma de hospedagem:** definir na hora do deploy; código mantido
  agnóstico.
