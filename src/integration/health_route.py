import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from src.config import Settings, get_settings

router = APIRouter()

# RIPE NCC's own well-known IP. RIPEstat's network-info endpoint requires a
# `resource` parameter; probing without one is a guaranteed error response.
READINESS_PROBE_RESOURCE = "193.0.6.139"


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
        response = await http_client.get(
            settings.ripestat_base_url,
            params={"resource": READINESS_PROBE_RESOURCE},
            timeout=3.0,
        )
        if response.status_code >= 500:
            raise HTTPException(status_code=503, detail="RIPEstat unreachable")
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="RIPEstat unreachable")
    return {"status": "ok"}
