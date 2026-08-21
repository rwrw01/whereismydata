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
