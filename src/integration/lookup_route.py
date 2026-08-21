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
