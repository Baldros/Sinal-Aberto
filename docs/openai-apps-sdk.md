# OpenAI Apps SDK

Este documento resume o básico do **Apps SDK oficial da OpenAI** para orientar a evolução do Sinal Aberto como app dentro do ChatGPT.

A proposta aqui não é substituir a documentação oficial, mas registrar os pontos essenciais e manter os links principais para consulta posterior.

## Posicionamento para o Sinal Aberto

O Sinal Aberto foi pensado inicialmente como um app para o ChatGPT, mas a natureza do projeto aponta para algo maior: uma camada de utilidade pública acessível por múltiplos assistentes.

O caminho mais alinhado com isso é construir o Sinal Aberto como um **servidor MCP aberto**, consumido pelo ChatGPT via Apps SDK e, futuramente, por outros chatbots e clientes compatíveis com MCP.

Em termos práticos:

- o **backend/MCP server** concentra os dados, ferramentas, scores, regras de segurança e explicabilidade;
- o **ChatGPT app** usa esse servidor para responder perguntas e, se necessário, renderizar uma interface visual;
- outros chatbots podem usar a mesma camada MCP quando houver compatibilidade;
- a lógica pública do projeto não fica presa a um único cliente.

## O que é o Apps SDK

O **OpenAI Apps SDK** é o framework oficial para construir apps que estendem o ChatGPT.

Segundo a documentação oficial, apps criados com o Apps SDK usam o **Model Context Protocol (MCP)** para se conectar ao ChatGPT. Para criar um app, normalmente são necessários:

1. um **servidor MCP**, obrigatório, que define as capacidades do app como ferramentas;
2. opcionalmente, um **componente web**, renderizado em um iframe dentro do ChatGPT, caso o app precise de interface visual.

Links oficiais:

- Página principal do Apps SDK: https://developers.openai.com/apps-sdk
- Quickstart: https://developers.openai.com/apps-sdk/quickstart
- Referência: https://developers.openai.com/apps-sdk/reference
- Exemplos oficiais no GitHub: https://github.com/openai/openai-apps-sdk-examples

## Diferença entre GPT com Action e app com Apps SDK

### GPT com Action

Um GPT com Action é um caminho mais simples para MVPs. Ele permite conectar um GPT customizado a uma API externa por meio de um schema OpenAPI.

Pode ser útil para validar rapidamente:

- perguntas principais dos usuários;
- formato das respostas;
- utilidade dos dados;
- necessidade de filtros por cidade, bairro, raio e janela temporal.

Links oficiais:

- Introdução a Actions: https://platform.openai.com/docs/actions
- Actions em GPTs: https://help.openai.com/en/articles/9442513-gpt-actions
- Autenticação em Actions: https://platform.openai.com/docs/actions/authentication

### App com Apps SDK

O Apps SDK é mais adequado quando o produto precisa de:

- ferramentas MCP bem definidas;
- interface visual dentro do ChatGPT;
- componentes interativos;
- fluxo de publicação/revisão como app;
- arquitetura reaproveitável por outros clientes MCP;
- maior controle de estado, autenticação, UX e deploy.

Para o Sinal Aberto, o Apps SDK faz mais sentido na fase em que o projeto já tiver backend próprio, score probabilístico, endpoints estáveis e alguma experiência visual ou interativa.

## Componentes principais

### 1. Servidor MCP

O servidor MCP é a base do app.

Ele expõe ferramentas que o ChatGPT pode chamar para buscar dados, calcular métricas e explicar resultados.

Para o Sinal Aberto, ferramentas possíveis:

```text
get_recent_activity(city, region, time_window)
get_active_clusters(city, time_window)
estimate_activity_probability(location, radius, time_window)
estimate_public_impact(cluster_id)
explain_assessment(cluster_id)
list_data_sources()
```

Essas ferramentas devem retornar dados suficientes para o modelo responder com fonte, horário, nível de confiança, limitação e explicação.

Links oficiais:

- MCP Apps in ChatGPT: https://developers.openai.com/apps-sdk/concepts/mcp-apps
- MCP Server: https://developers.openai.com/apps-sdk/concepts/server
- Definir ferramentas: https://developers.openai.com/apps-sdk/plan/define-tools
- Set up your server: https://developers.openai.com/apps-sdk/build/server

### 2. Ferramentas

Ferramentas são as capacidades que o app oferece ao ChatGPT.

No caso do Sinal Aberto, elas devem evitar respostas operacionais sensíveis e focar em informação pública, contextualização e avaliação probabilística.

Exemplo de ferramenta conceitual:

```text
estimate_activity_probability

Entrada:
- cidade
- bairro ou região
- latitude/longitude opcional
- raio opcional
- janela temporal

Saída:
- probabilidade/faixa de atividade atual
- nível de confiança
- evidências recentes
- fatores históricos usados como prior
- limitações da estimativa
- fontes consultadas
- horário da consulta
```

Links oficiais:

- Definir ferramentas: https://developers.openai.com/apps-sdk/plan/define-tools
- Referência do Apps SDK: https://developers.openai.com/apps-sdk/reference

### 3. Componente web opcional

O Apps SDK permite criar uma interface visual renderizada dentro do ChatGPT.

Para o Sinal Aberto, isso pode ser útil para:

- mapa simplificado por regiões;
- lista de clusters ativos;
- cards de evidência;
- escala de probabilidade e impacto;
- linha do tempo de ocorrências recentes;
- explicação dos sinais que sustentam a avaliação.

A documentação informa que o componente web é opcional: se o app só precisar de ferramentas e respostas textuais, não é necessário registrar uma UI.

Links oficiais:

- Quickstart: https://developers.openai.com/apps-sdk/quickstart
- Build your ChatGPT UI: https://developers.openai.com/apps-sdk/build/ui
- Design components: https://developers.openai.com/apps-sdk/plan/design-components
- UI guidelines: https://developers.openai.com/apps-sdk/concepts/ui-guidelines
- UX principles: https://developers.openai.com/apps-sdk/concepts/ux-principles

### 4. Autenticação

Dependendo das fontes e funcionalidades, o app pode exigir autenticação.

Para o Sinal Aberto, a primeira versão idealmente deveria evitar login de usuário e operar com dados públicos/agregados, reduzindo risco de privacidade. Se no futuro houver preferências, histórico de locais ou alertas personalizados, será necessário avaliar autenticação e política de privacidade com muito mais cuidado.

Links oficiais:

- Authenticate users: https://developers.openai.com/apps-sdk/build/auth
- Security & Privacy: https://developers.openai.com/apps-sdk/guides/security-privacy

### 5. Estado

O app pode precisar gerenciar estado de sessão, filtros e resultados recentes.

Para o Sinal Aberto, exemplos de estado:

- cidade selecionada;
- região/bairro consultado;
- janela temporal;
- último cluster visualizado;
- preferências de visualização.

Por privacidade, o projeto deve evitar armazenar localização precisa do usuário quando não for necessário.

Links oficiais:

- Manage state: https://developers.openai.com/apps-sdk/build/state

## Deploy

A documentação oficial indica que, durante desenvolvimento local, é possível expor o servidor local ao ChatGPT usando um túnel como `ngrok`.

Para produção, o app deve estar atrás de um endpoint HTTPS estável. A documentação destaca requisitos como:

- baixa latência;
- suporte a streaming em `/mcp`;
- TLS confiável;
- logs e métricas para depuração;
- endpoint estável;
- tratamento adequado de erros HTTP.

Links oficiais:

- Deploy your app: https://developers.openai.com/apps-sdk/deploy
- Connect from ChatGPT: https://developers.openai.com/apps-sdk/deploy/connect
- Test your integration: https://developers.openai.com/apps-sdk/deploy/test
- Troubleshooting: https://developers.openai.com/apps-sdk/guides/troubleshooting

## Submissão e publicação

Depois de construir e testar o app em Developer Mode, a publicação pública passa pelo fluxo de revisão no dashboard da OpenAI.

Segundo a documentação oficial, antes de submeter é necessário observar pontos como:

- verificação da organização ou pessoa que publicará o app;
- permissões de gerenciamento de apps no dashboard;
- servidor MCP hospedado em domínio publicamente acessível;
- não usar endpoint local ou apenas de teste;
- definir uma Content Security Policy (CSP) com os domínios exatos acessados;
- fornecer informações como nome do app, logo, descrição, URLs da empresa e política de privacidade, dados do MCP, informações das ferramentas, screenshots, prompts de teste e localização.

Links oficiais:

- Submit your app: https://developers.openai.com/apps-sdk/deploy/submission
- App submission guidelines: https://developers.openai.com/apps-sdk/resources/app-submission-guidelines
- Developer Mode: https://platform.openai.com/docs/apps/developer-mode
- Platform Dashboard: https://platform.openai.com/

## Pontos específicos para o Sinal Aberto

Como o Sinal Aberto lida com segurança pública, o app precisa ser conservador no design.

### O que o app deve fazer

- Informar evidências recentes de atividade armada ou policial.
- Indicar fonte, horário de consulta e nível de confiança.
- Explicar a classificação probabilística.
- Mostrar limitações da estimativa.
- Agregar eventos em clusters para reduzir ruído.
- Evitar falsa precisão.
- Priorizar linguagem cidadã e não operacional.

### O que o app deve evitar

- Afirmar certeza sobre operação em andamento sem fonte oficial.
- Expor localização precisa de agentes ou forças de segurança.
- Sugerir rotas para contornar operações.
- Incentivar decisões táticas perigosas.
- Armazenar localização precisa do usuário sem necessidade.
- Usar fontes não verificadas sem sinalizar incerteza.

## Arquitetura sugerida

```text
ChatGPT / outros clientes MCP
        |
        v
Servidor MCP do Sinal Aberto
        |
        +-- Ferramentas de consulta recente
        +-- Ferramentas de clusterização
        +-- Ferramentas de score probabilístico
        +-- Ferramentas de explicabilidade
        |
        v
Backend de dados
        |
        +-- Fogo Cruzado
        +-- ISP Dados
        +-- SINESP / MJSP
        +-- DATA.RIO
        +-- fontes complementares verificadas
```

## Roadmap técnico sugerido

- [ ] Validar acesso, termos e limites da API do Fogo Cruzado.
- [ ] Criar backend mínimo de consulta e cache.
- [ ] Definir ferramentas MCP iniciais.
- [ ] Criar servidor MCP local.
- [ ] Testar no ChatGPT via Developer Mode.
- [ ] Implementar score probabilístico inicial.
- [ ] Implementar agrupamento por clusters.
- [ ] Adicionar respostas explicáveis.
- [ ] Avaliar necessidade de componente web.
- [ ] Preparar política de privacidade.
- [ ] Preparar prompts de teste e screenshots.
- [ ] Submeter app para revisão quando houver estabilidade.

## Links oficiais principais

### Apps SDK

- Página principal: https://developers.openai.com/apps-sdk
- Quickstart: https://developers.openai.com/apps-sdk/quickstart
- Referência: https://developers.openai.com/apps-sdk/reference
- Changelog: https://developers.openai.com/apps-sdk/resources/changelog
- Exemplos: https://github.com/openai/openai-apps-sdk-examples

### Planejamento

- Research use cases: https://developers.openai.com/apps-sdk/plan/research-use-cases
- Define tools: https://developers.openai.com/apps-sdk/plan/define-tools
- Design components: https://developers.openai.com/apps-sdk/plan/design-components

### Build

- Set up your server: https://developers.openai.com/apps-sdk/build/server
- Build your ChatGPT UI: https://developers.openai.com/apps-sdk/build/ui
- Authenticate users: https://developers.openai.com/apps-sdk/build/auth
- Manage state: https://developers.openai.com/apps-sdk/build/state

### Deploy e publicação

- Deploy your app: https://developers.openai.com/apps-sdk/deploy
- Connect from ChatGPT: https://developers.openai.com/apps-sdk/deploy/connect
- Test your integration: https://developers.openai.com/apps-sdk/deploy/test
- Submit your app: https://developers.openai.com/apps-sdk/deploy/submission
- App submission guidelines: https://developers.openai.com/apps-sdk/resources/app-submission-guidelines

### Segurança, privacidade e UX

- Security & Privacy: https://developers.openai.com/apps-sdk/guides/security-privacy
- UX principles: https://developers.openai.com/apps-sdk/concepts/ux-principles
- UI guidelines: https://developers.openai.com/apps-sdk/concepts/ui-guidelines
- Troubleshooting: https://developers.openai.com/apps-sdk/guides/troubleshooting

### Complementar: ChatGPT Actions

- Actions: https://platform.openai.com/docs/actions
- GPT Actions: https://help.openai.com/en/articles/9442513-gpt-actions
- Actions authentication: https://platform.openai.com/docs/actions/authentication

## Status

Documento inicial de referência. Deve ser atualizado conforme o projeto evoluir e conforme a documentação oficial da OpenAI mudar.
