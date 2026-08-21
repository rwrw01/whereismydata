import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from src.config import Settings, get_settings
from src.schemas import LookupRequest, LookupResponse
from src.service.cache import TTLCache
from src.service.lookup_orchestrator import lookup_hostnames
from src.service.peeringdb_client import PeeringDBClient
from src.service.rate_limiter import RateLimitExceeded, RateLimiter
from src.service.ripestat_client import RipeStatClient

router = APIRouter()


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def get_cache(request: Request) -> TTLCache:
    return request.app.state.cache


def get_rate_limiter(request: Request) -> RateLimiter:
    return request.app.state.rate_limiter


def get_client_ip(request: Request) -> str:
    """Best-effort client IP for rate limiting. Trusts the first entry of
    X-Forwarded-For (set by both candidate hosting platforms, Fly.io and
    Render); falls back to the direct peer for local/unproxied setups."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


@router.post("/lookup", response_model=LookupResponse)
async def lookup(
    request: Request,
    body: LookupRequest,
    http_client: httpx.AsyncClient = Depends(get_http_client),
    cache: TTLCache = Depends(get_cache),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    settings: Settings = Depends(get_settings),
) -> LookupResponse:
    try:
        await rate_limiter.check(get_client_ip(request))
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Try again later.",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc

    ripestat = RipeStatClient(http_client, settings.ripestat_base_url, cache)
    peeringdb = PeeringDBClient(
        http_client, settings.peeringdb_base_url, settings.peeringdb_api_key, cache
    )

    # Deduplicate before doing any work: a batch of 200 duplicates must not cause
    # 200 real DNS/RIPEstat/PeeringDB round-trips. Results are mapped back onto the
    # original list afterwards so the caller still gets one result per input entry.
    unique_hostnames = list(dict.fromkeys(body.hostnames))
    results = await lookup_hostnames(unique_hostnames, ripestat, peeringdb)
    by_hostname = {result["hostname"]: result for result in results}

    return LookupResponse(results=[by_hostname[hostname] for hostname in body.hostnames])
