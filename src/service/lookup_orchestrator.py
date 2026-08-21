import asyncio
import logging

from src.service.dns_resolver import resolve_hostname
from src.service.peeringdb_client import PeeringDBClient
from src.service.ripestat_client import RipeStatClient

logger = logging.getLogger(__name__)

MAX_CONCURRENT_LOOKUPS = 10


def _unknown(hostname: str) -> dict:
    return {"hostname": hostname, "asn": None, "org_name": None, "org_country": None}


async def _lookup_one(hostname: str, ripestat: RipeStatClient, peeringdb: PeeringDBClient) -> dict:
    ips = await resolve_hostname(hostname)
    if not ips:
        return _unknown(hostname)

    asn = await ripestat.get_asn(ips[0])
    if asn is None:
        return _unknown(hostname)

    org = await peeringdb.lookup(asn)
    return {
        "hostname": hostname,
        "asn": asn,
        "org_name": org.org_name if org else None,
        "org_country": org.org_country if org else None,
    }


async def lookup_hostnames(
    hostnames: list[str], ripestat: RipeStatClient, peeringdb: PeeringDBClient
) -> list[dict]:
    # Cap in-flight work so a large batch cannot fan out into an unbounded burst
    # of DNS/RIPEstat/PeeringDB round-trips ("Geen API-misbruik").
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_LOOKUPS)

    async def _guarded(hostname: str) -> dict:
        async with semaphore:
            return await _lookup_one(hostname, ripestat, peeringdb)

    # return_exceptions=True is defense in depth: one hostname raising an
    # unforeseen exception must not take down the results for the whole batch.
    results = await asyncio.gather(
        *(_guarded(h) for h in hostnames),
        return_exceptions=True,
    )
    output = []
    for hostname, result in zip(hostnames, results):
        if isinstance(result, BaseException):
            logger.error("Lookup failed for hostname %s", hostname, exc_info=result)
            output.append(_unknown(hostname))
        else:
            output.append(result)
    return output
