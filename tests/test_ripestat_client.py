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
