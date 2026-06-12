# API Fogo Cruzado

## Base do MVP

A API oficial do Fogo Cruzado esta na versao 2.0 e usa a base:

```text
https://api-service.fogocruzado.org.br/api/v2
```

A autenticacao usa JWT. O login e feito por `POST /auth/login` com:

```json
{
  "email": "seu@email",
  "password": "sua senha"
}
```

O token retornado em `data.accessToken` deve ser enviado nos endpoints como:

```text
Authorization: Bearer <token>
```

## Endpoints priorizados

- `GET /states`: lista estados monitorados.
- `GET /cities`: lista cidades, com filtros opcionais por `cityId`, `cityName` e `stateId`.
- `GET /occurrences`: endpoint principal de ocorrencias. Na validacao pratica da API, `idState` e obrigatorio. Aceita paginacao por `page` e `take`, ordenacao por `order`, filtros por cidades e filtros por data como `initialdate` e `finaldate`.

## Variaveis de ambiente

Para rodar a suite de integracao local, crie um `.env` com:

```text
FOGOCRUZADO_EMAIL=seu@email
FOGOCRUZADO_PASSWORD=sua_senha
```

Opcionalmente, a URL base pode ser sobrescrita:

```text
FOGOCRUZADO_API_BASE_URL=https://api-service.fogocruzado.org.br/api/v2
```

Os testes tambem aceitam aliases legados para facilitar uso local:

- `FOGO_CRUZADO_EMAIL`
- `FOGOCRUZADO_USER`
- `FOGO_CRUZADO_USER`
- `FOGO_CRUZADO_PASSWORD`

Como compatibilidade local, se esses nomes explicitos nao existirem, os testes tambem aceitam `EMAIL`, `USER`, `USERNAME`, `email`, `user` ou `username` e `PASSWORD`, `PASS`, `password` ou `pass`, mas apenas quando vierem do arquivo `.env`.

## Testes de acesso

Execute:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration -m integration
```

Os testes validam:

- login e retorno de `data.accessToken`;
- contrato minimo de `/states`;
- contrato minimo de `/cities`;
- contrato minimo de `/occurrences`.

Eles nao imprimem usuario, senha nem token. Se as credenciais nao estiverem configuradas, a suite e pulada.
