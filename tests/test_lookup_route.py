import httpx
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
