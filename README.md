# har-provider-lookup

Stateless lookup service: given a list of hostnames, returns the network
owner (leverancier) and that owner's statutory country of registration
(statutaire zetel), sourced from RIPEstat and PeeringDB. No database, no
persisted results, no MaxMind/GeoIP dependency.

Built to serve [har-scan-web](../har-scan-web), a client-side HAR-file
analyzer.

## Running locally

```bash
uv sync --group dev
cp .env.example .env
uv run uvicorn src.main:app --reload --port 8080
```

## Testing

```bash
uv run pytest -v
```

## API

### `POST /lookup`

Request: `{"hostnames": ["example.com", "cdn.example.com"]}` (max 200 hostnames)

Response: `{"results": [{"hostname": "example.com", "asn": 15169, "org_name": "Google LLC", "org_country": "US"}]}`

### `GET /healthz` / `GET /readyz`

Liveness / readiness probes.

## License

EUPL-1.2 — see [LICENSE](LICENSE).

## Dependencies

| Package | License |
|---|---|
| fastapi | MIT |
| uvicorn | BSD-3-Clause |
| httpx | BSD-3-Clause |
| pydantic-settings | MIT |
| pytest (dev) | MIT |
| pytest-asyncio (dev) | Apache-2.0 |
| respx (dev) | BSD-3-Clause |
| ruff (dev) | MIT |
