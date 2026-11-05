# Fable

A choose-your-own-adventure story generator powered by Gemini or DeepSeek.

- Generate branching stories in English or Arabic.
- Explore choices, go back, and replay different endings.
- Save reading progress and recent stories in your browser.
- Share links to generated stories.

Built with React, TypeScript, FastAPI and PostgreSQL.

## Quick start

Requires Docker with Docker Compose v2.20+. Run from the repository root:

```sh
cp .env.example .env
```

Edit `.env`:

- Replace `POSTGRES_PASSWORD` with a random URL-safe password, such as the output
  of `openssl rand -hex 24`.
- Set `STORY_PROVIDER` to `gemini` or `deepseek` and add the matching API key.

```sh
docker compose up --build -d --wait
```

Open **http://127.0.0.1:8080**. API docs: **http://127.0.0.1:8080/api/docs**.
Change `APP_PORT` in `.env` if needed. Database migrations run automatically.

```sh
docker compose logs -f backend  # View backend logs
docker compose down            # Stop the application; keep saved stories
```

`docker compose down -v` also deletes the database. Keep `.env` private; provider
keys are used only by the backend. After changing settings, run
`docker compose up -d`; after code changes, add `--build`.

## Development

- [Backend setup, providers and tests](backend/README.md)
- [Frontend setup and API integration](frontend/README.md)
- [Docker smoke tests](scripts/README.md)

GitHub Actions checks backend lint/tests, frontend tests/build, Docker integration
and Git history for secrets. CI uses a fixture provider and needs no API keys.

## Deployment notes

The app listens on localhost by default. Before making it publicly accessible,
add HTTPS, authentication, request limits and database backups. Background jobs
run inside the API process and do not recover automatically after a crash.
