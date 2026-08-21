import asyncio
from unittest.mock import AsyncMock

from src.service.lookup_orchestrator import lookup_hostnames
from src.service.peeringdb_client import PeeringDBOrg


async def test_lookup_hostnames_happy_path(monkeypatch):
    import src.service.lookup_orchestrator as orch

    monkeypatch.setattr(orch, "resolve_hostname", AsyncMock(return_value=["93.184.216.34"]))

    ripestat = AsyncMock()
    ripestat.get_asn.return_value = 15133

    peeringdb = AsyncMock()
    peeringdb.lookup.return_value = PeeringDBOrg(org_name="Edgecast Inc", org_country="US")

    results = await lookup_hostnames(["example.com"], ripestat, peeringdb)

    assert results == [
        {
            "hostname": "example.com",
            "asn": 15133,
            "org_name": "Edgecast Inc",
            "org_country": "US",
        }
    ]


async def test_lookup_hostnames_dns_failure_gives_unknown_result(monkeypatch):
    import src.service.lookup_orchestrator as orch

    monkeypatch.setattr(orch, "resolve_hostname", AsyncMock(return_value=[]))

    ripestat = AsyncMock()
    peeringdb = AsyncMock()

    results = await lookup_hostnames(["does-not-exist.invalid"], ripestat, peeringdb)

    assert results == [
        {"hostname": "does-not-exist.invalid", "asn": None, "org_name": None, "org_country": None}
    ]
    ripestat.get_asn.assert_not_called()
    peeringdb.lookup.assert_not_called()


async def test_lookup_hostnames_runs_concurrently(monkeypatch):
    import src.service.lookup_orchestrator as orch

    monkeypatch.setattr(orch, "resolve_hostname", AsyncMock(return_value=["1.2.3.4"]))

    ripestat = AsyncMock()
    ripestat.get_asn.return_value = None
    peeringdb = AsyncMock()

    results = await lookup_hostnames(["a.com", "b.com", "c.com"], ripestat, peeringdb)

    assert [r["hostname"] for r in results] == ["a.com", "b.com", "c.com"]
    assert ripestat.get_asn.call_count == 3


async def test_lookup_hostnames_survives_unexpected_exception(monkeypatch):
    """One hostname blowing up must not lose the results for the whole batch."""
    import src.service.lookup_orchestrator as orch

    async def fake_resolve(hostname: str) -> list[str]:
        if hostname == "boom.example.com":
            raise RuntimeError("unforeseen failure")
        return ["93.184.216.34"]

    monkeypatch.setattr(orch, "resolve_hostname", fake_resolve)

    ripestat = AsyncMock()
    ripestat.get_asn.return_value = 15133
    peeringdb = AsyncMock()
    peeringdb.lookup.return_value = PeeringDBOrg(org_name="Edgecast Inc", org_country="US")

    results = await lookup_hostnames(
        ["ok.example.com", "boom.example.com", "also-ok.example.com"], ripestat, peeringdb
    )

    assert results == [
        {
            "hostname": "ok.example.com",
            "asn": 15133,
            "org_name": "Edgecast Inc",
            "org_country": "US",
        },
        {
            "hostname": "boom.example.com",
            "asn": None,
            "org_name": None,
            "org_country": None,
        },
        {
            "hostname": "also-ok.example.com",
            "asn": 15133,
            "org_name": "Edgecast Inc",
            "org_country": "US",
        },
    ]


async def test_lookup_hostnames_handles_oversized_label_without_raising():
    """A 64-char DNS label makes getaddrinfo raise UnicodeEncodeError; the batch
    must degrade to null fields for that hostname rather than 500."""
    ripestat = AsyncMock()
    peeringdb = AsyncMock()

    bad = "a" * 64 + ".example.com"
    results = await lookup_hostnames([bad], ripestat, peeringdb)

    assert results == [{"hostname": bad, "asn": None, "org_name": None, "org_country": None}]
    ripestat.get_asn.assert_not_called()


async def test_lookup_hostnames_caps_concurrency(monkeypatch):
    import src.service.lookup_orchestrator as orch

    in_flight = 0
    peak = 0

    async def fake_resolve(hostname: str) -> list[str]:
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return []

    monkeypatch.setattr(orch, "resolve_hostname", fake_resolve)

    hostnames = [f"h{i}.example.com" for i in range(50)]
    results = await lookup_hostnames(hostnames, AsyncMock(), AsyncMock())

    assert len(results) == 50
    assert peak <= orch.MAX_CONCURRENT_LOOKUPS
