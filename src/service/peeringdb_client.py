import json
import logging
from dataclasses import asdict, dataclass

import httpx

from src.service.cache import TTLCache

logger = logging.getLogger(__name__)


@dataclass
class PeeringDBOrg:
    org_name: str | None
    org_country: str | None


class PeeringDBClient:
    """Looks up the organisation (leverancier) and statutory country
    (statutaire zetel) registered in PeeringDB for a given ASN."""

    def __init__(self, client: httpx.AsyncClient, base_url: str, api_key: str, cache: TTLCache):
        self._client = client
        self._base_url = base_url
        self._headers = {"Authorization": f"Api-Key {api_key}"} if api_key else {}
        self._cache = cache

    async def lookup(self, asn: int) -> PeeringDBOrg | None:
        cache_key = f"peeringdb:asn:{asn}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return PeeringDBOrg(**json.loads(cached)) if cached != "null" else None

        org = await self._fetch(asn)
        await self._cache.set(cache_key, json.dumps(asdict(org)) if org else "null")
        return org

    async def _fetch(self, asn: int) -> PeeringDBOrg | None:
        try:
            net_response = await self._client.get(
                f"{self._base_url}/net", params={"asn": asn}, headers=self._headers
            )
            if net_response.status_code != 200:
                logger.warning("PeeringDB /net returned %d for ASN %d", net_response.status_code, asn)
                return None

            net_data = net_response.json().get("data", [])
            if not net_data:
                return None

            entry = net_data[0]
            org_name = entry.get("name")
            org_id = entry.get("org_id")

            org_country = None
            if org_id:
                org_response = await self._client.get(
                    f"{self._base_url}/org/{org_id}", headers=self._headers
                )
                if org_response.status_code == 200:
                    org_rows = org_response.json().get("data", [])
                    if org_rows:
                        org_country = org_rows[0].get("country") or None

            return PeeringDBOrg(org_name=org_name, org_country=org_country)
        except httpx.HTTPError:
            logger.exception("PeeringDB lookup failed for ASN %d", asn)
            return None
