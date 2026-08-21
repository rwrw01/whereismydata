import asyncio
import socket


async def resolve_hostname(hostname: str) -> list[str]:
    """Resolve a hostname to its IPv4 addresses. Returns [] on any failure."""
    try:
        loop = asyncio.get_event_loop()
        infos = await loop.getaddrinfo(hostname, None, family=socket.AF_INET)
        return list({info[4][0] for info in infos})
    except (socket.gaierror, OSError):
        return []
