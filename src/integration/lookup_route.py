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
