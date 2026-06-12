# Ferramentas MCP do Sinal Aberto

Atualizado em: **2026-06-12**.

Este documento descreve a proposta inicial de ferramentas MCP públicas do Sinal Aberto. As ferramentas devem expor capacidades de produto, não detalhes internos da API Fogo Cruzado.

Endpoints como `GET /states`, `GET /cities` e `GET /occurrences` devem ficar encapsulados no adaptador interno de dados. O MCP deve oferecer respostas orientadas a contexto, confiança, fonte, horário e limitações.

## Princípios

- Retornar evidências e incertezas, não afirmações absolutas.
- Evitar precisão operacional sensível.
- Preferir bairro, região e cluster a coordenadas exatas em respostas finais.
- Sempre informar fonte, horário de consulta e, quando disponível, horário de última atualização.
- Reduzir confiança quando os dados forem escassos, antigos ou inconsistentes.
- Não sugerir rotas, desvios, fuga, aproximação de agentes ou decisões táticas.

## Ferramentas propostas

O contrato inicial deve ter **6 ferramentas públicas**:

1. `get_recent_activity`
2. `get_active_clusters`
3. `estimate_activity_probability`
4. `estimate_public_impact`
5. `explain_assessment`
6. `list_data_sources`

## 1. `get_recent_activity`

Consulta sinais recentes de atividade armada ou policial em uma cidade, bairro ou região.

### Entrada

```text
city: string
region: string | null
time_window: string
```

Exemplos de `time_window`:

```text
30m
1h
3h
6h
24h
```

### Saída

```text
city
region
time_window
query_time
source_update_time
activity_summary
evidence_level
confidence_level
recent_occurrences[]
limitations[]
sources[]
```

### Descrição

Esta deve ser a ferramenta mais simples do MVP. Ela consulta dados recentes, normaliza os registros e retorna um resumo rastreável dos sinais encontrados.

Deve incluir:

- quantidade de ocorrências recentes;
- recência da ocorrência mais nova;
- bairros/localidades envolvidos;
- presença de ação policial;
- presença de agentes;
- vítimas reportadas;
- transporte afetado;
- fonte e horário de atualização.

## 2. `get_active_clusters`

Lista clusters recentes em uma cidade dentro de uma janela temporal.

### Entrada

```text
city: string
time_window: string
```

### Saída

```text
city
time_window
query_time
clusters[]
sources[]
limitations[]
```

Cada item de `clusters[]` deve conter:

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

### Descrição

Agrupa ocorrências por proximidade temporal e geográfica para evitar respostas baseadas em eventos isolados demais.

No MVP, a clusterização pode ser feita no código da aplicação e salva em SQLite para evitar recalcular tudo a cada pergunta.

## 3. `estimate_activity_probability`

Estima a faixa de probabilidade de atividade armada ou policial recente em uma região.

### Entrada

```text
location: string
radius: number | null
time_window: string
```

`location` deve aceitar bairro, região ou localidade. Latitude/longitude pode ser suportada internamente, mas a resposta pública deve evitar precisão sensível.

### Saída

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

### Faixas sugeridas

```text
baixa evidência
evidência moderada
alta evidência
evidência muito alta
```

### Descrição

Calcula uma classificação probabilística com base em recência, concentração de ocorrências, ação policial, presença de agentes, histórico local e sinais complementares.

A saída não deve prometer que uma operação está em andamento. Deve expressar evidência recente e incerteza.

## 4. `estimate_public_impact`

Estima o impacto provável de um cluster específico para a população.

### Entrada

```text
cluster_id: string
```

### Saída

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

### Faixas sugeridas

```text
baixo impacto reportado
médio impacto reportado
alto impacto reportado
crítico
```

### Descrição

Separa gravidade pública de probabilidade de atividade atual. Um cluster pode ter alta evidência de atividade recente, mas impacto reportado baixo, ou o inverso.

Deve considerar:

- vítimas feridas;
- mortes;
- múltiplas ocorrências próximas;
- interrupção de transporte;
- duração aproximada;
- dispersão geográfica;
- presença de operação policial.

## 5. `explain_assessment`

Explica a classificação atribuída a um cluster.

### Entrada

```text
cluster_id: string
```

### Saída

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

### Descrição

Fornece explicabilidade para o usuário e para o modelo cliente. Deve mostrar quais sinais sustentam a avaliação e quais fatores reduzem a confiança.

Exemplos de sinais:

- ocorrência muito recente;
- múltiplos registros próximos;
- ação policial marcada;
- presença de agentes;
- vítimas reportadas;
- transporte interrompido;
- ausência de confirmação oficial de continuidade;
- dados antigos ou escassos.

## 6. `list_data_sources`

Lista fontes de dados usadas pelo sistema e seu estado operacional.

### Entrada

```text
none
```

### Saída

```text
sources[]
query_time
limitations[]
```

Cada item de `sources[]` deve conter:

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

### Descrição

Ajuda a manter rastreabilidade e transparência. A primeira versão deve listar Fogo Cruzado como fonte principal e marcar ISP Dados, SINESP, IBGE, DATA.RIO e transporte como fontes complementares planejadas ou parcialmente integradas, conforme o estado real do sistema.

## Priorização de implementação

### MVP inicial

1. `list_data_sources`
2. `get_recent_activity`
3. `get_active_clusters`

### MVP com score inicial

4. `estimate_activity_probability`
5. `estimate_public_impact`

### MVP explicável

6. `explain_assessment`

## Observação de implementação

As ferramentas que usam `cluster_id` dependem da camada de clusterização e persistência local. Antes delas, o backend precisa:

- autenticar na API Fogo Cruzado;
- consultar estados, cidades e ocorrências;
- normalizar ocorrências em SQLite;
- guardar metadados de fonte e atualização;
- calcular clusters recentes;
- calcular score inicial de atividade e impacto.

