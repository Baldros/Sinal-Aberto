# Sinal Aberto

**Sinal Aberto** é uma proposta de assistente de inteligência urbana para estimar, de forma probabilística e transparente, sinais recentes de atividade armada ou policial em uma região e seu possível impacto para a população.

O projeto nasce com foco em cidades brasileiras com desafios graves de segurança pública, especialmente o Rio de Janeiro, e parte de uma premissa simples: o cidadão comum precisa de informação contextual, rastreável e responsável para entender melhor o que está acontecendo ao seu redor.

> O Sinal Aberto não pretende ser um radar absoluto de operações policiais, nem uma fonte oficial de emergência. A proposta é interpretar dados públicos e sinais recentes para indicar evidências, incertezas e impacto provável em tempo quase real.

## Documentos do projeto

- [OpenAI Apps SDK](docs/openai-apps-sdk.md): resumo dos conceitos básicos do SDK oficial da OpenAI, links úteis e caminho sugerido para transformar o Sinal Aberto em app do ChatGPT e servidor MCP aberto.
- [Stack técnica e hospedagem](docs/stack-e-hospedagem.md): decisão atual de começar com MVP leve em Python/FastMCP + SQLite, mantendo PostgreSQL/PostGIS e Redis como evolução.
- [Fontes de dados](docs/fontes-de-dados.md): fontes priorizadas, forma de acesso e papel de cada base no produto.
- [API Fogo Cruzado](docs/fogocruzado-api.md): base oficial da API v2, autenticacao, endpoints priorizados e testes de integracao.
- [Ferramentas MCP](docs/ferramentas-mcp.md): proposta de ferramentas públicas do servidor MCP, descrições, entradas, saídas e priorização.

## Visão do produto

A ideia inicial é construir um app para o ChatGPT capaz de responder perguntas como:

- Há sinais recentes de operação policial ou atividade armada em alguma região da cidade?
- Quais áreas têm maior evidência de atividade recente neste momento?
- Qual é o nível provável de impacto para a população?
- A informação vem de qual fonte, com qual horário de atualização e com qual nível de confiança?
- O evento parece isolado ou faz parte de um cluster de ocorrências próximas no tempo e no espaço?

A longo prazo, o Sinal Aberto pode evoluir para uma camada aberta de utilidade pública, disponível não apenas no ChatGPT, mas também em outros chatbots, aplicativos cívicos, painéis públicos e integrações via MCP.

## Tese central

O problema não deve ser tratado de forma determinística.

Em vez de afirmar que existe ou não existe uma operação em andamento, o Sinal Aberto deve estimar:

1. **Probabilidade de atividade atual**  
   Estimativa de que há atividade armada ou policial recente ainda relevante em determinada região.

2. **Impacto provável para a população**  
   Estimativa do efeito prático do evento para moradores, trabalhadores e pessoas em deslocamento.

3. **Nível de confiança**  
   Grau de robustez da resposta, considerando fonte, recência, consistência dos sinais e histórico local.

4. **Explicabilidade**  
   A resposta deve mostrar quais sinais levaram à classificação: recência, concentração de ocorrências, vítimas, presença policial, interrupções de transporte, histórico da região etc.

## Exemplo de resposta desejada

> Há alta evidência de atividade armada/policial recente na região do Complexo do Alemão. Foram identificados registros próximos nos últimos 45 minutos, incluindo indicação de ação policial e presença de agentes. O impacto estimado é alto, principalmente pela concentração temporal dos registros e pelo histórico da região.  
>  
> Confiança: moderada.  
> Limitação: os dados indicam ocorrências recentes, mas não confirmam oficialmente que a operação segue em andamento.

## Métricas propostas

### 1. Probabilidade de atividade atual

Uma métrica para estimar se um evento recente ainda pode estar ativo ou relevante.

Sinais possíveis:

- Minutos desde a última ocorrência.
- Número de ocorrências próximas nas últimas horas.
- Ocorrência marcada como ação policial ou operação policial.
- Presença de agentes.
- Unidade policial identificada.
- Cluster geográfico e temporal.
- Histórico da área para ocorrências semelhantes.
- Probabilidade histórica de continuidade após o primeiro registro.

Exemplo conceitual:

```text
score_atividade =
  recencia
+ cluster_recente
+ indicador_operacao_policial
+ presenca_agentes
+ historico_local
+ fontes_complementares
```

A saída não precisa ser exibida como percentual exato. Pode ser apresentada em faixas:

- Baixa evidência.
- Evidência moderada.
- Alta evidência.
- Evidência muito alta.

### 2. Impacto provável

Uma métrica separada para estimar a gravidade ou intensidade do impacto público.

Sinais possíveis:

- Vítimas feridas.
- Mortes.
- Múltiplas ocorrências próximas.
- Duração estimada do cluster.
- Dispersão geográfica.
- Interrupção de transporte.
- Horário de alta circulação.
- Histórico local de letalidade ou recorrência.
- Presença de operação policial.

Faixas possíveis:

- Baixo impacto reportado.
- Médio impacto reportado.
- Alto impacto reportado.
- Crítico.

## Unidade de análise: clusters

O Sinal Aberto deve evitar analisar ocorrências isoladas de forma excessivamente literal.

A unidade principal deve ser o **cluster ativo**, ou seja, um conjunto de ocorrências relacionadas por:

- proximidade geográfica;
- janela temporal;
- bairro, comunidade ou localidade;
- tipo de evento;
- presença policial;
- sinais de continuidade.

Isso permite respostas mais úteis e menos frágeis do que simplesmente listar eventos individuais.

## Fontes de dados consideradas

### Fonte principal

#### Fogo Cruzado

- Site da API: https://api.fogocruzado.org.br/
- Documentação: https://api.fogocruzado.org.br/docs

O Fogo Cruzado é a fonte mais alinhada com a proposta inicial do Sinal Aberto. A API fornece dados atualizados sobre tiroteios e disparos de arma de fogo, incluindo regiões metropolitanas como Rio de Janeiro, Recife, Bahia e Pará. A documentação informa que a API possui metadados de última atualização e que as datas seguem o fuso de Brasília.

Pontos relevantes:

- Base voltada a violência armada.
- Ocorrências georreferenciadas.
- Potencial de consulta em tempo quase real.
- Dados sobre tiroteios, disparos, presença de agentes, ação/operação policial, vítimas e outros indicadores.
- Requer autorização prévia para uso da API.

### Fontes complementares

#### ISP Dados - Instituto de Segurança Pública do Rio de Janeiro

- Portal: https://www.ispdados.rj.gov.br/

Fonte oficial para bases de registros criminais e atividade policial do estado do Rio de Janeiro. Útil para histórico, contexto, validação estatística e construção de priors territoriais.

#### ISP Visualização / ISP Conecta

- Visualização de dados: https://www.ispvisualizacao.rj.gov.br/
- ISP Conecta: https://ispconecta.rj.gov.br/

Pode ser usado para painéis, contexto territorial e análise pública de indicadores de segurança.

#### SINESP / Ministério da Justiça e Segurança Pública

- Portal de dados: https://dados.mj.gov.br/dataset/sistema-nacional-de-estatisticas-de-seguranca-publica

Fonte nacional de indicadores de segurança pública. Útil para análise agregada, comparação territorial e contexto histórico, mas não deve ser tratada como fonte principal de tempo real.

#### DATA.RIO

- Portal: https://www.data.rio/

Fonte relevante para camadas urbanas, bases geográficas, bairros, limites territoriais, equipamentos públicos e enriquecimento geoespacial da aplicação.

#### Outras fontes potenciais

- Dados de transporte público e trânsito.
- Comunicados oficiais de órgãos públicos.
- Fontes jornalísticas verificadas.
- Bases municipais de ocorrências, serviços e infraestrutura urbana.
- Relatos públicos, quando houver metodologia robusta de verificação e controle de boatos.

## Princípios de produto

1. **Probabilístico, não determinístico**  
   O sistema estima evidências e probabilidades, sem prometer confirmação absoluta.

2. **Explicável**  
   Toda resposta deve informar os principais fatores que levaram à classificação.

3. **Rastreável**  
   Toda afirmação deve indicar fonte, horário de consulta e, quando possível, horário de última atualização dos dados.

4. **Conservador por padrão**  
   Na dúvida, o sistema deve reduzir a confiança da resposta em vez de exagerar a certeza.

5. **Útil para o cidadão comum**  
   A linguagem deve ser clara, direta e orientada a contexto, não a jargão técnico.

6. **Responsável e não operacional**  
   O projeto não deve ajudar usuários a burlar operações, localizar agentes com precisão sensível ou tomar decisões táticas perigosas.

7. **Privacidade por padrão**  
   O sistema deve evitar armazenar localização precisa do usuário sem necessidade clara.

## Limitações assumidas

- Não há garantia de cobertura completa de todas as operações policiais.
- Ocorrências podem entrar na base com atraso.
- Uma ocorrência recente não prova que o evento continua ativo.
- Dados colaborativos podem exigir validação, correção ou atualização posterior.
- Fontes oficiais podem ter defasagem temporal.
- A classificação de impacto é uma estimativa, não uma confirmação oficial.

## Arquitetura pretendida

### Decisão de MVP

O MVP inicial deve privilegiar **segurança, leveza e baixo custo operacional**.

Para começar, a arquitetura preferida é:

- servidor MCP em Python com FastMCP;
- persistência local simples com SQLite;
- cache curto em memória ou tabela SQLite;
- consultas à API do Fogo Cruzado por adaptador isolado;
- score probabilístico e clusterização inicial no código da aplicação;
- sem login de usuário na primeira versão, se possível.

PostgreSQL/PostGIS e Redis continuam sendo a rota natural de evolução quando houver necessidade real de consultas geoespaciais complexas, maior concorrência, histórico amplo, dashboard público ou múltiplas instâncias escrevendo no mesmo banco.

### Fase 1: app para ChatGPT

- GPT customizado ou app no ChatGPT.
- Integração com backend próprio.
- Consulta a fontes externas via API.
- Respostas em linguagem natural com fonte, horário, confiança e explicação.

### Fase 2: backend de dados

- Proxy para a API do Fogo Cruzado e fontes complementares.
- Cache leve e controle de atualização.
- Banco SQLite no MVP, com caminho de migração para PostgreSQL/PostGIS.
- Normalização geográfica.
- Detecção de clusters inicialmente no código da aplicação.
- Cálculo de probabilidade de atividade atual.
- Cálculo de impacto provável.
- Logs mínimos e política de privacidade.

### Fase 3: MCP aberto

O Sinal Aberto deve evoluir para um servidor MCP aberto, permitindo que outros chatbots e assistentes consultem a mesma camada de inteligência urbana.

Possíveis ferramentas MCP:

- `get_recent_activity(city, region, time_window)`
- `get_active_clusters(city, time_window)`
- `estimate_activity_probability(location, radius, time_window)`
- `estimate_public_impact(cluster_id)`
- `explain_assessment(cluster_id)`
- `list_data_sources()`

### Fase 4: expansão para múltiplos canais

- ChatGPT.
- Outros chatbots compatíveis com MCP.
- API pública.
- Dashboard web.
- Integrações com projetos jornalísticos, cívicos e acadêmicos.

## Roadmap inicial

- [ ] Solicitar autorização de uso da API do Fogo Cruzado.
- [ ] Validar limites, termos de uso, cache, atribuição e possibilidade de uso público.
- [ ] Criar backend mínimo em Python/FastMCP para consulta de ocorrências recentes.
- [ ] Definir schema SQLite inicial para ocorrências, clusters e cache.
- [ ] Mapear campos relevantes da API.
- [ ] Definir primeira versão do score probabilístico.
- [ ] Implementar agrupamento por clusters temporais e geográficos no código da aplicação.
- [ ] Criar respostas explicáveis em linguagem natural.
- [ ] Construir protótipo como app/GPT do ChatGPT.
- [ ] Documentar limitações, política de privacidade e disclaimers.
- [ ] Especificar servidor MCP aberto.

## Disclaimer

O Sinal Aberto é uma proposta de ferramenta de informação pública. Ele não substitui canais oficiais, serviços de emergência ou orientações de autoridades competentes.

Em situações de risco imediato, procure abrigo seguro e acione os canais oficiais de emergência.

## Status

Projeto em fase inicial de concepção e validação de dados.
