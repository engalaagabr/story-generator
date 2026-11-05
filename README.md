# Story Generator API

A Python API for generating, validating, and storing branching stories with
Gemini or DeepSeek. Built with FastAPI, async SQLAlchemy, and PostgreSQL.

Submit a theme, track its generation job, and retrieve a story with connected
scenes, choices, and winning and losing endings.

## Architecture

The application is a feature-oriented modular monolith. Story and job logic live
in separate modules; HTTP routing, database resources, and external integrations
are shared infrastructure.

```text
backend/
├── app/
│   ├── main.py                 # Application factory and resource lifecycle
│   ├── api/
│   │   ├── routes/             # Health, stories, and jobs endpoints
│   │   ├── dependencies.py     # Request sessions and service wiring
│   │   └── error_handlers.py   # Application errors mapped to HTTP responses
│   ├── core/                   # Environment settings and application exceptions
│   ├── db/                     # Engine, sessions, metadata registry, and readiness
│   ├── integrations/llm/       # Provider contract, factory, Gemini, and DeepSeek
│   └── modules/
│       ├── stories/            # Prompts, generation, graph validation, and persistence
│       └── jobs/               # Job state, atomic claims, and processing orchestration
├── alembic/                    # Migration environment and schema revisions
└── tests/                      # Unit tests, integration tests, and story fixtures
```

Routes delegate to services; repositories own queries and writes. The job
processor owns generation transactions. Provider adapters share a JSON-generation
contract, while story validation stays in the stories module. Generated-output
schemas are separate from public API schemas. The application factory wires
resources and supports dependency injection for tests.

## Generation lifecycle

1. The create endpoint saves a `pending` job and returns a snapshot of that state.
2. A FastAPI background task atomically changes the job to `processing`. Missing
   jobs or jobs already claimed are skipped.
3. The generation service builds the prompt and requests JSON from the provider.
   No database transaction remains open during the model request.
4. Pydantic validates the output. Invalid JSON or graph structure can trigger a
   correction request containing validation feedback and the previous response.
5. The repository saves the story and nodes, remapping model-local node IDs to
   database IDs in every choice reference.
6. The story, nodes, and `completed` job state commit together. If processing
   fails, story writes roll back and the processor attempts to record `failed`
   in a separate transaction.

Job states: `pending → processing → completed` or `failed`.

## Run with Docker

Requires Docker with Compose v2.20+ and a provider account with generation access.
Run from the repository root:

```sh
cp .env.example .env
```

Edit the root `.env`:

- Replace `POSTGRES_PASSWORD` with a random URL-safe password, such as the output
  of `openssl rand -hex 24`.
- Choose `STORY_PROVIDER=deepseek` or `STORY_PROVIDER=gemini`.
- Set the API key for that provider.

```sh
docker compose up --build -d --wait
```

Compose waits for PostgreSQL to become healthy and runs `alembic upgrade head`
before starting the API. Application containers run as non-root users. The
PostgreSQL port and API container port are not published directly to the host.

| Resource | Default URL |
| --- | --- |
| API readiness | `http://127.0.0.1:8080/api/health` |
| Swagger UI | `http://127.0.0.1:8080/api/docs` |
| OpenAPI schema | `http://127.0.0.1:8080/openapi.json` |

Useful commands:

```sh
docker compose ps
docker compose logs -f backend
docker compose up -d                 # Apply changed environment settings
docker compose up --build -d --wait  # Rebuild after code changes
docker compose down                 # Stop; keep the database volume
```

Change `APP_PORT` if 8080 is occupied. Credentials are supplied at runtime;
real `.env` files are excluded from Git and Docker build contexts.

## Run locally

Use Python 3.14 to match the container runtime and an available PostgreSQL server.
The commands below use a POSIX shell and run from the repository root:

```sh
cd backend
python3.14 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

In `backend/.env`, set `DATABASE_URL` and the selected provider's credentials.
The URL must use the async PostgreSQL driver:

```dotenv
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/story_generator
```

The database must already exist. Apply its schema and start the server:

```sh
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API documentation is at `http://127.0.0.1:8000/api/docs`. `--reload` is for local
work; the container starts Uvicorn without it.

## Configuration

Compose reads **the root `.env`** and supplies settings to the containers.
Native execution reads **`backend/.env`**. Process environment variables take
precedence over values in the application's environment file. Restart the local
server or recreate containers after changing settings.

| Variable | Default / requirement |
| --- | --- |
| `DATABASE_URL` | Required locally; constructed by Compose. |
| `STORY_PROVIDER` | `deepseek` or `gemini`; default `deepseek`. |
| `STORY_GENERATION_MAX_ATTEMPTS` | `2`; allowed range `1–3`. |
| `DEEPSEEK_API_KEY` / `GEMINI_API_KEY` | Key for the selected provider. |

Provider model names, base URLs, timeouts, and token limits are listed in
[the environment template](backend/.env.example). Both providers default to a
120-second HTTP timeout and 8192 output tokens.

Only the selected provider's key is needed. The API can start without a provider
key, but generation jobs fail until one is configured. Readiness checks verify
the database, not model access or billing.

Gemini uses the native `generateContent` API with a response schema. DeepSeek
uses a chat-completions endpoint with JSON output enabled. For the configured
V4.1 Flash alias on `api.deepseek.com`, the adapter sends `deepseek-flash` as the
API model name. On other endpoints, it preserves the configured model ID.
For endpoint-specific examples, see [provider configuration](backend/README.md).

Compose defaults to `APP_BIND_ADDRESS=127.0.0.1` and `APP_PORT=8080`.
Database credentials use `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`;
see [the Compose environment template](.env.example). The password must be
URL-safe because Compose inserts it into the connection URL.

## API usage

All application endpoints use the `/api` prefix.

| Method | Endpoint | Response |
| --- | --- | --- |
| `GET` | `/api/health` | Database readiness; HTTP 200 or 503. |
| `POST` | `/api/story/create` | HTTP 200 with a pending job snapshot. |
| `GET` | `/api/jobs/{job_id}` | Job status, timestamps, result ID, and error. |
| `GET` | `/api/story/{story_id}/complete` | Story metadata, root node, and all nodes. |

### Create a job

For Docker, use port 8080. For native execution, change the base URL to port 8000.

```sh
API_URL=http://127.0.0.1:8080

curl -sS -X POST "$API_URL/api/story/create" \
  -H 'Content-Type: application/json' \
  -d '{"theme":"An explorer searching for a lost city"}'
```

The response includes `job_id`, `status`, `created_at`, `story_id`,
`completed_at`, and `error`. Initially, status is `pending` and the result,
completion timestamp, and error are null.

### Poll and retrieve

Replace the example ID with the `job_id` returned by creation:

```sh
JOB_ID=97f42641-c98e-4e03-b1ef-0e3977c96ad4
curl -sS "$API_URL/api/jobs/$JOB_ID"
```

Continue checking until the status is `completed` or `failed`. A completed job
contains a `story_id`; use that value to retrieve the story:

```sh
STORY_ID=1
curl -sS "$API_URL/api/story/$STORY_ID/complete"
```

The response contains `id`, `title`, `session_id`, `created_at`, `root_node`, and
`all_nodes`. Each node includes its content, ending flags, and choices containing
`text` and `node_id`. `all_nodes` is keyed by database node ID; JSON object keys
are strings. Follow a choice by looking up its `node_id` in this mapping.

Creation reuses or sets a `session_id` cookie. This groups records but does not
provide authentication or restrict access to a story.

## Database and migrations

Three tables store application data: `stories` holds metadata, `story_nodes`
holds scenes and JSON choices, and `story_jobs` tracks generation state and errors.
The application owns the database engine and disposes it on shutdown.

For native execution, run from `backend` with the virtual environment active:

```sh
alembic upgrade head
alembic current
alembic check
```

For Compose, prefix migration commands with `docker compose exec backend`.

`docker compose down` preserves saved data. **`docker compose down -v` deletes the
PostgreSQL volume.** Back up data before schema changes. Updating PostgreSQL
credentials in `.env` does not change users inside an existing database volume.

## Tests and checks

From `backend`, with the virtual environment active:

```sh
python -m pip install -r requirements-dev.txt
DATABASE_URL=sqlite+aiosqlite:///:memory: python -m unittest discover -s tests -v
python -m ruff check . ../scripts
python -m ruff format --check . ../scripts
```

Tests use temporary SQLite databases and mocked providers, covering generation,
graph validation, transactions, job state, API behavior, and module boundaries.
No provider key is required. [Docker smoke tests](scripts/README.md) cover the
PostgreSQL flow; CI also checks Git history for secrets.
