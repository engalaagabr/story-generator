# Docker smoke tests

Run from the repository root with Docker Compose and Python 3. The test override
uses a fixture server instead of a paid model API; Nginx, FastAPI, migrations,
background jobs and PostgreSQL run normally.

```sh
export POSTGRES_PASSWORD=test-only-password APP_PORT=18080
docker compose -p fable-test -f compose.yaml -f compose.test.yaml up --build -d --wait
python3 scripts/smoke_test.py http://127.0.0.1:18080
docker compose -p fable-test -f compose.yaml -f compose.test.yaml down -v
unset POSTGRES_PASSWORD APP_PORT
```

Choose another `APP_PORT` and matching URL if the port is occupied. The test
project uses its own database volume; the cleanup command deletes that volume.
Use these commands in a separate terminal so the exported variables do not
change settings for a normal Compose deployment.

The smoke test checks built assets, API health, documentation, story creation,
job polling, persisted story nodes and choice targets. Run it only against the
fixture stack above. `compose.test.yaml` is for tests, not real generation.
GitHub Actions runs the same checks automatically.
