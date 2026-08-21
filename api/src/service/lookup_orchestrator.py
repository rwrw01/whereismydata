import asyncio
import logging

from src.service.dns_resolver import resolve_hostname
from src.service.peeringdb_client import PeeringDBClient
from src.service.ripestat_client import RipeStatClient

logger = logging.getLogger(__name__)

MAX_CONCURRENT_LOOKUPS = 10


def _unknown(hostname: str) -> dict:
    return {
        "hostname": hostname,
        "asn": None,
        "org_name": None,
        "org_country": None,
        "org_country_source": None,
    }


async def _lookup_one(hostname: str, ripestat: RipeStatClient, peeringdb: PeeringDBClient) -> dict:
    ips = await resolve_hostname(hostname)
    if not ips:
        return _unknown(hostname)

    asn = await ripestat.get_asn(ips[0])
    if asn is None:
        return _unknown(hostname)

    org = await peeringdb.lookup(asn)
    org_name = org.org_name if org else None
    org_country = org.org_country if org else None
    org_country_source = "peeringdb" if org_country else None

    # PeeringDB org profiles are self-reported and frequently leave the
    # country field blank even for well-known networks (Microsoft, Amazon).
    # Fall back to the ASN's RIR registration country in that case — a
    # different, coarser fact (which registry region the ASN was allocated
    # in, not necessarily the org's legal seat), so the source is reported
    # alongside it rather than silently presented as if it were PeeringDB's.
    if org_country is None:
        org_country = await ripestat.get_registration_country(asn)
        if org_country is not None:
            org_country_source = "ripestat"

    return {
        "hostname": hostname,
        "asn": asn,
        "org_name": org_name,
        "org_country": org_country,
        "org_country_source": org_country_source,
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
