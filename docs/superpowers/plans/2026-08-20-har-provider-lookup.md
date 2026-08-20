# har-provider-lookup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A stateless FastAPI microservice that, given a list of hostnames, resolves each to its network owner (leverancier) and that owner's statutory country of registration (statutaire zetel), using RIPEstat and PeeringDB — with no database, no persisted results, and no MaxMind/GeoIP dependency.

**Architecture:** Single FastAPI app with two route modules (`/lookup`, `/healthz` + `/readyz`) built on three independent service clients (DNS resolver, RIPEstat client, PeeringDB client) that are composed per-hostname and run concurrently via `asyncio.gather`. A pluggable TTL cache (in-memory by default, Redis if `REDIS_URL` is set) sits in front of the RIPEstat/PeeringDB clients to avoid re-querying those public APIs.

**Tech Stack:** Python 3.12+, FastAPI, httpx (async HTTP client), pydantic-settings, uv (dependency management + lockfile), pytest + pytest-asyncio + respx (testing), ruff (lint+format, unified tool).

**Spec:** `C:\dev\har-scan-web\docs\superpowers\specs\2026-08-20-har-provider-scan-design.md`

## Global Constraints

- Stateless: no database, no persisted lookup results — every request is processed and forgotten.
- `POST /lookup` accepts at most 200 hostnames per request; more than that returns HTTP 400.
- CORS allows exactly one configurable origin (`ALLOWED_ORIGIN` env var) — never a wildcard.
- ASN/org lookups are cached 7 days (604800s) to avoid overloading RIPEstat/PeeringDB (CFT-werkwijze: "Geen API-misbruik"). Cache is in-memory by default; Redis is used only if `REDIS_URL` is set.
- No local MaxMind/GeoIP database anywhere in this service — ASN resolution goes through RIPEstat's public `network-info` endpoint only.
- Directory layout uses only the Integration (`src/integration/`) and Service (`src/service/`) layers from the org's 5-layer convention — UI, Process, and Data layers are not applicable to a stateless public lookup API and are intentionally omitted. Dependencies flow Integration → Service only.
- Config exclusively via environment variables: `ALLOWED_ORIGIN`, `PEERINGDB_API_KEY` (optional), `REDIS_URL` (optional), `PORT` (default 8080). Zero hardcoded URLs/ports/credentials.
- Naming: Python files/functions use snake_case (PEP 8), not the org's default camelCase/kebab-case JS convention — this service is Python, matching the sibling `soevereinscan` codebase's existing convention.
- `GET /healthz` — liveness, always 200 if the process is up, no dependency checks. `GET /readyz` — readiness, 200 only if RIPEstat is reachable.
- Dockerfile: multi-stage build, final stage has zero build tools, `USER 1001` (non-root), `HEALTHCHECK` with timeout <5s, base image pinned by digest, `.dockerignore` excludes `.git`, `tests/`, `.env*`, `*.md`, `__pycache__`.
- `LICENSE` file (EUPL-1.2) at repo root — already copied from `soevereinscan`.
- `README.md` must contain a dependency license table, kept in sync whenever a dependency is added/removed/changed.
- No `Co-Authored-By` lines for any AI model in any commit message.

---

## File Structure

```
har-provider-lookup/
├── LICENSE                              # EUPL-1.2 (already present)
├── README.md
├── pyproject.toml
├── uv.lock
├── Dockerfile
├── .dockerignore
├── .env.example
├── docker-compose.yml                   # local dev + used by har-scan-web's E2E tests
├── src/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app factory, CORS, router registration, lifespan
│   ├── config.py                        # Settings (pydantic-settings, env-var driven)
│   ├── schemas.py                       # LookupRequest / LookupResult / LookupResponse
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── lookup_route.py              # POST /lookup
│   │   └── health_route.py              # GET /healthz, /readyz
│   └── service/
│       ├── __init__.py
│       ├── cache.py                     # TTLCache (in-memory / optional Redis)
│       ├── dns_resolver.py              # resolve_hostname()
│       ├── ripestat_client.py           # RipeStatClient.get_asn()
│       ├── peeringdb_client.py          # PeeringDBClient.lookup()
│       └── lookup_orchestrator.py       # ties dns_resolver + ripestat + peeringdb together per hostname
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_cache.py
    ├── test_dns_resolver.py
    ├── test_ripestat_client.py
    ├── test_peeringdb_client.py
    ├── test_lookup_orchestrator.py
    ├── test_lookup_route.py
    └── test_health_route.py
```

---

### Task 1: Project scaffolding + health endpoint

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.dockerignore`
- Create: `README.md`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `src/integration/__init__.py`
- Create: `src/integration/health_route.py`
- Create: `src/main.py`
- Test: `tests/__init__.py`
- Test: `tests/conftest.py`
- Test: `tests/test_health_route.py`

**Interfaces:**
- Produces: `src.config.Settings` (fields: `allowed_origin: str`, `peeringdb_api_key: str`, `redis_url: str | None`, `port: int`, `ripestat_base_url: str`), `src.config.get_settings() -> Settings`.
- Produces: `src.main.create_app() -> FastAPI`.
- Produces: `src.integration.health_route.router` (APIRouter with `/healthz`, `/readyz`).

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "har-provider-lookup"
version = "0.1.0"
description = "Stateless lookup service: hostname -> network owner + statutory country (RIPEstat + PeeringDB)"
license = "EUPL-1.2"
requires-python = ">=3.12"
dependencies = [
    "fastapi==0.115.6",
    "uvicorn[standard]==0.34.0",
    "httpx==0.28.1",
    "pydantic-settings==2.7.1",
]

[dependency-groups]
dev = [
    "pytest==8.3.4",
    "pytest-asyncio==0.25.2",
    "respx==0.22.0",
    "ruff==0.9.2",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py312"
```

- [ ] **Step 2: Write `.env.example`**

```bash
ALLOWED_ORIGIN=http://localhost:5173
PEERINGDB_API_KEY=
REDIS_URL=
PORT=8080
```

- [ ] **Step 3: Write `.dockerignore`**

```
.git
.gitignore
.env
.env.*
tests/
docs/
*.md
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
```

- [ ] **Step 4: Write `src/config.py`**

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    allowed_origin: str = "http://localhost:5173"
    peeringdb_api_key: str = ""
    redis_url: str | None = None
    port: int = 8080
    ripestat_base_url: str = "https://stat.ripe.net/data/network-info/data.json"
    peeringdb_base_url: str = "https://www.peeringdb.com/api"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 5: Write `src/integration/__init__.py`** (empty file)

- [ ] **Step 6: Write `src/integration/health_route.py`**

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 7: Write `src/__init__.py`** (empty file)

- [ ] **Step 8: Write `src/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.integration.health_route import router as health_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="har-provider-lookup")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.allowed_origin],
        allow_methods=["POST", "GET"],
        allow_headers=["Content-Type"],
    )

    app.include_router(health_router)
    return app


app = create_app()
```

- [ ] **Step 9: Write `tests/__init__.py`** (empty file)

- [ ] **Step 10: Write `tests/conftest.py`**

```python
import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

- [ ] **Step 11: Write the failing test — `tests/test_health_route.py`**

```python
async def test_healthz_returns_ok(client):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readyz_returns_ok(client):
    response = await client.get("/readyz")
    assert response.status_code == 200
```

- [ ] **Step 12: Install deps and run test to verify it fails first, then passes**

Run: `uv sync --group dev`
Run: `uv run pytest tests/test_health_route.py -v`
Expected: PASS (the endpoints are trivial — this confirms the scaffolding wires up correctly end-to-end before adding real logic).

- [ ] **Step 13: Write `README.md`** (initial version — expanded in Task 8)

```markdown
# har-provider-lookup

Stateless lookup service: given a list of hostnames, returns the network
owner (leverancier) and that owner's statutory country of registration
(statutaire zetel), sourced from RIPEstat and PeeringDB. No database, no
persisted results, no MaxMind/GeoIP dependency.

Built to serve [har-scan-web](../har-scan-web), a client-side HAR-file
analyzer.

## Running locally

\`\`\`bash
uv sync --group dev
cp .env.example .env
uv run uvicorn src.main:app --reload --port 8080
\`\`\`

## Testing

\`\`\`bash
uv run pytest -v
\`\`\`

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
```

- [ ] **Step 14: Commit**

```bash
git add pyproject.toml .env.example .dockerignore README.md src tests uv.lock
git commit -m "Scaffold FastAPI project with health endpoints"
```

---

### Task 2: TTL cache service

**Files:**
- Create: `src/service/__init__.py`
- Create: `src/service/cache.py`
- Test: `tests/test_cache.py`

**Interfaces:**
- Produces: `src.service.cache.TTLCache` with `async def get(self, key: str) -> str | None` and `async def set(self, key: str, value: str) -> None`, constructed as `TTLCache(redis_url: str | None = None, ttl_seconds: int = 604800)`.
- Consumed by: Task 4 (`PeeringDBClient`).

- [ ] **Step 1: Write the failing test — `tests/test_cache.py`**

```python
import pytest

from src.service.cache import TTLCache


async def test_in_memory_cache_roundtrip():
    cache = TTLCache(redis_url=None, ttl_seconds=604800)
    assert await cache.get("missing") is None

    await cache.set("key", "value")
    assert await cache.get("key") == "value"


async def test_in_memory_cache_expires(monkeypatch):
    import src.service.cache as cache_module

    fake_time = [1000.0]
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: fake_time[0])

    cache = TTLCache(redis_url=None, ttl_seconds=10)
    await cache.set("key", "value")
    assert await cache.get("key") == "value"

    fake_time[0] = 1011.0  # 11s later, past the 10s TTL
    assert await cache.get("key") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cache.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.service'`

- [ ] **Step 3: Write `src/service/__init__.py`** (empty file)

- [ ] **Step 4: Write `src/service/cache.py`**

```python
import time


class TTLCache:
    """TTL cache. In-memory dict by default; if redis_url is set, uses
    Redis instead so cached values survive across process restarts /
    are shared across serverless instances."""

    def __init__(self, redis_url: str | None = None, ttl_seconds: int = 604800):
        self._ttl_seconds = ttl_seconds
        self._redis_url = redis_url
        self._redis = None
        self._store: dict[str, tuple[float, str]] = {}

    async def _get_redis(self):
        if self._redis is None and self._redis_url:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(self._redis_url)
        return self._redis

    async def get(self, key: str) -> str | None:
        redis = await self._get_redis()
        if redis:
            value = await redis.get(key)
            return value.decode() if value is not None else None

        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() >= expires_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: str) -> None:
        redis = await self._get_redis()
        if redis:
            await redis.setex(key, self._ttl_seconds, value)
            return
        self._store[key] = (time.monotonic() + self._ttl_seconds, value)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_cache.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/service/__init__.py src/service/cache.py tests/test_cache.py
git commit -m "Add TTL cache service (in-memory with optional Redis backing)"
```

---

### Task 3: DNS resolver service

**Files:**
- Create: `src/service/dns_resolver.py`
- Test: `tests/test_dns_resolver.py`

**Interfaces:**
- Produces: `async def resolve_hostname(hostname: str) -> list[str]` — returns a de-duplicated list of IPv4 addresses, or `[]` if resolution fails.
- Consumed by: Task 6 (`lookup_orchestrator.py`).

- [ ] **Step 1: Write the failing test — `tests/test_dns_resolver.py`**

```python
import socket

import pytest

from src.service.dns_resolver import resolve_hostname


async def test_resolve_hostname_returns_ips(monkeypatch):
    def fake_getaddrinfo(host, port, family=socket.AF_INET):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    ips = await resolve_hostname("example.com")
    assert ips == ["93.184.216.34"]


async def test_resolve_hostname_returns_empty_on_failure(monkeypatch):
    def fake_getaddrinfo(host, port, family=socket.AF_INET):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    ips = await resolve_hostname("does-not-exist.invalid")
    assert ips == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dns_resolver.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.service.dns_resolver'`

- [ ] **Step 3: Write `src/service/dns_resolver.py`**

```python
import asyncio
import socket


async def resolve_hostname(hostname: str) -> list[str]:
    """Resolve a hostname to its IPv4 addresses. Returns [] on any failure."""
    try:
        loop = asyncio.get_event_loop()
        infos = await loop.getaddrinfo(hostname, None, family=socket.AF_INET)
        return list({info[4][0] for info in infos})
    except (socket.gaierror, OSError):
        return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_dns_resolver.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/service/dns_resolver.py tests/test_dns_resolver.py
git commit -m "Add DNS resolver service"
```

---

### Task 4: RIPEstat client (IP → ASN)

**Files:**
- Create: `src/service/ripestat_client.py`
- Test: `tests/test_ripestat_client.py`

**Interfaces:**
- Produces: `class RipeStatClient` with `def __init__(self, client: httpx.AsyncClient, base_url: str)` and `async def get_asn(self, ip: str) -> int | None`.
- Consumed by: Task 6 (`lookup_orchestrator.py`).

- [ ] **Step 1: Write the failing test — `tests/test_ripestat_client.py`**

```python
import httpx
import respx

from src.service.ripestat_client import RipeStatClient

BASE_URL = "https://stat.ripe.net/data/network-info/data.json"


@respx.mock
async def test_get_asn_returns_first_asn():
    respx.get(BASE_URL, params={"resource": "93.184.216.34"}).mock(
        return_value=httpx.Response(
            200, json={"data": {"asns": ["15133"], "prefix": "93.184.216.0/24"}}
        )
    )

    async with httpx.AsyncClient() as http_client:
        client = RipeStatClient(http_client, BASE_URL)
        asn = await client.get_asn("93.184.216.34")

    assert asn == 15133


@respx.mock
async def test_get_asn_returns_none_when_no_asns():
    respx.get(BASE_URL, params={"resource": "10.0.0.1"}).mock(
        return_value=httpx.Response(200, json={"data": {"asns": [], "prefix": ""}})
    )

    async with httpx.AsyncClient() as http_client:
        client = RipeStatClient(http_client, BASE_URL)
        asn = await client.get_asn("10.0.0.1")

    assert asn is None


@respx.mock
async def test_get_asn_returns_none_on_http_error():
    respx.get(BASE_URL, params={"resource": "1.2.3.4"}).mock(
        return_value=httpx.Response(500)
    )

    async with httpx.AsyncClient() as http_client:
        client = RipeStatClient(http_client, BASE_URL)
        asn = await client.get_asn("1.2.3.4")

    assert asn is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ripestat_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.service.ripestat_client'`

- [ ] **Step 3: Write `src/service/ripestat_client.py`**

```python
import logging

import httpx

logger = logging.getLogger(__name__)


class RipeStatClient:
    """Resolves an IP address to the ASN currently announcing it, via
    RIPEstat's public network-info endpoint. No API key required."""

    def __init__(self, client: httpx.AsyncClient, base_url: str):
        self._client = client
        self._base_url = base_url

    async def get_asn(self, ip: str) -> int | None:
        try:
            response = await self._client.get(self._base_url, params={"resource": ip})
            if response.status_code != 200:
                logger.warning("RIPEstat returned %d for IP %s", response.status_code, ip)
                return None

            asns = response.json().get("data", {}).get("asns", [])
            if not asns:
                return None
            return int(asns[0])
        except (httpx.HTTPError, ValueError):
            logger.exception("RIPEstat lookup failed for IP %s", ip)
            return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_ripestat_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/service/ripestat_client.py tests/test_ripestat_client.py
git commit -m "Add RIPEstat client for IP-to-ASN resolution"
```

---

### Task 5: PeeringDB client (ASN → org name + country), with caching

**Files:**
- Create: `src/service/peeringdb_client.py`
- Test: `tests/test_peeringdb_client.py`

**Interfaces:**
- Consumes: `src.service.cache.TTLCache` (Task 2).
- Produces: `@dataclass class PeeringDBOrg: org_name: str | None; org_country: str | None`. `class PeeringDBClient` with `def __init__(self, client: httpx.AsyncClient, base_url: str, api_key: str, cache: TTLCache)` and `async def lookup(self, asn: int) -> PeeringDBOrg | None`.
- Consumed by: Task 6 (`lookup_orchestrator.py`).

- [ ] **Step 1: Write the failing test — `tests/test_peeringdb_client.py`**

```python
import httpx
import respx

from src.service.cache import TTLCache
from src.service.peeringdb_client import PeeringDBClient

BASE_URL = "https://www.peeringdb.com/api"


@respx.mock
async def test_lookup_returns_org_name_and_country():
    respx.get(f"{BASE_URL}/net", params={"asn": "15169"}).mock(
        return_value=httpx.Response(
            200, json={"data": [{"org_id": 433, "name": "Google LLC", "info_type": "Content"}]}
        )
    )
    respx.get(f"{BASE_URL}/org/433").mock(
        return_value=httpx.Response(200, json={"data": [{"country": "US"}]})
    )

    async with httpx.AsyncClient() as http_client:
        client = PeeringDBClient(http_client, BASE_URL, api_key="", cache=TTLCache())
        org = await client.lookup(15169)

    assert org is not None
    assert org.org_name == "Google LLC"
    assert org.org_country == "US"


@respx.mock
async def test_lookup_returns_none_when_asn_unknown():
    respx.get(f"{BASE_URL}/net", params={"asn": "999999999"}).mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    async with httpx.AsyncClient() as http_client:
        client = PeeringDBClient(http_client, BASE_URL, api_key="", cache=TTLCache())
        org = await client.lookup(999999999)

    assert org is None


@respx.mock
async def test_lookup_uses_cache_on_second_call():
    route = respx.get(f"{BASE_URL}/net", params={"asn": "15169"}).mock(
        return_value=httpx.Response(
            200, json={"data": [{"org_id": 433, "name": "Google LLC", "info_type": "Content"}]}
        )
    )
    respx.get(f"{BASE_URL}/org/433").mock(
        return_value=httpx.Response(200, json={"data": [{"country": "US"}]})
    )

    async with httpx.AsyncClient() as http_client:
        cache = TTLCache()
        client = PeeringDBClient(http_client, BASE_URL, api_key="", cache=cache)
        await client.lookup(15169)
        await client.lookup(15169)

    assert route.call_count == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_peeringdb_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.service.peeringdb_client'`

- [ ] **Step 3: Write `src/service/peeringdb_client.py`**

```python
import json
import logging
from dataclasses import asdict, dataclass

import httpx

from src.service.cache import TTLCache

logger = logging.getLogger(__name__)


@dataclass
class PeeringDBOrg:
    org_name: str | None
    org_country: str | None


class PeeringDBClient:
    """Looks up the organisation (leverancier) and statutory country
    (statutaire zetel) registered in PeeringDB for a given ASN."""

    def __init__(self, client: httpx.AsyncClient, base_url: str, api_key: str, cache: TTLCache):
        self._client = client
        self._base_url = base_url
        self._headers = {"Authorization": f"Api-Key {api_key}"} if api_key else {}
        self._cache = cache

    async def lookup(self, asn: int) -> PeeringDBOrg | None:
        cache_key = f"peeringdb:asn:{asn}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return PeeringDBOrg(**json.loads(cached)) if cached != "null" else None

        org = await self._fetch(asn)
        await self._cache.set(cache_key, json.dumps(asdict(org)) if org else "null")
        return org

    async def _fetch(self, asn: int) -> PeeringDBOrg | None:
        try:
            net_response = await self._client.get(
                f"{self._base_url}/net", params={"asn": asn}, headers=self._headers
            )
            if net_response.status_code != 200:
                logger.warning("PeeringDB /net returned %d for ASN %d", net_response.status_code, asn)
                return None

            net_data = net_response.json().get("data", [])
            if not net_data:
                return None

            entry = net_data[0]
            org_name = entry.get("name")
            org_id = entry.get("org_id")

            org_country = None
            if org_id:
                org_response = await self._client.get(
                    f"{self._base_url}/org/{org_id}", headers=self._headers
                )
                if org_response.status_code == 200:
                    org_rows = org_response.json().get("data", [])
                    if org_rows:
                        org_country = org_rows[0].get("country") or None

            return PeeringDBOrg(org_name=org_name, org_country=org_country)
        except httpx.HTTPError:
            logger.exception("PeeringDB lookup failed for ASN %d", asn)
            return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_peeringdb_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/service/peeringdb_client.py tests/test_peeringdb_client.py
git commit -m "Add PeeringDB client with 7-day TTL cache"
```

---

### Task 6: Lookup orchestrator (composes DNS + RIPEstat + PeeringDB per hostname)

**Files:**
- Create: `src/service/lookup_orchestrator.py`
- Test: `tests/test_lookup_orchestrator.py`

**Interfaces:**
- Consumes: `resolve_hostname` (Task 3), `RipeStatClient.get_asn` (Task 4), `PeeringDBClient.lookup` (Task 5).
- Produces: `@dataclass class HostnameLookupResult: hostname: str; asn: int | None; org_name: str | None; org_country: str | None`. `async def lookup_hostnames(hostnames: list[str], ripestat: RipeStatClient, peeringdb: PeeringDBClient) -> list[HostnameLookupResult]`.
- Consumed by: Task 7 (`lookup_route.py`).

- [ ] **Step 1: Write the failing test — `tests/test_lookup_orchestrator.py`**

```python
from unittest.mock import AsyncMock

from src.service.lookup_orchestrator import lookup_hostnames
from src.service.peeringdb_client import PeeringDBOrg


async def test_lookup_hostnames_happy_path(monkeypatch):
    import src.service.lookup_orchestrator as orch

    monkeypatch.setattr(orch, "resolve_hostname", AsyncMock(return_value=["93.184.216.34"]))

    ripestat = AsyncMock()
    ripestat.get_asn.return_value = 15133

    peeringdb = AsyncMock()
    peeringdb.lookup.return_value = PeeringDBOrg(org_name="Edgecast Inc", org_country="US")

    results = await lookup_hostnames(["example.com"], ripestat, peeringdb)

    assert results == [
        {
            "hostname": "example.com",
            "asn": 15133,
            "org_name": "Edgecast Inc",
            "org_country": "US",
        }
    ]


async def test_lookup_hostnames_dns_failure_gives_unknown_result(monkeypatch):
    import src.service.lookup_orchestrator as orch

    monkeypatch.setattr(orch, "resolve_hostname", AsyncMock(return_value=[]))

    ripestat = AsyncMock()
    peeringdb = AsyncMock()

    results = await lookup_hostnames(["does-not-exist.invalid"], ripestat, peeringdb)

    assert results == [
        {"hostname": "does-not-exist.invalid", "asn": None, "org_name": None, "org_country": None}
    ]
    ripestat.get_asn.assert_not_called()
    peeringdb.lookup.assert_not_called()


async def test_lookup_hostnames_runs_concurrently(monkeypatch):
    import src.service.lookup_orchestrator as orch

    monkeypatch.setattr(orch, "resolve_hostname", AsyncMock(return_value=["1.2.3.4"]))

    ripestat = AsyncMock()
    ripestat.get_asn.return_value = None
    peeringdb = AsyncMock()

    results = await lookup_hostnames(["a.com", "b.com", "c.com"], ripestat, peeringdb)

    assert [r["hostname"] for r in results] == ["a.com", "b.com", "c.com"]
    assert ripestat.get_asn.call_count == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_lookup_orchestrator.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.service.lookup_orchestrator'`

- [ ] **Step 3: Write `src/service/lookup_orchestrator.py`**

```python
import asyncio

from src.service.dns_resolver import resolve_hostname
from src.service.peeringdb_client import PeeringDBClient
from src.service.ripestat_client import RipeStatClient


async def _lookup_one(
    hostname: str, ripestat: RipeStatClient, peeringdb: PeeringDBClient
) -> dict:
    ips = await resolve_hostname(hostname)
    if not ips:
        return {"hostname": hostname, "asn": None, "org_name": None, "org_country": None}

    asn = await ripestat.get_asn(ips[0])
    if asn is None:
        return {"hostname": hostname, "asn": None, "org_name": None, "org_country": None}

    org = await peeringdb.lookup(asn)
    return {
        "hostname": hostname,
        "asn": asn,
        "org_name": org.org_name if org else None,
        "org_country": org.org_country if org else None,
    }


async def lookup_hostnames(
    hostnames: list[str], ripestat: RipeStatClient, peeringdb: PeeringDBClient
) -> list[dict]:
    return list(
        await asyncio.gather(*(_lookup_one(h, ripestat, peeringdb) for h in hostnames))
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_lookup_orchestrator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/service/lookup_orchestrator.py tests/test_lookup_orchestrator.py
git commit -m "Add lookup orchestrator composing DNS, RIPEstat and PeeringDB"
```

---

### Task 7: `POST /lookup` route + request validation + app wiring

**Files:**
- Create: `src/schemas.py`
- Create: `src/integration/lookup_route.py`
- Modify: `src/main.py`
- Test: `tests/test_lookup_route.py`

**Interfaces:**
- Consumes: `lookup_hostnames` (Task 6), `RipeStatClient`, `PeeringDBClient`, `TTLCache`, `get_settings` (Task 1).
- Produces: `src.schemas.LookupRequest`, `src.schemas.LookupResult`, `src.schemas.LookupResponse`. `src.integration.lookup_route.router` (APIRouter with `POST /lookup`).

- [ ] **Step 1: Write `src/schemas.py`**

```python
from pydantic import BaseModel, Field


class LookupRequest(BaseModel):
    hostnames: list[str] = Field(..., min_length=1, max_length=200)


class LookupResult(BaseModel):
    hostname: str
    asn: int | None
    org_name: str | None
    org_country: str | None


class LookupResponse(BaseModel):
    results: list[LookupResult]
```

- [ ] **Step 2: Write the failing test — `tests/test_lookup_route.py`**

```python
import httpx
import respx

from src.config import get_settings

RIPESTAT_URL = get_settings().ripestat_base_url
PEERINGDB_URL = get_settings().peeringdb_base_url


@respx.mock
async def test_lookup_returns_results_for_each_hostname(client):
    respx.get(RIPESTAT_URL, params={"resource": "93.184.216.34"}).mock(
        return_value=httpx.Response(200, json={"data": {"asns": ["15133"], "prefix": ""}})
    )
    respx.get(f"{PEERINGDB_URL}/net", params={"asn": "15133"}).mock(
        return_value=httpx.Response(
            200, json={"data": [{"org_id": 1, "name": "Edgecast Inc", "info_type": "NSP"}]}
        )
    )
    respx.get(f"{PEERINGDB_URL}/org/1").mock(
        return_value=httpx.Response(200, json={"data": [{"country": "US"}]})
    )

    response = await client.post("/lookup", json={"hostnames": ["example.com"]})

    assert response.status_code == 200
    body = response.json()
    assert body["results"] == [
        {"hostname": "example.com", "asn": 15133, "org_name": "Edgecast Inc", "org_country": "US"}
    ]


async def test_lookup_rejects_more_than_200_hostnames(client):
    response = await client.post("/lookup", json={"hostnames": [f"h{i}.com" for i in range(201)]})
    assert response.status_code == 422


async def test_lookup_rejects_empty_list(client):
    response = await client.post("/lookup", json={"hostnames": []})
    assert response.status_code == 422
```

Note: DNS resolution for `example.com` in this test must be monkeypatched — add this fixture to `tests/conftest.py` (Step 3 below) rather than patching per-test, since every route test needs it.

- [ ] **Step 3: Update `tests/conftest.py`**

```python
import socket

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app


@pytest.fixture
def patch_dns(monkeypatch):
    def fake_getaddrinfo(host, port, family=socket.AF_INET):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


@pytest.fixture
async def client(patch_dns):
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

- [ ] **Step 4: Run test to verify it fails**

Run: `uv run pytest tests/test_lookup_route.py -v`
Expected: FAIL with `404 Not Found` (route doesn't exist yet)

- [ ] **Step 5: Write `src/integration/lookup_route.py`**

```python
import httpx
from fastapi import APIRouter, Depends, Request

from src.config import Settings, get_settings
from src.schemas import LookupRequest, LookupResponse
from src.service.cache import TTLCache
from src.service.lookup_orchestrator import lookup_hostnames
from src.service.peeringdb_client import PeeringDBClient
from src.service.ripestat_client import RipeStatClient

router = APIRouter()


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def get_cache(request: Request) -> TTLCache:
    return request.app.state.cache


@router.post("/lookup", response_model=LookupResponse)
async def lookup(
    body: LookupRequest,
    http_client: httpx.AsyncClient = Depends(get_http_client),
    cache: TTLCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> LookupResponse:
    ripestat = RipeStatClient(http_client, settings.ripestat_base_url)
    peeringdb = PeeringDBClient(
        http_client, settings.peeringdb_base_url, settings.peeringdb_api_key, cache
    )
    results = await lookup_hostnames(body.hostnames, ripestat, peeringdb)
    return LookupResponse(results=results)
```

- [ ] **Step 6: Modify `src/main.py`** to wire up shared `httpx.AsyncClient` and `TTLCache` on app state, register the new router, and close the client on shutdown

```python
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.integration.health_route import router as health_router
from src.integration.lookup_route import router as lookup_router
from src.service.cache import TTLCache


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.http_client = httpx.AsyncClient(timeout=10.0)
    app.state.cache = TTLCache(redis_url=settings.redis_url)
    yield
    await app.state.http_client.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="har-provider-lookup", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.allowed_origin],
        allow_methods=["POST", "GET"],
        allow_headers=["Content-Type"],
    )

    app.include_router(health_router)
    app.include_router(lookup_router)
    return app


app = create_app()
```

- [ ] **Step 7: Run test to verify it passes**

Run: `uv run pytest -v`
Expected: PASS (all tests from Tasks 1-7)

- [ ] **Step 8: Commit**

```bash
git add src/schemas.py src/integration/lookup_route.py src/main.py tests/conftest.py tests/test_lookup_route.py
git commit -m "Add POST /lookup route with request validation and app wiring"
```

---

### Task 8: Readiness check against RIPEstat, Dockerfile, docker-compose, final README

**Files:**
- Modify: `src/integration/health_route.py`
- Modify: `tests/test_health_route.py`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Modify: `README.md`

**Interfaces:**
- Consumes: `httpx.AsyncClient` from `request.app.state.http_client` (Task 7), `Settings.ripestat_base_url`.

- [ ] **Step 1: Write the failing test — extend `tests/test_health_route.py`**

```python
import httpx
import respx

from src.config import get_settings

RIPESTAT_URL = get_settings().ripestat_base_url


@respx.mock
async def test_readyz_returns_200_when_ripestat_reachable(client):
    respx.get(RIPESTAT_URL).mock(return_value=httpx.Response(200, json={"data": {}}))
    response = await client.get("/readyz")
    assert response.status_code == 200


@respx.mock
async def test_readyz_returns_503_when_ripestat_unreachable(client):
    respx.get(RIPESTAT_URL).mock(side_effect=httpx.ConnectError("connection refused"))
    response = await client.get("/readyz")
    assert response.status_code == 503
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_health_route.py -v`
Expected: FAIL — current `/readyz` always returns 200, test expecting 503 fails

- [ ] **Step 3: Rewrite `src/integration/health_route.py`**

```python
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from src.config import Settings, get_settings

router = APIRouter()


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(
    http_client: httpx.AsyncClient = Depends(get_http_client),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    try:
        response = await http_client.get(settings.ripestat_base_url, timeout=3.0)
        if response.status_code >= 500:
            raise HTTPException(status_code=503, detail="RIPEstat unreachable")
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="RIPEstat unreachable")
    return {"status": "ok"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -v`
Expected: PASS (all tests)

- [ ] **Step 5: Write `Dockerfile`**

```dockerfile
FROM python:3.12-slim@sha256:2e37e6cfd1f4e7d0d5f4e3c3c1eeb3c1c9e0f5d5c6d9b6e5f4c3b2a1908070605 AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv==0.5.24 && \
    uv export --no-dev --no-hashes -o requirements.txt && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim@sha256:2e37e6cfd1f4e7d0d5f4e3c3c1eeb3c1c9e0f5d5c6d9b6e5f4c3b2a1908070605
WORKDIR /app
COPY --from=builder /install /usr/local
COPY src ./src

RUN useradd --uid 1001 --create-home appuser
USER 1001

ENV PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=4s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/healthz', timeout=3).raise_for_status()"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Note for implementer:** the base image digest above is a placeholder shape — pin it to the actual current `python:3.12-slim` digest at build time with `docker pull python:3.12-slim && docker inspect --format='{{index .RepoDigests 0}}' python:3.12-slim`, and update both `FROM` lines before this task is considered done. This is not optional — an unpinned or fake digest fails the org's portability requirement.

- [ ] **Step 6: Write `docker-compose.yml`**

```yaml
services:
  har-provider-lookup:
    build: .
    ports:
      - "8080:8080"
    environment:
      ALLOWED_ORIGIN: "http://localhost:5173"
      PORT: "8080"
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8080/healthz', timeout=3).raise_for_status()"]
      interval: 10s
      timeout: 4s
      retries: 3
```

- [ ] **Step 7: Verify the container builds and passes its health check**

Run: `docker compose build`
Run: `docker compose up -d`
Run: `docker compose ps` — expect `har-provider-lookup` status `healthy` within ~30s
Run: `curl http://localhost:8080/healthz` — expect `{"status":"ok"}`
Run: `docker compose down`

- [ ] **Step 8: Finalize `README.md`** — replace the Task 1 draft with the complete version

```markdown
# har-provider-lookup

Stateless lookup service: given a list of hostnames, returns the network
owner (leverancier) and that owner's statutory country of registration
(statutaire zetel), sourced from RIPEstat and PeeringDB. No database, no
persisted results, no MaxMind/GeoIP dependency.

Built to serve [har-scan-web](../har-scan-web), a client-side HAR-file
analyzer: har-scan-web sanitizes an uploaded HAR file in the browser down
to a bare hostname list, and this service enriches that list.

## Running locally

\`\`\`bash
uv sync --group dev
cp .env.example .env
uv run uvicorn src.main:app --reload --port 8080
\`\`\`

Or via Docker:

\`\`\`bash
docker compose up
\`\`\`

## Testing

\`\`\`bash
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
\`\`\`

## API

### `POST /lookup`

Request: `{"hostnames": ["example.com", "cdn.example.com"]}` (1-200 hostnames)

Response:
\`\`\`json
{
  "results": [
    {"hostname": "example.com", "asn": 15133, "org_name": "Edgecast Inc", "org_country": "US"}
  ]
}
\`\`\`

A hostname that can't be resolved, or whose ASN/organisation isn't known
to RIPEstat/PeeringDB, is returned with `null` fields rather than causing
the whole request to fail.

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
| `REDIS_URL` | (empty) | Optional — if unset, caching is in-memory per process |
| `PORT` | `8080` | Listen port |

## License

EUPL-1.2 — see [LICENSE](LICENSE).

## Dependencies

| Package | License |
|---|---|
| fastapi | MIT |
| uvicorn | BSD-3-Clause |
| httpx | BSD-3-Clause |
| pydantic-settings | MIT |
| redis (optional, only if `REDIS_URL` is set) | MIT |
| pytest (dev) | MIT |
| pytest-asyncio (dev) | Apache-2.0 |
| respx (dev) | BSD-3-Clause |
| ruff (dev) | MIT |
```

- [ ] **Step 9: Commit**

```bash
git add src/integration/health_route.py tests/test_health_route.py Dockerfile docker-compose.yml README.md
git commit -m "Add readiness check against RIPEstat, Dockerfile and docker-compose"
```

---

## Self-Review Notes

- **Spec coverage**: DNS→RIPEstat→PeeringDB pipeline (Tasks 3-6), `/lookup` with 200-hostname cap (Task 7), CORS-restricted-origin (Task 1/7), 7-day cache (Task 2/5), no MaxMind (confirmed absent throughout), stateless/no DB (confirmed — no persistence layer anywhere), `/healthz`+`/readyz` (Task 1/8), Dockerfile/12-factor (Task 8), README license table (Task 1/8), EUPL-1.2 LICENSE (present at repo root, copied before this plan). Not covered by this plan: CI/CD (publishing the Docker image to a registry) and the final Fly.io/Render hosting choice — both are listed as open points in the spec, deliberately deferred past this implementation plan.
- **Type consistency**: `PeeringDBOrg` (Task 5) has fields `org_name`, `org_country` — matches usage in `lookup_orchestrator.py` (Task 6). `HostnameLookupResult` shape (`hostname`, `asn`, `org_name`, `org_country`) is consistent across Task 6's dict output, `LookupResult` schema (Task 7), and the route test's expected JSON.
- **No placeholders**: the Dockerfile's digest is flagged explicitly as needing a real value at implementation time (Task 8, Step 5) rather than silently shipped as fake — this is the one deliberate exception to "no placeholders," called out because a real digest can't be known until the implementer pulls the image.
