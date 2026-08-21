import socket

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app


@pytest.fixture
def patch_dns(monkeypatch):
    # asyncio's loop.getaddrinfo calls socket.getaddrinfo in an executor with
    # all positional args (host, port, family, type, proto, flags), so the
    # fake must accept the full signature, not just (host, port, family).
    def fake_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


@pytest.fixture
async def client(patch_dns):
    app = create_app()
    # ASGITransport does not send lifespan events, so app.state (http_client,
    # cache) set up in src.main.lifespan would otherwise never be populated.
    # Drive the app's own lifespan context manually to match production wiring.
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
