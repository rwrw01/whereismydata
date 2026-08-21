import httpx
import respx

from src.service.cache import TTLCache
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
        client = RipeStatClient(http_client, BASE_URL, cache=TTLCache())
        asn = await client.get_asn("93.184.216.34")

    assert asn == 15133


@respx.mock
async def test_get_asn_returns_none_when_no_asns():
    respx.get(BASE_URL, params={"resource": "10.0.0.1"}).mock(
        return_value=httpx.Response(200, json={"data": {"asns": [], "prefix": ""}})
    )

    async with httpx.AsyncClient() as http_client:
        client = RipeStatClient(http_client, BASE_URL, cache=TTLCache())
        asn = await client.get_asn("10.0.0.1")

    assert asn is None


@respx.mock
async def test_get_asn_returns_none_on_http_error():
    respx.get(BASE_URL, params={"resource": "1.2.3.4"}).mock(return_value=httpx.Response(500))

    async with httpx.AsyncClient() as http_client:
        client = RipeStatClient(http_client, BASE_URL, cache=TTLCache())
        asn = await client.get_asn("1.2.3.4")

    assert asn is None


@respx.mock
async def test_get_asn_returns_none_when_data_is_null():
    """A syntactically valid response with data=null must not raise AttributeError."""
    respx.get(BASE_URL, params={"resource": "1.2.3.4"}).mock(
        return_value=httpx.Response(200, json={"data": None})
    )

    async with httpx.AsyncClient() as http_client:
        client = RipeStatClient(http_client, BASE_URL, cache=TTLCache())
        asn = await client.get_asn("1.2.3.4")

    assert asn is None


@respx.mock
async def test_get_asn_returns_none_when_response_is_a_json_array():
    respx.get(BASE_URL, params={"resource": "1.2.3.4"}).mock(
        return_value=httpx.Response(200, json=["unexpected"])
    )

    async with httpx.AsyncClient() as http_client:
        client = RipeStatClient(http_client, BASE_URL, cache=TTLCache())
        asn = await client.get_asn("1.2.3.4")

    assert asn is None


@respx.mock
async def test_get_asn_returns_none_when_asns_is_a_dict():
    respx.get(BASE_URL, params={"resource": "1.2.3.4"}).mock(
        return_value=httpx.Response(200, json={"data": {"asns": {"0": "15133"}}})
    )

    async with httpx.AsyncClient() as http_client:
        client = RipeStatClient(http_client, BASE_URL, cache=TTLCache())
        asn = await client.get_asn("1.2.3.4")

    assert asn is None


@respx.mock
async def test_get_asn_returns_none_when_asn_is_not_numeric():
    respx.get(BASE_URL, params={"resource": "1.2.3.4"}).mock(
        return_value=httpx.Response(200, json={"data": {"asns": [{"nested": "object"}]}})
    )

    async with httpx.AsyncClient() as http_client:
        client = RipeStatClient(http_client, BASE_URL, cache=TTLCache())
        asn = await client.get_asn("1.2.3.4")

    assert asn is None


@respx.mock
async def test_get_asn_uses_cache_on_second_call():
    route = respx.get(BASE_URL, params={"resource": "93.184.216.34"}).mock(
        return_value=httpx.Response(200, json={"data": {"asns": ["15133"], "prefix": ""}})
    )

    async with httpx.AsyncClient() as http_client:
        cache = TTLCache()
        client = RipeStatClient(http_client, BASE_URL, cache=cache)
        first = await client.get_asn("93.184.216.34")
        second = await client.get_asn("93.184.216.34")

    assert first == 15133
    assert second == 15133
    assert route.call_count == 1


@respx.mock
async def test_get_asn_caches_confirmed_absence_of_an_asn():
    route = respx.get(BASE_URL, params={"resource": "10.0.0.1"}).mock(
        return_value=httpx.Response(200, json={"data": {"asns": [], "prefix": ""}})
    )

    async with httpx.AsyncClient() as http_client:
        cache = TTLCache()
        client = RipeStatClient(http_client, BASE_URL, cache=cache)
        assert await client.get_asn("10.0.0.1") is None
        assert await client.get_asn("10.0.0.1") is None

    assert route.call_count == 1


@respx.mock
async def test_get_asn_does_not_cache_transient_failure():
    route = respx.get(BASE_URL, params={"resource": "1.2.3.4"}).mock(
        return_value=httpx.Response(500)
    )

    async with httpx.AsyncClient() as http_client:
        cache = TTLCache()
        client = RipeStatClient(http_client, BASE_URL, cache=cache)
        assert await client.get_asn("1.2.3.4") is None
        assert await client.get_asn("1.2.3.4") is None

    assert route.call_count == 2  # NOT cached — both calls hit the network
