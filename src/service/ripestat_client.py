import logging

import httpx

logger = logging.getLogger(__name__)


class RipeStatClient:
    """Resolves an IP address to the ASN currently announcing it, via
    RIPEstat's public network-info endpoint. No API key required."""

    def __init__(self, client: httpx.AsyncClient, base_url: str):
        self._client = client
        self._base_url = base_url

    async def get_asn(self, ip: str) -> int | None:
        try:
            response = await self._client.get(self._base_url, params={"resource": ip})
            if response.status_code != 200:
                logger.warning("RIPEstat returned %d for IP %s", response.status_code, ip)
                return None

            asns = response.json().get("data", {}).get("asns", [])
            if not asns:
                return None
            return int(asns[0])
        except (httpx.HTTPError, ValueError):
            logger.exception("RIPEstat lookup failed for IP %s", ip)
            return None
