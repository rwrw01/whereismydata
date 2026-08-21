# har-provider-lookup

Stateless lookup service: given a list of hostnames, returns the network
owner (leverancier) and that owner's statutory country of registration
(statutaire zetel), sourced from RIPEstat and PeeringDB. No database, no
persisted results, no MaxMind/GeoIP dependency.

Built to serve [web](../web), a client-side HAR-file analyzer: it
sanitizes an uploaded HAR file in the browser down to a bare hostname
list, and this service enriches that list.

## Running locally

```bash
uv sync --group dev
cp .env.example .env
uv run uvicorn src.main:app --reload --port 8080
```

Or via Docker:

```bash
docker compose up
```

## Deploying (Vercel)

Vercel auto-detects `src/main.py` as a Python ASGI entrypoint (no extra
config needed beyond `vercel.json`, which only trims the deployment
bundle). Import this repo as a second Vercel project with **Root
Directory** set to `api`.

Required environment variables (Project Settings → Environment
Variables):

| Variable | Value |
|---|---|
| `ALLOWED_ORIGIN` | The `web` project's Vercel URL (or custom domain) |
| `REDIS_URL` | **Effectively required on Vercel**, see note below |
| `RATE_LIMIT_PER_HOUR` | Optional, defaults to `10` |
| `PEERINGDB_API_KEY` | Optional |

`PORT` is irrelevant on Vercel (serverless — Vercel manages the
listener). The `Dockerfile`/`docker-compose.yml` are for local
development and the Playwright E2E suite only; Vercel's Python runtime
does not use them.

**Why `REDIS_URL` matters here specifically:** Vercel Functions are
stateless serverless invocations — a "warm" container may reuse
`app.state` across a few consecutive requests, but under any real
traffic (concurrent requests, scaling, cold starts) there is no
guarantee two requests share the same in-memory `TTLCache`/`RateLimiter`
state. Without Redis, the 7-day PeeringDB/RIPEstat cache and the
per-IP rate limit both degrade to "per container instance" rather than
the intended global behavior — the rate limit in particular stops being
a reliable abuse guard. Connect a Redis instance (e.g. via the Vercel
Marketplace "Upstash for Redis" integration) and point `REDIS_URL` at
its standard `redis://`/`rediss://` connection string — Upstash's
console shows this under the database's "Connect" tab; the exact env
var name the marketplace integration injects may differ, so verify it
and set `REDIS_URL` to match.

## Testing

```bash
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
```

## API

### `POST /lookup`

Request: `{"hostnames": ["example.com", "cdn.example.com"]}` (1-200 hostnames;
each 1-253 characters, `A-Z a-z 0-9 . _ -` only — anything else is rejected
with a 422). Duplicate hostnames are looked up once and the result is repeated
in the response, so the response always has one entry per input entry.

Response:
```json
{
  "results": [
    {"hostname": "example.com", "asn": 15133, "org_name": "Edgecast Inc", "org_country": "US"}
  ]
}
```

A hostname that can't be resolved, or whose ASN/organisation isn't known
to RIPEstat/PeeringDB, is returned with `null` fields rather than causing
the whole request to fail.

Rate limited per client IP (read from `X-Forwarded-For`, falling back to
the direct peer): `RATE_LIMIT_PER_HOUR` requests per rolling hour window.
Exceeding it returns `429 Too Many Requests` with a `Retry-After` header
(seconds until the window resets).

### `GET /healthz`

Liveness probe. Always 200 if the process is running.

### `GET /readyz`

Readiness probe. 200 if RIPEstat is reachable, 503 otherwise.

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `ALLOWED_ORIGIN` | `http://localhost:5173` | CORS origin allowed to call this API |
| `PEERINGDB_API_KEY` | (empty) | Optional — raises PeeringDB rate limits |
| `REDIS_URL` | (empty) | Optional for a single long-running process (VPS/Docker); **effectively required on serverless hosting** — see [Deploying (Vercel)](#deploying-vercel) |
| `PORT` | `8080` | Listen port (the container binds `$PORT`; PaaS platforms such as Fly.io and Render inject it) |
| `RATE_LIMIT_PER_HOUR` | `10` | Max `/lookup` requests per client IP per rolling hour |

## License

EUPL-1.2 — see [LICENSE](LICENSE).

## Dependencies

| Package | License |
|---|---|
| fastapi | MIT |
| uvicorn | BSD-3-Clause |
| httpx | BSD-3-Clause |
| pydantic-settings | MIT |
| redis | MIT |
| pytest (dev) | MIT |
| pytest-asyncio (dev) | Apache-2.0 |
| respx (dev) | BSD-3-Clause |
| ruff (dev) | MIT |
