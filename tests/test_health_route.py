import httpx
import respx

from src.config import get_settings
from src.integration.health_route import READINESS_PROBE_RESOURCE

RIPESTAT_URL = get_settings().ripestat_base_url


async def test_healthz_returns_ok(client):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@respx.mock
async def test_readyz_returns_200_when_ripestat_reachable(client):
    respx.get(RIPESTAT_URL).mock(return_value=httpx.Response(200, json={"data": {}}))
    response = await client.get("/readyz")
    assert response.status_code == 200


@respx.mock
async def test_readyz_sends_a_valid_resource_parameter(client):
    """RIPEstat's network-info endpoint requires `resource`; a probe without it
    is a guaranteed error response on every readiness check."""
    route = respx.get(RIPESTAT_URL, params={"resource": READINESS_PROBE_RESOURCE}).mock(
        return_value=httpx.Response(200, json={"data": {}})
    )

    response = await client.get("/readyz")

    assert response.status_code == 200
    assert route.call_count == 1


@respx.mock
async def test_readyz_returns_503_when_ripestat_unreachable(client):
    respx.get(RIPESTAT_URL).mock(side_effect=httpx.ConnectError("connection refused"))
    response = await client.get("/readyz")
    assert response.status_code == 503


@respx.mock
async def test_readyz_returns_503_when_ripestat_returns_5xx(client):
    respx.get(RIPESTAT_URL).mock(return_value=httpx.Response(500))
    response = await client.get("/readyz")
    assert response.status_code == 503
