import httpx
import respx

from src.service.cache import TTLCache
from src.service.ripestat_client import RipeStatClient

BASE_URL = "https://stat.ripe.net/data/network-info/data.json"
COUNTRY_URL = "https://stat.ripe.net/data/rir-stats-country/data.json"


def make_client(http_client, cache=None):
    return RipeStatClient(http_client, BASE_URL, COUNTRY_URL, cache or TTLCache())


@respx.mock
async def test_get_asn_returns_first_asn():
    respx.get(BASE_URL, params={"resource": "93.184.216.34"}).mock(
        return_value=httpx.Response(
            200, json={"data": {"asns": ["15133"], "prefix": "93.184.216.0/24"}}
        )
    )

    async with httpx.AsyncClient() as http_client:
        client = make_client(http_client)
        asn = await client.get_asn("93.184.216.34")

    assert asn == 15133


@respx.mock
async def test_get_asn_returns_none_when_no_asns():
    respx.get(BASE_URL, params={"resource": "10.0.0.1"}).mock(
        return_value=httpx.Response(200, json={"data": {"asns": [], "prefix": ""}})
    )

    async with httpx.AsyncClient() as http_client:
        client = make_client(http_client)
        asn = await client.get_asn("10.0.0.1")

    assert asn is None


@respx.mock
async def test_get_asn_returns_none_on_http_error():
    respx.get(BASE_URL, params={"resource": "1.2.3.4"}).mock(return_value=httpx.Response(500))

    async with httpx.AsyncClient() as http_client:
        client = make_client(http_client)
        asn = await client.get_asn("1.2.3.4")

    assert asn is None


@respx.mock
async def test_get_asn_returns_none_when_data_is_null():
    """A syntactically valid response with data=null must not raise AttributeError."""
    respx.get(BASE_URL, params={"resource": "1.2.3.4"}).mock(
        return_value=httpx.Response(200, json={"data": None})
    )

    async with httpx.AsyncClient() as http_client:
        client = make_client(http_client)
        asn = await client.get_asn("1.2.3.4")

    assert asn is None


@respx.mock
async def test_get_asn_returns_none_when_response_is_a_json_array():
    respx.get(BASE_URL, params={"resource": "1.2.3.4"}).mock(
        return_value=httpx.Response(200, json=["unexpected"])
    )

    async with httpx.AsyncClient() as http_client:
        client = make_client(http_client)
        asn = await client.get_asn("1.2.3.4")

    assert asn is None


@respx.mock
async def test_get_asn_returns_none_when_asns_is_a_dict():
    respx.get(BASE_URL, params={"resource": "1.2.3.4"}).mock(
        return_value=httpx.Response(200, json={"data": {"asns": {"0": "15133"}}})
    )

    async with httpx.AsyncClient() as http_client:
        client = make_client(http_client)
        asn = await client.get_asn("1.2.3.4")

    assert asn is None


@respx.mock
async def test_get_asn_returns_none_when_asn_is_not_numeric():
    respx.get(BASE_URL, params={"resource": "1.2.3.4"}).mock(
        return_value=httpx.Response(200, json={"data": {"asns": [{"nested": "object"}]}})
    )

    async with httpx.AsyncClient() as http_client:
        client = make_client(http_client)
        asn = await client.get_asn("1.2.3.4")

    assert asn is None


@respx.mock
async def test_get_asn_uses_cache_on_second_call():
    route = respx.get(BASE_URL, params={"resource": "93.184.216.34"}).mock(
        return_value=httpx.Response(200, json={"data": {"asns": ["15133"], "prefix": ""}})
    )

    async with httpx.AsyncClient() as http_client:
        client = make_client(http_client, cache=TTLCache())
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
        client = make_client(http_client, cache=TTLCache())
        assert await client.get_asn("10.0.0.1") is None
        assert await client.get_asn("10.0.0.1") is None

    assert route.call_count == 1


@respx.mock
async def test_get_asn_does_not_cache_transient_failure():
    route = respx.get(BASE_URL, params={"resource": "1.2.3.4"}).mock(
        return_value=httpx.Response(500)
    )

    async with httpx.AsyncClient() as http_client:
        client = make_client(http_client, cache=TTLCache())
        assert await client.get_asn("1.2.3.4") is None
        assert await client.get_asn("1.2.3.4") is None

    assert route.call_count == 2  # NOT cached — both calls hit the network


@respx.mock
async def test_get_registration_country_returns_country():
    respx.get(COUNTRY_URL, params={"resource": "AS8075"}).mock(
        return_value=httpx.Response(200, json={"data": {"located_resources": [{"location": "US"}]}})
    )

    async with httpx.AsyncClient() as http_client:
        client = make_client(http_client)
        country = await client.get_registration_country(8075)

    assert country == "US"


@respx.mock
async def test_get_registration_country_returns_none_when_no_resources():
    respx.get(COUNTRY_URL, params={"resource": "AS99999999"}).mock(
        return_value=httpx.Response(200, json={"data": {"located_resources": []}})
    )

    async with httpx.AsyncClient() as http_client:
        client = make_client(http_client)
        country = await client.get_registration_country(99999999)

    assert country is None


@respx.mock
async def test_get_registration_country_returns_none_on_http_error():
    respx.get(COUNTRY_URL, params={"resource": "AS8075"}).mock(return_value=httpx.Response(500))

    async with httpx.AsyncClient() as http_client:
        client = make_client(http_client)
        country = await client.get_registration_country(8075)

    assert country is None


@respx.mock
async def test_get_registration_country_returns_none_when_shape_is_unexpected():
    respx.get(COUNTRY_URL, params={"resource": "AS8075"}).mock(
        return_value=httpx.Response(200, json={"data": {"located_resources": "not-a-list"}})
    )

    async with httpx.AsyncClient() as http_client:
        client = make_client(http_client)
        country = await client.get_registration_country(8075)

    assert country is None


@respx.mock
async def test_get_registration_country_uses_cache_on_second_call():
    route = respx.get(COUNTRY_URL, params={"resource": "AS8075"}).mock(
        return_value=httpx.Response(200, json={"data": {"located_resources": [{"location": "US"}]}})
    )

    async with httpx.AsyncClient() as http_client:
        cache = TTLCache()
        client = make_client(http_client, cache=cache)
        first = await client.get_registration_country(8075)
        second = await client.get_registration_country(8075)

    assert first == "US"
    assert second == "US"
    assert route.call_count == 1


@respx.mock
async def test_get_registration_country_does_not_cache_transient_failure():
    route = respx.get(COUNTRY_URL, params={"resource": "AS8075"}).mock(
        return_value=httpx.Response(500)
    )

    async with httpx.AsyncClient() as http_client:
        cache = TTLCache()
        client = make_client(http_client, cache=cache)
        assert await client.get_registration_country(8075) is None
        assert await client.get_registration_country(8075) is None

    assert route.call_count == 2
