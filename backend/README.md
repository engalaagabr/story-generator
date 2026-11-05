# Story generator backend

The backend is a feature-oriented modular monolith. The maintained
[architecture guide](docs/architecture.md) explains every source file,
dependency direction, transaction ownership, naming, and how to add features
and model providers. Start there when reusing the structure in another project.

Run commands from the `backend` directory. Install dependencies with
`python -m pip install -r requirements.txt`, copy `.env.example` to `.env`, and
set `DATABASE_URL` to your PostgreSQL connection string, and configure a provider
below. Keep `.env` private; it is ignored by Git.

Apply migrations with `alembic upgrade head`, then start the server with
`uvicorn app.main:app --reload`. API documentation is at `/api/docs`.

## Story generation

`POST /api/story/create` with `{"theme":"A space adventure"}` creates a background
job. Poll `GET /api/jobs/{job_id}` for its status. Once completed, fetch
`GET /api/story/{story_id}/complete` using the job's `story_id`.

`modules/stories/generation.py` owns story prompting and output validation.
Provider adapters return model text, and the story repository saves choices
using database node IDs. The job processor owns transaction boundaries.
Provider failures or invalid stories mark the job as failed; partial database
writes roll back.
Set `STORY_PROVIDER` to `deepseek` (the default) or `gemini`. Only the selected
provider's API key is required. Restart the server after changing `.env`.
The server can start without a key, but generation jobs will fail with a
configuration error until the selected provider's key is set.

`STORY_GENERATION_MAX_ATTEMPTS` limits validation/correction attempts (default 2,
maximum 3). The prompt contains a complete, validated example. If a model returns
invalid JSON or breaks story graph rules, the generation service sends the
validation feedback and previous output back for correction. Only validated
stories reach persistence. A correction is an additional model request and can
incur provider charges; set this value to 1 to disable correction. Transport,
billing, permission, and quota failures are not retried by this policy.
Validation logs contain rule failures, not full prompts or generated stories.

## Gemini

Set these values in your local `.env`:

```dotenv
STORY_PROVIDER=gemini
GEMINI_API_KEY=your-google-ai-studio-key
GEMINI_MODEL=gemini-2.5-flash
```

Gemini uses Google's native `generateContent` API with a JSON response schema.
The API schema omits length bounds to keep Google's output grammar manageable;
the full schema and graph rules are still enforced locally before saving.
The key is sent in the `x-goog-api-key` header. Both providers use the same story
prompt, validation, and persistence flow.

Optional settings:

- `GEMINI_BASE_URL`: defaults to `https://generativelanguage.googleapis.com/v1beta`.
- `GEMINI_MODEL`: defaults to `gemini-2.5-flash`; accepts a model ID with or without `models/`.
- `GEMINI_TIMEOUT_SECONDS`: HTTP timeout, default 120 seconds.
- `GEMINI_MAX_TOKENS`: output token limit, default 8192.

HTTP 429 indicates a quota or rate limit; check the Google project's quota and
billing. Model access alone does not guarantee that generation quota is available.
See Google's [Gemini API documentation](https://ai.google.dev/api/generate-content).

## DeepSeek / OpenRouter

Set `STORY_PROVIDER=deepseek` and configure `DEEPSEEK_API_KEY` for your chosen endpoint.

Optional settings (defaults shown in `.env.example`):

- `DEEPSEEK_BASE_URL`: API base URL, including any required `/v1` prefix.
- `DEEPSEEK_MODEL`: model name; defaults to `deepseek/deepseek-v4.1-flash`.
- `DEEPSEEK_TIMEOUT_SECONDS`: HTTP timeout, default 120 seconds.
- `DEEPSEEK_MAX_TOKENS`: output token limit, default 8192. Increase it if a job
  reports truncated output.

The provider uses non-thinking mode. See the official
[DeepSeek API documentation](https://api-docs.deepseek.com/) and
[JSON output guide](https://api-docs.deepseek.com/guides/json_mode/).

### V4.1 Flash model names

With `DEEPSEEK_BASE_URL=https://api.deepseek.com`, the provider translates
`deepseek/deepseek-v4.1-flash` (or `deepseek-v4.1-flash`) to `deepseek-flash`.
This is DeepSeek's official API name for the current V4.1 Flash version; it
follows DeepSeek's updates rather than pinning the original September snapshot.
An existing `DEEPSEEK_MODEL=deepseek-flash` setting also continues to work.

To use the exact [OpenRouter model ID](https://openrouter.ai/deepseek/deepseek-v4.1-flash),
set `DEEPSEEK_BASE_URL=https://openrouter.ai/api/v1`,
`DEEPSEEK_MODEL=deepseek/deepseek-v4.1-flash`, and set `DEEPSEEK_API_KEY` to an
**OpenRouter** API key. The full model ID is sent unchanged to OpenRouter, using
its `reasoning.enabled=false` option. A direct DeepSeek key cannot authenticate
with OpenRouter.

An `Insufficient API balance (HTTP 402)` job error means the configured provider
account needs API credits. A valid key can list models even when its account
has no balance, so model-list access alone does not verify generation. Add
credits with the provider, then create a new story job; failed jobs are not
retried automatically.

## Tests

Install `requirements-dev.txt`, then run `python -m unittest discover -s tests -v`.
Tests mock both providers' HTTP responses; they need no API key or paid API requests.
