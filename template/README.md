# ADK A2A Agent Server

## Overview

ADK Template for creating an A2A Agent Server.

Project Documentation:
- [Development Guide Documentation](./docs/development_guide.md)
- [Development UV Guide Documentation](./docs/development_uv_guide.md)


## Installation

From the project root (or from this template directory):

```bash
cd templates/adk-a2a-agent-server
uv sync
```

## Configuration

Make a copy of `.env.example` and rename it to `.env`. Update the environment variables as needed. Ensure `AGENT_NAME` is a valid identifier (letters, digits, underscores only; no hyphens).

### Remote MCP tools

The template can attach tools from a remote MCP server directly to the orchestrator agent using ADK's MCP toolset support.

Set these env vars to enable it:

- `MCP_TRANSPORT=sse` with `MCP_SERVICE_URL=http://localhost:8001/sse`
- `MCP_TRANSPORT=streamable_http` with `MCP_SERVICE_URL=http://localhost:3000/mcp`
- `MCP_API_KEY=...` if the remote MCP server expects a bearer token

This follows the Google ADK + external MCP pattern described in the Google Cloud guide: [Use Google ADK and MCP with an external server](https://cloud.google.com/blog/topics/developers-practitioners/use-google-adk-and-mcp-with-an-external-server).

## Usage

From this directory (the template/project root):

```bash
uv run main.py
```

The A2A server listens on `http://0.0.0.0:${PORT}` using the value from `.env`.
The A2A agent card is exposed at `/.well-known/agent-card.json`, and the JSON-RPC
endpoint accepts `POST` requests at `/`.

For local testing, make sure `CLOUD_RUN_URL` in `.env` matches the base URL clients
should use, for example `http://127.0.0.1:8000`.

### Test client

A sample client lives outside the `agent/` package at `client/client.py` so you can
test the running server like a real external caller.

Run the server in one terminal:

```bash
uv run main.py
```

Run the client in a second terminal:

```bash
uv run python client/client.py
```

Optional environment variables for the client:

- `A2A_BASE_URL=http://127.0.0.1:8000` points to the running A2A server.
- `A2A_USER_MESSAGE="What can you do?"` sets the message to send.
- `A2A_STREAM=true` uses `message/stream` instead of `message/send`.
- `A2A_POLL_TASK=true` keeps polling if the server returns a task instead of a direct message.

Example:

```bash
A2A_BASE_URL=http://127.0.0.1:8000 \
A2A_USER_MESSAGE="Summarize what this agent can do." \
uv run python client/client.py
```

### Real A2A call flow

The real client flow follows the ADK and A2A docs:

1. Fetch the agent card from `/.well-known/agent-card.json`.
2. Create a client with `ClientFactory`.
3. Send a message and consume the returned message/task events.

### Model provider (Vertex AI / Model Garden)

The model used by the root and sub-agents is resolved from env via `agent/core/model`:

- **LLM_PROVIDER=vertex_ai** (default): uses `LLM_MODEL` (e.g. `gemini-2.0-flash`). Set `GOOGLE_GENAI_USE_VERTEXAI=TRUE` and `GOOGLE_CLOUD_PROJECT` (and optionally `GOOGLE_CLOUD_LOCATION` or `VERTEX_AI_LOCATION`) for Vertex AI.
- **LLM_PROVIDER=garden**: uses a Vertex AI Model Garden or fine-tuned endpoint. Set `GOOGLE_CLOUD_PROJECT`, `VERTEX_AI_LOCATION`, and `GARDEN_ENDPOINT_ID` (path is built from these).

`get_model()` is used in `agent/root_agent.py` and sub-agents (e.g. `example_agent`) so all agents share the same provider/config.

### How state, memory, artifact, and MCP are used

- **Session (state)**  
  The Runner uses `session_service` to load and save conversation state and event history. No extra wiring is needed; the Runner calls it automatically for each request.

- **Memory (long-term knowledge)**  
  When `memory_service` is set, the Runner receives it and the root agent is configured with:
  - An **after_agent_callback** that calls `memory_service.add_session_to_memory(session)` after each turn, so session content is ingested into long-term memory.
  - The **load_memory** tool so the agent can query past conversations when needed.
  Set `MEMORY_SERVICE_BACKEND=none` to disable memory.

- **Artifact**  
  The Runner uses `artifact_service` for storing and loading artifacts. Tools and agent code use `context.save_artifact()` / `context.load_artifact()`; the Runner provides the service on the invocation context. Set `ARTIFACT_SERVICE_BACKEND=none` to disable artifacts.

- **MCP (remote tools)**  
  When `MCP_SERVICE_URL` is set, the root orchestrator also receives an ADK `McpToolset` created in `agent/tools/mcp.py`. The template supports both `sse` and `streamable_http` transports and forwards `MCP_API_KEY` as a bearer token when provided.

## Connectors – official SDK docs and references

Official documentation and GitHub repositories for each connector (state/session, memory, artifact):

### Session (state) management – `BaseSessionService`

| Backend   | Implementation              | Official docs / GitHub | Notes |
|----------|-----------------------------|-------------------------|--------|
| **inmemory** | `InMemorySessionService`   | [ADK Sessions – Session](https://google.github.io/adk-docs/sessions/session/) · [adk-python (GitHub)](https://github.com/google/adk-python) | Built-in; no persistence. |
| **firestore** | Template `FirestoreSessionService` | [Cloud Firestore](https://cloud.google.com/firestore/docs) · [adk-python](https://github.com/google/adk-python) (base interface) | Custom connector in this repo; implements ADK `BaseSessionService`. |
| **redis** / **memorystore** | `RedisSessionService` (google-adk-redis / adk-redis) | [google-adk-redis (PyPI)](https://pypi.org/project/google-adk-redis/) · [adk-redis (GitHub)](https://github.com/redis-developer/adk-redis) | Install: `pip install google-adk-redis` or `pip install adk-redis[memory]`. |
| **postgres** | `DatabaseSessionService` | [ADK Sessions – Session](https://google.github.io/adk-docs/sessions/session/) · [adk-python](https://github.com/google/adk-python) | Uses ADK's database-backed session service. Requires an async SQLAlchemy URL such as `postgresql+asyncpg://user:password@localhost:5432/adk_sessions` and the `asyncpg` package. |
| **mongodb** | Template `MongoDBSessionService` | [ADK Sessions – Session](https://google.github.io/adk-docs/sessions/session/) · [Motor](https://motor.readthedocs.io/) | Custom connector in this repo that stores app state, user state, session state, and event history in MongoDB collections. Requires `MONGODB_URI`, `MONGODB_DATABASE`, and the `motor` package. |

- **ADK sessions overview:** [Introduction to Session, State, and Memory](https://google.github.io/adk-docs/sessions/)

### Memory (long-term knowledge) – `BaseMemoryService`

| Backend   | Implementation              | Official docs / GitHub | Notes |
|----------|-----------------------------|-------------------------|--------|
| **inmemory** | `InMemoryMemoryService`   | [ADK Memory](https://google.github.io/adk-docs/sessions/memory/) · [adk-python (GitHub)](https://github.com/google/adk-python) | Built-in; keyword search; no persistence. |
| **redis** | `RedisLongTermMemoryService` (adk-redis) | [adk-redis (GitHub)](https://github.com/redis-developer/adk-redis) · [PyPI adk-redis](https://pypi.org/project/adk-redis/) · [Redis Agent Memory Server](https://github.com/redis/agent-memory-server) | Install: `pip install adk-redis[memory]`. Requires Redis Agent Memory Server (e.g. `http://localhost:8088`). Semantic search, auto-extraction, recency boost. |

- **ADK memory overview:** [Memory – Agent Development Kit (ADK)](https://google.github.io/adk-docs/sessions/memory/)

### Artifact storage – `BaseArtifactService`

| Backend   | Implementation              | Official docs / GitHub | Notes |
|----------|-----------------------------|-------------------------|--------|
| **inmemory** | `InMemoryArtifactService` | [ADK Artifacts](https://google.github.io/adk-docs/artifacts/) · [adk-python (GitHub)](https://github.com/google/adk-python) | Built-in; no persistence. |
| **gcs**  | `GcsArtifactService`       | [ADK Artifacts](https://google.github.io/adk-docs/artifacts/) · [adk-python (GitHub)](https://github.com/google/adk-python) | Built-in; requires GCS bucket and credentials. |

- **ADK artifacts overview:** [Artifacts – Agent Development Kit (ADK)](https://google.github.io/adk-docs/artifacts/)

### Summary of official / reference links

- **ADK docs (sessions, memory, artifacts):** https://google.github.io/adk-docs/
- **ADK Python (GitHub):** https://github.com/google/adk-python
- **adk-redis (Redis session + long-term memory):** https://github.com/redis-developer/adk-redis
- **Redis Agent Memory Server (for redis memory):** https://github.com/redis/agent-memory-server

## Directory Structure

The directory structure follows a standard layout: **entry-point agent** and **sub-agents** in dedicated folders, each with a `sub_agent` module and a separate **prompt** file.

```
.
├── .env.example                # Example environment variables (copy to .env)
├── .gitignore
├── .pre-commit-config.yaml
├── .python-version
├── README.md
├── agent/                      # Main source code
│   ├── __init__.py
│   ├── root_agent.py           # Entry point: root agent, runner, A2A app
│   ├── core/                   # Config, OTEL, model, state/memory/artifact (env-configured)
│   │   ├── __init__.py
│   │   ├── config.py           # Pydantic settings (env)
│   │   ├── otel.py             # OpenTelemetry setup
│   │   ├── model/              # LLM provider (Vertex AI, Model Garden)
│   │   │   ├── __init__.py     # get_model()
│   │   │   ├── types.py        # ModelProvider enum
│   │   │   └── provider.py     # Resolves model from LLM_PROVIDER (vertex_ai | garden)
│   │   ├── state_management/   # ADK BaseSessionService (session/state)
│   │   │   ├── factory.py     # get_session_service() from SESSION_SERVICE_BACKEND
│   │   │   ├── types.py       # SessionBackend enum
│   │   │   └── connectors/    # inmemory, firestore, redis, postgres, mongodb
│   │   ├── memory_management/ # ADK BaseMemoryService (long-term knowledge)
│   │   │   ├── factory.py     # get_memory_service() from MEMORY_SERVICE_BACKEND
│   │   │   ├── types.py       # MemoryBackend enum
│   │   │   └── connectors/    # inmemory, redis
│   │   └── artifact_management/ # ADK BaseArtifactService (binary artifacts)
│   │       ├── factory.py     # get_artifact_service() from ARTIFACT_SERVICE_BACKEND
│   │       ├── types.py       # ArtifactBackend enum
│   │       └── connectors/    # inmemory, gcs
│   ├── exceptions/             # Custom exceptions
│   │   ├── __init__.py
│   │   └── base.py            # APIException, etc.
│   ├── tools/                  # Reusable tool helpers (memory tools, example tools)
│   └── sub_agents/             # Sub-agents used by the root agent
│       ├── __init__.py         # Exports example_agent, remote_agent
│       ├── example_agent/      # Local (in-process) sub-agent
│       │   ├── __init__.py
│       │   ├── sub_agent.py    # Agent definition
│       │   └── prompt.py       # Instruction text for this sub-agent
│       └── remote_agent/       # Remote (A2A) sub-agent
│           ├── __init__.py
│           ├── sub_agent.py    # RemoteA2aAgent definition
│           └── prompt.py       # Description for routing
├── client/                     # Example external A2A client
│   └── client.py               # Sends requests to the running A2A server
├── dockerfile.dev
├── dockerfile.prod
├── docs/
│   ├── development_guide.md
│   └── development_uv_guide.md
├── main.py                     # Runs the agent server (uvicorn)
├── makefile
├── pyproject.toml
└── uv.lock
```

### Folder Descriptions

---

## Root-Level Files

### `.env.example`
- Template for required environment variables.
- Copy to `.env` and configure values for local setup.

### `.gitignore`
- Defines files and folders Git should ignore.
- Prevents committing sensitive or unnecessary files.

### `.pre-commit-config.yaml`
- Configures automated checks before commits.
- Enforces linting, formatting, and code quality standards.

### `.python-version`
- Specifies the required Python version.
- Ensures consistency across development environments.

### `README.md`
- Main project documentation file.
- Provides setup, usage, and architecture overview.

### `dockerfile.dev`
- Docker configuration for development.
- Includes debugging tools and development dependencies.

### `dockerfile.prod`
- Docker configuration optimized for production.
- Uses minimal dependencies for performance and security.

### `main.py`
- Simple wrapper to run the agent server using `uvicorn`.

### `makefile`
- Defines common development commands.
- Simplifies build, test, and run operations.

### `pyproject.toml`
- Manages project dependencies and metadata.
- Configures tooling such as linters and formatters.

### `uv.lock`
- Locks dependency versions for consistency.
- Ensures reproducible builds across environments.

## `docs/`
- Contains detailed project documentation.
- Guides development standards and workflows.

    ### `development_guide.md`
    - Explains coding standards and structure.
    - Describes contribution and testing practices.

    ### `development_uv_guide.md`
    - Documents usage of the `uv` package manager.
    - Explains dependency locking and environment setup.

---

## `agent/`
- Main source code for the A2A Agent server. `root_agent.py` defines the root workflow agent, services, runner, and A2A app.

    ### `root_agent.py` (entry workflow)
    - Initializes OpenTelemetry and core services (session, memory, artifact).
    - Builds the **orchestrator LLM agent** that delegates to `example_agent` and `remote_agent`.
    - Wraps the orchestrator inside a **`SequentialAgent`** workflow (`root_agent`) following ADK workflow agent patterns.
    - Creates the `Runner`, builds the A2A FastAPI app via `to_a2a`, and instruments FastAPI.

    ### `core/`
    - **`config.py`**: Pydantic Settings; loads from `.env`. Includes model provider, session, memory, artifact backends, and OTEL toggles. Also propagates key settings to process env for `google-genai` / Vertex AI (`GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_GENAI_USE_VERTEXAI`).
    - **`otel.py`**: OpenTelemetry setup and FastAPI instrumentation. Always logs spans to console; optionally exports to Cloud Trace when `ENABLE_CLOUD_TRACE=true` and `GOOGLE_CLOUD_PROJECT` is set.
    - **`model/`**: LLM provider – **`get_model()`** returns the model string for `Agent(model=...)` from `LLM_PROVIDER` (vertex_ai \| garden). **vertex_ai**: uses `LLM_MODEL` (e.g. `gemini-2.0-flash`). **garden**: builds a Vertex AI endpoint path from `GOOGLE_CLOUD_PROJECT` + `VERTEX_AI_LOCATION` + `GARDEN_ENDPOINT_ID`.
    - **`state_management/`**: Session (state) service – **factory** returns `BaseSessionService` from `SESSION_SERVICE_BACKEND` (inmemory, firestore, redis, memorystore, postgres, mongodb). **Connectors**: InMemory (ADK), Firestore, Redis (via `google-adk-redis`), Memorystore (Redis-compatible), Postgres via ADK `DatabaseSessionService`, and a custom MongoDB connector built on `BaseSessionService` using Motor.
    - **`memory_management/`**: Long-term memory – **factory** returns `BaseMemoryService` from `MEMORY_SERVICE_BACKEND` (none, inmemory, redis). **Connectors**: InMemory (ADK) and Redis (via `adk-redis` + Redis Agent Memory Server). See section *Connectors – official SDK docs and references* above.
    - **`artifact_management/`**: Artifact storage – **factory** returns `BaseArtifactService` from `ARTIFACT_SERVICE_BACKEND` (none, inmemory, gcs). **Connectors**: InMemory (ADK), GcsArtifactService.

    ### `exceptions/`
    - **`base.py`**: Custom exception types (e.g. `APIException` with `message`, `status_code`). Use for consistent error handling.
    - Also defines `ToolConfigurationException` used by `agent/tools/memory.py` when optional tools are misconfigured.

    ### `tools/`
    - **`memory.py`**: `get_memory_tools(memory_service)` returns the list of memory-related tools to attach when memory is enabled. By default, when `memory_service` is not `None`, it attaches ADK's built-in `load_memory` tool so agents can query long-term memory. Raises `ToolConfigurationException` if the import fails while memory is enabled.
    - **`mcp.py`**: `get_mcp_tools()` returns an ADK `McpToolset` backed by `MCP_TRANSPORT`, `MCP_SERVICE_URL`, and `MCP_API_KEY`, so the orchestrator can discover and call tools from a remote MCP server.
    - **`example.py`**: Example pure-Python helper (`summarize_last_user_message`) that demonstrates how to organize reusable tool logic. You can wrap this as an ADK tool if needed.
    - **`__init__.py`**: Exports tool helpers for convenient imports from `agent.tools`.

    ### `sub_agents/`
    - **example_agent**: Local sub-agent (same process). `sub_agent.py` defines the `Agent`; `prompt.py` holds the instruction text.
    - **remote_agent**: Proxy to an external A2A service. `sub_agent.py` defines the `RemoteA2aAgent`; `prompt.py` holds the description used for routing. Set `REMOTE_A2A_AGENT_URL` in `.env` to the remote agent’s URL.

## `client/`
- Example external caller for the A2A server.
- Demonstrates agent-card discovery, `A2AClient` setup, and `message/send` / `message/stream` usage.