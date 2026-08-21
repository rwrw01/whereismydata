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

        # Defensive shape checks: a syntactically valid JSON body is no guarantee
        # of the documented structure (e.g. /net returning a bare JSON array).
        # A wrong shape is transient/unexpected, not a confirmed "ASN unknown".
        try:
            net_body = net_response.json()
            if not isinstance(net_body, dict):
                raise PeeringDBTransientError(f"non-object /net response for ASN {asn}")
            net_data = net_body.get("data", [])
            if not isinstance(net_data, list):
                raise PeeringDBTransientError(f"non-list /net data for ASN {asn}")
        except (ValueError, TypeError, KeyError) as e:
            raise PeeringDBTransientError(f"malformed /net response for ASN {asn}") from e

        if not net_data:
            return None

        entry = net_data[0]
        if not isinstance(entry, dict):
            raise PeeringDBTransientError(f"non-object /net entry for ASN {asn}")
        org_name = entry.get("name")
        org_id = entry.get("org_id")

        org_country = None
        if org_id:
            try:
                org_response = await self._client.get(
                    f"{self._base_url}/org/{org_id}", headers=self._headers
                )
                if org_response.status_code == 200:
                    org_body = org_response.json()
                    org_rows = org_body.get("data", []) if isinstance(org_body, dict) else []
                    if isinstance(org_rows, list) and org_rows and isinstance(org_rows[0], dict):
                        org_country = org_rows[0].get("country") or None
            except (httpx.HTTPError, ValueError, TypeError, KeyError):
                logger.warning(
                    "PeeringDB /org lookup failed for org %d, degrading to org_name only", org_id
                )

        return PeeringDBOrg(org_name=org_name, org_country=org_country)
