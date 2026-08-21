import asyncio
import socket


async def resolve_hostname(hostname: str) -> list[str]:
    """Resolve a hostname to its IPv4 addresses. Returns [] on any failure."""
    try:
        loop = asyncio.get_event_loop()
        infos = await loop.getaddrinfo(hostname, None, family=socket.AF_INET)
        # dict.fromkeys deduplicates while preserving the resolver's own ordering,
        # so the IP picked downstream is deterministic across process restarts
        # (a set's iteration order is randomized by Python hash randomization).
        return list(dict.fromkeys(info[4][0] for info in infos))
    except (socket.gaierror, OSError, UnicodeError):
        # UnicodeError (e.g. UnicodeEncodeError) is raised by getaddrinfo for
        # hostnames with a label >63 chars, non-ASCII/IDN labels, or a bare ".".
        # It is a ValueError subclass, NOT an OSError subclass.
        return []
