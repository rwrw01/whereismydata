import httpx
import pytest
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


async def test_lookup_rejects_oversized_hostname(client):
    response = await client.post("/lookup", json={"hostnames": ["a" * 254 + ".com"]})
    assert response.status_code == 422


async def test_lookup_rejects_empty_hostname(client):
    response = await client.post("/lookup", json={"hostnames": [""]})
    assert response.status_code == 422


@pytest.mark.parametrize(
    "hostname",
    [
        "exa mple.com",
        "http://example.com/path",
        "example.com\nevil.com",
        "exam<ple>.com",
        "example.com:8080",
    ],
)
async def test_lookup_rejects_malformed_hostname(client, hostname):
    response = await client.post("/lookup", json={"hostnames": [hostname]})
    assert response.status_code == 422


@respx.mock
async def test_lookup_deduplicates_work_but_keeps_one_result_per_input(client):
    ripestat_route = respx.get(RIPESTAT_URL, params={"resource": "93.184.216.34"}).mock(
        return_value=httpx.Response(200, json={"data": {"asns": ["15133"], "prefix": ""}})
    )
    peeringdb_route = respx.get(f"{PEERINGDB_URL}/net", params={"asn": "15133"}).mock(
        return_value=httpx.Response(
            200, json={"data": [{"org_id": 1, "name": "Edgecast Inc", "info_type": "NSP"}]}
        )
    )
    respx.get(f"{PEERINGDB_URL}/org/1").mock(
        return_value=httpx.Response(200, json={"data": [{"country": "US"}]})
    )

    response = await client.post(
        "/lookup",
        json={"hostnames": ["example.com", "example.com", "example.com"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 3
    assert [r["hostname"] for r in body["results"]] == ["example.com"] * 3
    assert all(r["org_name"] == "Edgecast Inc" for r in body["results"])
    # The work happened once, not three times.
    assert ripestat_route.call_count == 1
    assert peeringdb_route.call_count == 1
