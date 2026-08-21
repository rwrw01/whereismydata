import asyncio

from src.service.dns_resolver import resolve_hostname
from src.service.peeringdb_client import PeeringDBClient
from src.service.ripestat_client import RipeStatClient


async def _lookup_one(
    hostname: str, ripestat: RipeStatClient, peeringdb: PeeringDBClient
) -> dict:
    ips = await resolve_hostname(hostname)
    if not ips:
        return {"hostname": hostname, "asn": None, "org_name": None, "org_country": None}

    asn = await ripestat.get_asn(ips[0])
    if asn is None:
        return {"hostname": hostname, "asn": None, "org_name": None, "org_country": None}

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
    return list(
        await asyncio.gather(*(_lookup_one(h, ripestat, peeringdb) for h in hostnames))
    )
