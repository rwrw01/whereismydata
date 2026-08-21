import logging

import httpx

from src.service.cache import TTLCache

logger = logging.getLogger(__name__)


class RipeStatTransientError(Exception):
    """Raised internally when a RIPEstat call fails transiently (network/HTTP/parse
    error, or an unexpectedly shaped response) — signals get_asn() to skip caching,
    so the next request retries instead of caching a false negative for 7 days."""


class RipeStatClient:
    """Resolves an IP address to the ASN currently announcing it, via
    RIPEstat's public network-info endpoint. No API key required."""

    def __init__(self, client: httpx.AsyncClient, base_url: str, cache: TTLCache):
        self._client = client
        self._base_url = base_url
        self._cache = cache

    async def get_asn(self, ip: str) -> int | None:
        cache_key = f"ripestat:ip:{ip}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return int(cached) if cached != "null" else None

        try:
            asn = await self._fetch(ip)
        except RipeStatTransientError:
            logger.warning("RIPEstat lookup transiently failed for IP %s, not caching", ip)
            return None

        await self._cache.set(cache_key, str(asn) if asn is not None else "null")
        return asn

    async def _fetch(self, ip: str) -> int | None:
        try:
            response = await self._client.get(self._base_url, params={"resource": ip})
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
