import logging

import httpx

from src.service.cache import TTLCache

logger = logging.getLogger(__name__)


class RipeStatTransientError(Exception):
    """Raised internally when a RIPEstat call fails transiently (network/HTTP/parse
    error, or an unexpectedly shaped response) — signals the caller to skip caching,
    so the next request retries instead of caching a false negative for 7 days."""


class RipeStatClient:
    """Two RIPEstat lookups, both public and keyless:
    - get_asn: resolves an IP address to the ASN currently announcing it
      (network-info endpoint).
    - get_registration_country: the country the ASN was registered in at its
      Regional Internet Registry (rir-stats-country endpoint). Used as a
      fallback when PeeringDB's own org.country field is blank — many large
      networks (e.g. Microsoft, Amazon) have a populated ASN/org name in
      PeeringDB but never filled in their org's address fields."""

    def __init__(
        self, client: httpx.AsyncClient, network_info_url: str, country_url: str, cache: TTLCache
    ):
        self._client = client
        self._network_info_url = network_info_url
        self._country_url = country_url
        self._cache = cache

    async def get_asn(self, ip: str) -> int | None:
        cache_key = f"ripestat:ip:{ip}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return int(cached) if cached != "null" else None

        try:
            asn = await self._fetch_asn(ip)
        except RipeStatTransientError:
            logger.warning("RIPEstat lookup transiently failed for IP %s, not caching", ip)
            return None

        await self._cache.set(cache_key, str(asn) if asn is not None else "null")
        return asn

    async def _fetch_asn(self, ip: str) -> int | None:
        try:
            response = await self._client.get(self._network_info_url, params={"resource": ip})
            if response.status_code != 200:
                logger.warning("RIPEstat returned %d for IP %s", response.status_code, ip)
                raise RipeStatTransientError(f"status {response.status_code}")

            # Defensive shape checks: a syntactically valid JSON body is no
            # guarantee of the documented structure. A wrong shape is treated as
            # transient (unexpected condition), not as a confirmed "no ASN".
            data = response.json()
            if not isinstance(data, dict):
                raise RipeStatTransientError(f"non-object response for IP {ip}")

            payload = data.get("data", {})
            if not isinstance(payload, dict):
                raise RipeStatTransientError(f"non-object data field for IP {ip}")

            asns = payload.get("asns", [])
            if not isinstance(asns, list):
                raise RipeStatTransientError(f"non-list asns field for IP {ip}")
            if not asns:
                return None

            return int(asns[0])
        except (httpx.HTTPError, ValueError, TypeError) as e:
            # int() on an unexpected type raises TypeError rather than ValueError.
            raise RipeStatTransientError(f"RIPEstat lookup failed for IP {ip}") from e

    async def get_registration_country(self, asn: int) -> str | None:
        cache_key = f"ripestat:country:{asn}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached if cached != "null" else None

        try:
            country = await self._fetch_country(asn)
        except RipeStatTransientError:
            logger.warning(
                "RIPEstat country lookup transiently failed for ASN %d, not caching", asn
            )
            return None

        await self._cache.set(cache_key, country if country is not None else "null")
        return country

    async def _fetch_country(self, asn: int) -> str | None:
        try:
            response = await self._client.get(self._country_url, params={"resource": f"AS{asn}"})
            if response.status_code != 200:
                logger.warning(
                    "RIPEstat rir-stats-country returned %d for AS%d", response.status_code, asn
                )
                raise RipeStatTransientError(f"status {response.status_code}")

            data = response.json()
            if not isinstance(data, dict):
                raise RipeStatTransientError(f"non-object response for AS{asn}")

            payload = data.get("data", {})
            if not isinstance(payload, dict):
                raise RipeStatTransientError(f"non-object data field for AS{asn}")

            resources = payload.get("located_resources", [])
            if not isinstance(resources, list):
                raise RipeStatTransientError(f"non-list located_resources field for AS{asn}")
            if not resources:
                return None

            first = resources[0]
            if not isinstance(first, dict):
                raise RipeStatTransientError(f"non-object located_resources entry for AS{asn}")

            country = first.get("location")
            if not isinstance(country, str) or not country:
                return None
            return country
        except httpx.HTTPError as e:
            raise RipeStatTransientError(f"RIPEstat country lookup failed for AS{asn}") from e
