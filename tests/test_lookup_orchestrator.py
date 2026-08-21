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
