import socket

import pytest

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
