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


class PeeringDBTransientError(Exception):
    """Raised internally when a PeeringDB call fails transiently (network/HTTP/parse
    error) — signals lookup() to skip caching, so the next request retries instead
    of caching a false negative for 7 days."""


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

        try:
            org = await self._fetch(asn)
        except PeeringDBTransientError:
            logger.warning("PeeringDB lookup transiently failed for ASN %d, not caching", asn)
            return None

        await self._cache.set(cache_key, json.dumps(asdict(org)) if org else "null")
        return org

    async def _fetch(self, asn: int) -> PeeringDBOrg | None:
        try:
            net_response = await self._client.get(
                f"{self._base_url}/net", params={"asn": asn}, headers=self._headers
            )
        except httpx.HTTPError as e:
            raise PeeringDBTransientError(f"network error fetching /net for ASN {asn}") from e

        if net_response.status_code != 200:
            logger.warning("PeeringDB /net returned %d for ASN %d", net_response.status_code, asn)
            raise PeeringDBTransientError(f"status {net_response.status_code}")

        try:
            net_data = net_response.json().get("data", [])
        except ValueError as e:
            raise PeeringDBTransientError(f"malformed /net response for ASN {asn}") from e

        if not net_data:
            return None

        entry = net_data[0]
        org_name = entry.get("name")
        org_id = entry.get("org_id")

        org_country = None
        if org_id:
            try:
                org_response = await self._client.get(
                    f"{self._base_url}/org/{org_id}", headers=self._headers
                )
                if org_response.status_code == 200:
                    org_rows = org_response.json().get("data", [])
                    if org_rows:
                        org_country = org_rows[0].get("country") or None
            except (httpx.HTTPError, ValueError):
                logger.warning(
                    "PeeringDB /org lookup failed for org %d, degrading to org_name only", org_id
                )

        return PeeringDBOrg(org_name=org_name, org_country=org_country)
