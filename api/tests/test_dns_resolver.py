import socket

from src.service.dns_resolver import resolve_hostname


async def test_resolve_hostname_returns_ips(monkeypatch):
    def fake_getaddrinfo(host, port, family=socket.AF_INET, type=0, proto=0, flags=0):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    ips = await resolve_hostname("example.com")
    assert ips == ["93.184.216.34"]


async def test_resolve_hostname_returns_empty_on_failure(monkeypatch):
    def fake_getaddrinfo(host, port, family=socket.AF_INET, type=0, proto=0, flags=0):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    ips = await resolve_hostname("does-not-exist.invalid")
    assert ips == []


async def test_resolve_hostname_returns_empty_on_unicode_error(monkeypatch):
    """getaddrinfo raises UnicodeEncodeError (a ValueError, NOT an OSError) for
    labels >63 chars, non-ASCII/IDN hostnames and a bare '.'."""

    def fake_getaddrinfo(host, port, family=socket.AF_INET, type=0, proto=0, flags=0):
        raise UnicodeEncodeError("idna", host, 0, 1, "label empty or too long")

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    long_label = "a" * 64
    ips = await resolve_hostname(f"{long_label}.example.com")
    assert ips == []

    assert await resolve_hostname("möt-ünïcode.example.com") == []


async def test_resolve_hostname_does_not_raise_on_real_oversized_label():
    """No monkeypatching: exercises the real getaddrinfo path with a 64-char label."""
    ips = await resolve_hostname("a" * 64 + ".example.com")
    assert ips == []


async def test_resolve_hostname_preserves_resolver_order(monkeypatch):
    """Dedup must preserve getaddrinfo's ordering — a set's order is randomized
    per process, which would make the reported ASN non-reproducible."""

    def fake_getaddrinfo(host, port, family=socket.AF_INET, type=0, proto=0, flags=0):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.10", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("198.51.100.7", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.10", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.1", 0)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    ips = await resolve_hostname("multi.example.com")
    assert ips == ["203.0.113.10", "198.51.100.7", "192.0.2.1"]
