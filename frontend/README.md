# Fable frontend

For the complete Docker Compose stack, start with the [root README](../README.md).
The container uses `Dockerfile` and `docker/nginx.conf`; `nginx.conf` below is
an example for native hosting outside Docker.

A React + TypeScript + Vite frontend for the FastAPI story generator. Includes
prompt inspiration, English/Arabic generation, job polling, a branching story
reader, backtracking, replay, sharing links, and a browser-local library.

## Run locally

Requires Node.js 22.12+ and the configured backend (database and model provider).

From `backend`, start FastAPI:

```sh
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

In another terminal, from `frontend`:

```sh
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**. The development server proxies `/api` to
`http://127.0.0.1:8000`, including session cookies. No CORS changes are needed.
For a different backend address, copy `.env.example` to `.env`, set
`BACKEND_URL`, and restart Vite. Keep all Gemini/DeepSeek credentials in
`backend/.env`; no provider key belongs in the browser or a `VITE_` variable.

## API integration

| Endpoint | Frontend behavior |
| --- | --- |
| `GET /api/health` | Service connection indicator |
| `POST /api/story/create` | Sends `{ "theme": "..." }` with the requested story language |
| `GET /api/jobs/{job_id}` | Polls every two seconds until completed/failed; supports resuming |
| `GET /api/story/{story_id}/complete` | Loads nodes and choices; follows returned database IDs |

Job routes (`#/jobs/{job_id}`) and story routes (`#/stories/{story_id}`) survive
reloads. Polling pauses after 150 unsuccessful polls; the user can check again.
Leaving a generation page stops browser polling but does not cancel the backend
job. Network retries check the same job and do not create a second billable job.
Generation failures return to the saved draft for an explicit new attempt.

The current backend has no list-stories endpoint, so **My library is local to
this browser**, not a server account. It keeps up to 40 recently opened story
references and saves choices in localStorage. A story ID or shared URL can open
an existing backend story on another browser. Local storage failures do not
prevent reading or generating stories. No account/authentication UI is implied.

## Check and build

```sh
npm test
npm run build
npm run preview
```

`build` type-checks the application and creates `dist/`. Preview runs at
http://127.0.0.1:4173 and uses the same API proxy. Tests use mocked HTTP responses
and cover creation, polling, failure/retry, story choices, replay, reading
progress, local library, and missing stories. They do not call paid model APIs.
Fonts and icons are bundled locally; there are no external asset dependencies.

## Production hosting

Serve `dist/` as static files and reverse-proxy `/api` to FastAPI on the same
origin. Vite preview is for local build verification, not production serving.
An example Nginx server configuration is in `nginx.conf`; adjust its host,
certificate setup, static root, and backend address for your environment.
Hash routes require no server-side page routing. Share links only work for
people who can access your deployed frontend and backend.
