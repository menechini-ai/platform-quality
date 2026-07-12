"""TDD tests for the multi-phase RCA correlation engine (T013 / FR-009).

The Datadog client is faked; no live backend or database required.
"""

from typing import Any

import pytest

from app.rca.engine import ConclusionState, DependencyChain, DependencyNode, RcaEngine


class FakeDatadogClient:
    """Minimal async stand-in for the Datadog surface the engine calls."""

    def __init__(self) -> None:
        self.span_calls = 0

    async def aggregate_spans(self, **kwargs: Any) -> dict:
        self.span_calls += 1
        group_by = kwargs.get("group_by", [])
        if group_by and group_by[0].get("facet") == "service":
            return {
                "data": {
                    "attributes": {
                        "series": [
                            {"group_by": [{"facet": "service", "value": "api"}]},
                            {"group_by": [{"facet": "service", "value": "db"}]},
                        ]
                    }
                }
            }
        return {
            "data": {
                "attributes": {
                    "series": [
                        {
                            "group_by": [
                                {"facet": "service", "value": "api"},
                                {"facet": "parent_service", "value": "db"},
                            ]
                        }
                    ]
                }
            }
        }

    async def query_metrics(self, query: str, from_ts: int, to_ts: int) -> dict:  # noqa: ARG002
        return {"series": [{"pointlist": [[0, 1.0], [1, 9.0]]}]}

    async def search_logs(self, query: str, **kwargs: object) -> dict:  # noqa: ARG002
        return {"data": {"attributes": {"series": [{"value": "err"}]}}}


@pytest.mark.datadog
class TestRcaEngine:
    async def test_pipeline_builds_labeled_chain(self) -> None:
        client = FakeDatadogClient()
        engine = RcaEngine(client)
        result = await engine.run(
            "00000000-0000-0000-0000-000000000001",
            {"services": ["api", "db", "cache", "web"]},
        )

        assert isinstance(result, ConclusionState)
        assert result.root_cause == "api"
        roles = {n.role for n in result.dependency_chain.nodes}
        assert roles == {"root_cause", "propagator", "victim"}
        assert 0.0 <= result.confidence <= 1.0
        assert result.summary

    async def test_pipeline_degrades_without_client_surface(self) -> None:
        engine = RcaEngine(object())
        result = await engine.run("inc-1", {"signal": "latency spike"})

        assert isinstance(result, ConclusionState)
        assert result.root_cause == "latency spike"
        assert result.confidence == 0.0

    async def test_chain_orders_root_before_propagators(self) -> None:
        client = FakeDatadogClient()
        engine = RcaEngine(client)
        result = await engine.run("inc-2", {"services": ["api", "db", "cache", "web"]})

        chain = result.dependency_chain
        assert isinstance(chain, DependencyChain)
        assert chain.nodes[0].role == "root_cause"
        assert all(isinstance(n, DependencyNode) for n in chain.nodes)
