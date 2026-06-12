# API Fogo Cruzado

Atualizado em: **2026-06-12**.

Este documento resume a documentação oficial da API Fogo Cruzado v2 para orientar a implementação do Sinal Aberto. A API deve ser tratada como integração externa crítica: todo acesso precisa de autenticação, timeout, tratamento de erro, cache curto e registro de metadados de fonte.

Referências oficiais:

- Introdução: https://api.fogocruzado.org.br/docs
- Autenticação: https://api.fogocruzado.org.br/docs/auth
- Endpoints: https://api.fogocruzado.org.br/docs/endpoint
- Estados: https://api.fogocruzado.org.br/docs/endpoint/states
- Cidades: https://api.fogocruzado.org.br/docs/endpoint/cities
- Ocorrências: https://api.fogocruzado.org.br/docs/endpoint/occurrences

## Base da API

A documentação oficial da versão 2.0 usa a base:

```text
https://api-service.fogocruzado.org.br/api/v2
```

A página de endpoints informa três endpoints de dados:

- `GET /states`
- `GET /cities`
- `GET /occurrences`

Além deles, a página de autenticação documenta:

- `POST /auth/login`
- `POST /auth/refresh`

## Cobertura territorial e tempo

Segundo a introdução oficial, a API fornece dados atualizados sobre tiroteios e disparos de arma de fogo nas regiões metropolitanas monitoradas pelo Fogo Cruzado, incluindo Rio de Janeiro, Recife, Bahia e Pará, com diferentes datas históricas de início por região.

A documentação também informa que:

- as datas e horários retornados pela API devem ser interpretados no fuso de Brasília (`America/Sao_Paulo`, UTC-3);
- a API retorna metadados de última atualização em headers HTTP;
- `X-Last-Update` indica a última atualização geral das ocorrências;
- `X-Last-Update-State` indica a última atualização específica por estado quando aplicável.

Esses headers devem ser persistidos junto com os dados consultados para rastreabilidade e cache.

## Autenticação

### `POST /auth/login`

Uso: obter token JWT de acesso.

Request:

```json
{
  "email": "seu@email",
  "password": "sua senha"
}
```

Resposta esperada:

- HTTP `201`;
- `code: 201`;
- `data.accessToken`;
- `data.expiresIn`, em segundos.

O token retornado deve ser enviado nos demais endpoints como Bearer token:

```text
Authorization: Bearer <accessToken>
```

### `POST /auth/refresh`

Uso: renovar token antes do vencimento.

Request:

- método `POST`;
- header `Authorization: Bearer <accessToken>` com token ainda válido.
- na validação prática da API em 2026-06-12, também foi necessário enviar o token no corpo como `{"accessToken": "<accessToken>"}`; implementar o cliente com esse corpo para alinhar com o comportamento real.

Resposta esperada:

- HTTP `201`;
- `code: 201`;
- novo `data.accessToken`;
- novo `data.expiresIn`.

### Regras de implementação

- Nunca registrar email, senha ou token em logs.
- Carregar credenciais apenas de variáveis de ambiente ou secret manager.
- Renovar o token antes de `expiresIn` quando possível.
- Em `401` ou token expirado, tentar refresh uma vez; se falhar, fazer novo login.
- Em falhas repetidas de autenticação, retornar erro controlado para a camada MCP, sem vazar detalhes sensíveis.

## Endpoints de dados

Todos os endpoints de dados devem ser chamados com Bearer token.

### `GET /states`

Uso: listar estados monitorados.

Parâmetros documentados: nenhum.

Resposta esperada:

```text
msg
msgCode
code
data[]
```

Cada item de `data` deve conter, no mínimo:

```text
id
name
```

Uso no Sinal Aberto:

- descobrir `idState` para chamadas de ocorrências;
- manter tabela local de estados monitorados;
- relacionar cache e metadados por estado.

### `GET /cities`

Uso: listar cidades monitoradas.

Filtros documentados:

```text
cityId
cityName
stateId
```

Resposta esperada:

```text
msg
msgCode
code
data[]
```

Cada item de `data` deve conter, no mínimo:

```text
id
name
state.id
state.name
```

Uso no Sinal Aberto:

- mapear nome de cidade para `id`;
- filtrar ocorrências por cidade;
- montar cache local de cidades e estados;
- evitar ambiguidade em consultas por nome.

### `GET /occurrences`

Uso: consultar ocorrências. Este é o endpoint principal para o MVP.

Filtros e parâmetros documentados em exemplos oficiais:

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

Observações práticas:

- `idState` aparece nos exemplos oficiais e, na validação local, foi necessário para consultar ocorrências. Tratar `idState` como obrigatório no MVP.
- `idCities` pode aparecer repetido na query string para filtrar múltiplas cidades.
- `initialdate` e `finaldate` usam formato de data como `YYYY-MM-DD` nos exemplos oficiais.
- `order` deve ser tratado como ordenação temporal, usando `DESC` para consultas recentes.
- `page` e `take` controlam paginação.

Resposta esperada:

```text
msg
msgCode
code
pageMeta
data[]
```

`pageMeta` deve conter:

```text
page
take
itemCount
pageCount
hasPreviousPage
hasNextPage
```

Cada item de `data` representa uma ocorrência e pode conter:

```text
id
documentNumber
address
state
region
city
neighborhood
subNeighborhood
locality
latitude
longitude
date
policeAction
agentPresence
relatedRecord
contextInfo
transports
victims
animalVictims
```

Campos de maior valor para o Sinal Aberto:

- `date`: recência da ocorrência;
- `latitude` e `longitude`: agrupamento espacial;
- `state`, `city`, `neighborhood`, `subNeighborhood`, `locality`: normalização territorial;
- `policeAction`: sinal de ação/operação policial;
- `agentPresence`: presença de agentes;
- `contextInfo.mainReason`: motivo principal;
- `contextInfo.complementaryReasons`: motivos complementares;
- `contextInfo.clippings`: recortes relevantes;
- `contextInfo.massacre`: sinal de ocorrência crítica;
- `contextInfo.policeUnit`: unidade policial envolvida, quando informada;
- `transports`: impacto em transporte;
- `victims`: vítimas humanas;
- `animalVictims`: vítimas animais.

## Estrutura de `contextInfo`

`contextInfo` agrupa contexto da ocorrência.

Campos documentados:

```text
mainReason
complementaryReasons
clippings
massacre
policeUnit
```

Uso no score:

- `mainReason` e `complementaryReasons` ajudam a separar ação policial, operação policial, disputa, execução, tentativa de roubo e outros contextos;
- `clippings` ajuda a reconhecer recortes específicos, como feminicídio, perseguição, presídio, shopping, tiroteio contínuo e outros;
- `massacre` aumenta gravidade e reduz margem para respostas genéricas;
- `policeUnit` pode aumentar evidência de participação institucional, mas deve ser usado com cuidado para não produzir resposta operacional sensível.

As tabelas oficiais de motivos, recortes e qualificações ficam na página de ocorrências. A implementação deve evitar hardcode espalhado: se esses valores forem usados em regras, concentrar em uma camada de normalização testada.

## Estrutura de `transports`

`transports` informa impactos em transporte relacionados à ocorrência.

Campos documentados:

```text
id
occurrenceId
transport
interruptedTransport
dateInterruption
releaseDate
transportDescription
```

Uso no score:

- `interruptedTransport` é sinal direto de impacto público;
- `dateInterruption` e `releaseDate` ajudam a estimar se o impacto ainda pode estar ativo;
- `transportDescription` pode enriquecer a explicação, desde que a resposta não vire orientação tática de deslocamento.

## Estrutura de `victims`

`victims` informa vítimas humanas.

Campos documentados:

```text
id
occurrenceId
type
situation
circumstances
deathDate
personType
age
ageGroup
genre
race
place
serviceStatus
qualifications
politicalPosition
politicalStatus
partie
coorporation
agentPosition
agentStatus
unit
```

Uso no score:

- `situation` diferencia feridos e mortos;
- `personType`, `qualifications`, `agentStatus` e `serviceStatus` ajudam a entender se há civis, agentes de segurança, políticos ou outros perfis envolvidos;
- `deathDate` pode ajudar a separar ocorrência antiga de impacto ainda relevante;
- dados pessoais ou sensíveis devem ser usados apenas de forma agregada e responsável.

## Estrutura de `animalVictims`

`animalVictims` informa vítimas animais.

Campos documentados:

```text
id
occurrenceId
name
type
animalType
situation
circumstances
deathDate
```

Uso no MVP:

- armazenar sem descartar, para preservar contrato da API;
- não usar como sinal central do score inicial, salvo se a análise futura justificar.

## Estratégia de ingestão para o MVP

Fluxo recomendado:

1. Autenticar com `POST /auth/login`.
2. Renovar token com `POST /auth/refresh` quando necessário.
3. Sincronizar `GET /states`.
4. Sincronizar `GET /cities`, preferencialmente por `stateId` quando houver recorte.
5. Consultar `GET /occurrences` por `idState`, janela temporal e paginação.
6. Persistir headers `X-Last-Update` e `X-Last-Update-State` quando presentes.
7. Normalizar ocorrências em SQLite.
8. Pré-calcular ou cachear clusters recentes para evitar recalcular tudo a cada chamada MCP.

Para consultas recentes:

```text
GET /occurrences?order=DESC&page=1&take=20&idState=<state_id>&initialdate=<YYYY-MM-DD>&finaldate=<YYYY-MM-DD>
```

Para múltiplas cidades:

```text
GET /occurrences?order=DESC&page=1&take=20&idState=<state_id>&idCities=<city_id_1>&idCities=<city_id_2>
```

## Tratamento de erros e limites

Regras mínimas:

- configurar timeout explícito em todas as requisições;
- fazer retry apenas em falhas transitórias, com limite baixo;
- não fazer retry agressivo em `401`, `403` ou `4xx` de validação;
- registrar status code, endpoint, parâmetros não sensíveis e horário;
- nunca registrar token, email ou senha;
- retornar mensagens conservadoras quando a API estiver indisponível;
- preservar horário de consulta e headers de atualização para rastreabilidade.

## Variáveis de ambiente

Para rodar localmente:

```text
FOGOCRUZADO_EMAIL=seu@email
FOGOCRUZADO_PASSWORD=sua_senha
```

Opcionalmente:

```text
FOGOCRUZADO_API_BASE_URL=https://api-service.fogocruzado.org.br/api/v2
```

Aliases aceitos pela suíte atual de integração:

- `FOGO_CRUZADO_EMAIL`
- `FOGOCRUZADO_USER`
- `FOGO_CRUZADO_USER`
- `FOGO_CRUZADO_PASSWORD`

Como compatibilidade local, se esses nomes explícitos não existirem, os testes também aceitam `EMAIL`, `USER`, `USERNAME`, `email`, `user` ou `username` e `PASSWORD`, `PASS`, `password` ou `pass`, mas apenas quando vierem do arquivo `.env`.

## Cobertura de testes de integração

Execute:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration -m integration
```

Cobertura mínima que deve existir para considerar o acesso à API validado:

- `POST /auth/login`: retorna `data.accessToken` e `data.expiresIn`;
- `POST /auth/refresh`: renova token com Bearer token válido;
- `GET /states`: retorna lista com `id` e `name`;
- `GET /cities`: retorna lista com `id`, `name`, `state.id` e `state.name`;
- `GET /cities?cityId=...`: filtra por cidade;
- `GET /cities?cityName=...`: filtra por nome;
- `GET /cities?stateId=...`: filtra por estado;
- `GET /occurrences`: retorna `pageMeta` e lista de ocorrências;
- `GET /occurrences` com `initialdate` e `finaldate`: valida filtro temporal;
- `GET /occurrences` com múltiplos `idCities`: valida filtro por cidades;
- `GET /occurrences` com paginação: valida `page`, `take` e flags de `pageMeta`;
- headers `X-Last-Update` e `X-Last-Update-State`, quando presentes;
- contrato mínimo dos objetos `contextInfo`, `transports`, `victims` e `animalVictims`.

Os testes não devem imprimir usuário, senha nem token. Se credenciais não estiverem configuradas, a suíte deve ser pulada.

## Cobertura atual

A suíte de integração atual valida:

- login e retorno de token;
- refresh de token, incluindo o corpo `accessToken` exigido pela API real;
- contrato de `/states`;
- contrato de `/cities`;
- filtros de `/cities` por `cityId`, `cityName` e `stateId`;
- contrato de `/occurrences`;
- headers `X-Last-Update` e `X-Last-Update-State` em `/occurrences`;
- `pageMeta` e paginação de `/occurrences`;
- filtro temporal de `/occurrences` com `initialdate` e `finaldate`;
- filtro de `/occurrences` com múltiplos `idCities`;
- filtro `typeOccurrence=withVictim`;
- contrato mínimo de `contextInfo`;
- contrato mínimo de `transports`, `victims` e `animalVictims` quando essas listas vêm preenchidas.

Essa suíte ainda é de integração externa, não de regra de negócio do Sinal Aberto. Os testes de normalização, cache, persistência SQLite, clusterização e score probabilístico devem ser criados quando essas camadas existirem no código.
