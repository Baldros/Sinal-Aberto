# OpenAI Apps SDK

This document summarizes the essentials of the official **OpenAI Apps SDK** to
guide the evolution of Sinal Aberto as an app inside ChatGPT.

The goal is not to replace the official documentation. This file records the key
points for the project and keeps the main links available for later reference.

## Positioning for Sinal Aberto

Sinal Aberto was initially imagined as a ChatGPT app, but the nature of the
project points to something broader: a public-utility layer available to
multiple assistants.

The most aligned path is to build Sinal Aberto as an **open MCP server**,
consumed by ChatGPT through the Apps SDK and, later, by other MCP-compatible
chatbots and clients.

In practical terms:

- the **backend/MCP server** centralizes data, tools, scores, safety rules, and explainability;
- in the MVP, that backend should be lightweight: Python/FastMCP, SQLite, short cache, and clustering in application code;
- the **ChatGPT app** uses that server to answer questions and, if needed, render a visual interface;
- other chatbots can use the same MCP layer when they support the protocol;
- the project's public logic is not locked to a single client.

## What the Apps SDK Is

The **OpenAI Apps SDK** is the official framework for building apps that extend
ChatGPT.

According to the official documentation, apps built with the Apps SDK use the
**Model Context Protocol (MCP)** to connect to ChatGPT. Creating an app usually
requires:

1. a required **MCP server**, which defines the app's capabilities as tools;
2. optionally, a **web component**, rendered inside ChatGPT in an iframe when the app needs a visual interface.

Official links:

- Apps SDK homepage: https://developers.openai.com/apps-sdk
- Quickstart: https://developers.openai.com/apps-sdk/quickstart
- Reference: https://developers.openai.com/apps-sdk/reference
- Official examples on GitHub: https://github.com/openai/openai-apps-sdk-examples

## GPT With Action vs. Apps SDK App

### GPT With Action

A GPT with an Action is a simpler path for MVPs. It connects a custom GPT to an
external API through an OpenAPI schema.

It can validate quickly:

- users' main questions;
- response format;
- data usefulness;
- need for city, neighborhood, radius, and time-window filters.

Official links:

- Introduction to Actions: https://platform.openai.com/docs/actions
- Actions in GPTs: https://help.openai.com/en/articles/9442513-gpt-actions
- Actions authentication: https://platform.openai.com/docs/actions/authentication

### Apps SDK App

The Apps SDK is more appropriate when the product needs:

- well-defined MCP tools;
- a visual interface inside ChatGPT;
- interactive components;
- an app publication/review flow;
- architecture reusable by other MCP clients;
- more control over state, authentication, UX, and deployment.

For Sinal Aberto, the Apps SDK makes the most sense once the project has its own
backend, probabilistic scoring, stable endpoints, and some visual or interactive
experience.

## Main Components

### 1. MCP Server

The MCP server is the foundation of the app.

It exposes tools ChatGPT can call to fetch data, calculate metrics, and explain
results.

Possible Sinal Aberto tools:

```text
get_recent_activity(city, region, time_window)
get_active_clusters(city, time_window)
estimate_activity_probability(location, radius, time_window)
estimate_public_impact(cluster_id)
explain_assessment(cluster_id)
list_data_sources()
```

These tools should return enough data for the model to answer with source,
timestamp, confidence level, limitation, and explanation.

Official links:

- MCP Apps in ChatGPT: https://developers.openai.com/apps-sdk/concepts/mcp-apps
- MCP Server: https://developers.openai.com/apps-sdk/concepts/server
- Define tools: https://developers.openai.com/apps-sdk/plan/define-tools
- Set up your server: https://developers.openai.com/apps-sdk/build/server

### 2. Tools

Tools are the capabilities the app offers to ChatGPT.

For Sinal Aberto, tools should avoid sensitive operational answers and focus on
public information, context, and probabilistic assessment.

Conceptual tool example:

```text
estimate_activity_probability

Input:
- city
- neighborhood or region
- optional latitude/longitude
- optional radius
- time window

Output:
- probability/current-activity band
- confidence level
- recent evidence
- historical factors used as priors
- estimate limitations
- consulted sources
- query time
```

Official links:

- Define tools: https://developers.openai.com/apps-sdk/plan/define-tools
- Apps SDK reference: https://developers.openai.com/apps-sdk/reference

### 3. Optional Web Component

The Apps SDK can render a visual interface inside ChatGPT.

For Sinal Aberto, this may be useful for:

- simplified regional map;
- active cluster list;
- evidence cards;
- probability and impact scale;
- recent-occurrence timeline;
- explanation of signals behind the assessment.

The documentation states that the web component is optional. If the app only
needs tools and text responses, registering a UI is not required.

Official links:

- Quickstart: https://developers.openai.com/apps-sdk/quickstart
- Build your ChatGPT UI: https://developers.openai.com/apps-sdk/build/ui
- Design components: https://developers.openai.com/apps-sdk/plan/design-components
- UI guidelines: https://developers.openai.com/apps-sdk/concepts/ui-guidelines
- UX principles: https://developers.openai.com/apps-sdk/concepts/ux-principles

### 4. Authentication

Depending on sources and features, the app may require authentication.

For Sinal Aberto, the first version should ideally avoid user login and operate
with public/aggregate data, reducing privacy risk. If future versions include
preferences, location history, or personalized alerts, authentication and the
privacy policy will need more careful design.

Official links:

- Authenticate users: https://developers.openai.com/apps-sdk/build/auth
- Security & Privacy: https://developers.openai.com/apps-sdk/guides/security-privacy

### 5. State

The app may need to manage session state, filters, and recent results.

Sinal Aberto state examples:

- selected city;
- queried region/neighborhood;
- time window;
- last viewed cluster;
- visualization preferences.

For privacy, the project should avoid storing precise user location unless it is
necessary.

Official link:

- Manage state: https://developers.openai.com/apps-sdk/build/state

## Deployment

The official documentation indicates that, during local development, a local
server can be exposed to ChatGPT with a tunnel such as `ngrok`.

For production, the app must sit behind a stable HTTPS endpoint. Requirements
include:

- low latency;
- streaming support at `/mcp`;
- reliable TLS;
- logs and metrics for debugging;
- stable endpoint;
- appropriate HTTP error handling.

Official links:

- Deploy your app: https://developers.openai.com/apps-sdk/deploy
- Connect from ChatGPT: https://developers.openai.com/apps-sdk/deploy/connect
- Test your integration: https://developers.openai.com/apps-sdk/deploy/test
- Troubleshooting: https://developers.openai.com/apps-sdk/guides/troubleshooting

## Submission and Publication

After building and testing the app in Developer Mode, public publication goes
through the OpenAI dashboard review flow.

Before submission, the official documentation calls out points such as:

- verification of the organization or person publishing the app;
- app-management permissions in the dashboard;
- MCP server hosted on a publicly accessible domain;
- no local-only or test-only endpoint;
- Content Security Policy (CSP) with exact accessed domains;
- app name, logo, description, company URLs, privacy policy, MCP data, tool
  information, screenshots, test prompts, and localization.

Official links:

- Submit your app: https://developers.openai.com/apps-sdk/deploy/submission
- App submission guidelines: https://developers.openai.com/apps-sdk/resources/app-submission-guidelines
- Developer Mode: https://platform.openai.com/docs/apps/developer-mode
- Platform Dashboard: https://platform.openai.com/

## Sinal Aberto-Specific Points

Because Sinal Aberto handles public-safety context, the app needs conservative
design.

### What the app should do

- Report recent evidence of armed or police activity.
- Indicate source, query time, and confidence level.
- Explain the probabilistic classification.
- Show estimate limitations.
- Aggregate events into clusters to reduce noise.
- Avoid false precision.
- Prioritize civic, non-operational language.

### What the app should avoid

- Claim certainty about an ongoing operation without an official source.
- Expose precise locations of agents or public-safety forces.
- Suggest routes around operations.
- Encourage dangerous tactical decisions.
- Store precise user location without need.
- Use unverified sources without flagging uncertainty.

## Suggested Architecture

```text
ChatGPT / other MCP clients
        |
        v
Sinal Aberto MCP server
        |
        +-- recent-query tools
        +-- clustering tools
        +-- probabilistic-scoring tools
        +-- explainability tools
        |
        v
Data backend
        |
        +-- Fogo Cruzado adapter
        +-- IBGE territorial adapter
        +-- optional historical baselines
        +-- cache / SQLite
```

## Recommended Path

1. Build the backend as an MCP server first.
2. Expose `list_data_sources` and `get_recent_activity`.
3. Test locally with Developer Mode and a tunnel.
4. Add clustering and scoring only after the first tool contract is stable.
5. Add a visual component only if it clearly improves comprehension.
6. Prepare privacy policy, source attribution, and safety limitations before any public submission.
