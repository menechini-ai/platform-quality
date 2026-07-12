"""Tests for the SRE Metrics Engine (multi-metric analysis)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from app.analysis.sre_metrics import (
    CORRELATION_RULES,
    SRE_METRICS,
    CorrelationFinding,
    MetricResult,
    SREMetricsAnalyzer,
)


class TestSREMetricDefinitions:
    """Verify the SRE_METRICS catalog is well-formed."""

    def test_all_metrics_have_required_fields(self) -> None:
        required = {"id", "category", "name", "query", "warning_gt", "critical_gt", "description"}
        for metric in SRE_METRICS:
            missing = required - set(metric.keys())
            assert not missing, f"Metric {metric.get('id', '?')} missing: {missing}"

    def test_all_metrics_use_valid_categories(self) -> None:
        valid = {"cpu", "memory", "latency", "errors", "disk", "network"}
        for metric in SRE_METRICS:
            assert metric["category"] in valid, (
                f"Metric {metric['id']} has invalid category: {metric['category']}"
            )

    def test_thresholds_are_sensible(self) -> None:
        for metric in SRE_METRICS:
            assert metric["warning_gt"] < metric["critical_gt"], (
                f"Metric {metric['id']}: warning ({metric['warning_gt']})"
                f" must be < critical ({metric['critical_gt']})"
            )
            assert metric["warning_gt"] > 0, f"Metric {metric['id']}: warning threshold must be > 0"

    def test_correlation_rules_reference_existing_metrics(self) -> None:
        all_ids = {m["id"] for m in SRE_METRICS}
        for rule in CORRELATION_RULES:
            for metric_id in rule["conditions"]:
                assert metric_id in all_ids, (
                    f"Correlation rule '{rule['id']}' references unknown metric: {metric_id}"
                )


class TestClassification:
    """Test the classify function."""

    def test_classify_ok(self) -> None:
        metric_def = {"id": "cpu_user", "warning_gt": 70, "critical_gt": 90}
        assert SREMetricsAnalyzer._classify(50.0, metric_def) == "ok"

    def test_classify_warning(self) -> None:
        metric_def = {"id": "cpu_user", "warning_gt": 70, "critical_gt": 90}
        assert SREMetricsAnalyzer._classify(75.0, metric_def) == "warning"

    def test_classify_critical(self) -> None:
        metric_def = {"id": "cpu_user", "warning_gt": 70, "critical_gt": 90}
        assert SREMetricsAnalyzer._classify(95.0, metric_def) == "critical"

    def test_classify_at_threshold(self) -> None:
        metric_def = {"id": "cpu_user", "warning_gt": 70, "critical_gt": 90}
        assert SREMetricsAnalyzer._classify(70.0, metric_def) == "warning"
        assert SREMetricsAnalyzer._classify(90.0, metric_def) == "critical"
        assert SREMetricsAnalyzer._classify(69.9, metric_def) == "ok"


class TestQuerySingle:
    """Test _query_single with mocked Datadog client."""

    @staticmethod
    def _metric_def(**overrides: Any) -> dict[str, Any]:
        defs = {
            "id": "cpu_user",
            "category": "cpu",
            "name": "CPU",
            "query": "avg:system.cpu.user{${TAGS}}",
            "unit": "%",
            "warning_gt": 70,
            "critical_gt": 90,
            "description": "test",
        }
        defs.update(overrides)
        return defs

    @staticmethod
    def make_analyzer() -> tuple[Any, MagicMock]:
        mock_client = MagicMock()
        return SREMetricsAnalyzer(service="test-svc", client=mock_client), mock_client

    def test_nodata_when_no_series(self) -> None:
        analyzer, mock_client = self.make_analyzer()
        mock_client.query_metrics.return_value = {"series": []}
        result = analyzer._query_single(self._metric_def(), 0, 1000)
        assert result.status == "nodata"
        assert result.value is None

    def test_nodata_when_no_points(self) -> None:
        analyzer, mock_client = self.make_analyzer()
        mock_client.query_metrics.return_value = {"series": [{"pointlist": []}]}
        result = analyzer._query_single(self._metric_def(), 0, 1000)
        assert result.status == "nodata"

    def test_nodata_when_all_null(self) -> None:
        analyzer, mock_client = self.make_analyzer()
        mock_client.query_metrics.return_value = {
            "series": [{"pointlist": [[100, None], [200, None]]}]
        }
        result = analyzer._query_single(self._metric_def(), 0, 1000)
        assert result.status == "nodata"

    def test_classifies_ok_value(self) -> None:
        analyzer, mock_client = self.make_analyzer()
        mock_client.query_metrics.return_value = {
            "series": [{"pointlist": [[100, 50.0], [200, 55.0]]}]
        }
        result = analyzer._query_single(self._metric_def(), 0, 1000)
        assert result.status == "ok"
        assert result.value == 52.5

    def test_classifies_warning(self) -> None:
        analyzer, mock_client = self.make_analyzer()
        mock_client.query_metrics.return_value = {"series": [{"pointlist": [[100, 80.0]]}]}
        result = analyzer._query_single(self._metric_def(), 0, 1000)
        assert result.status == "warning"
        assert result.value == 80.0

    def test_classifies_critical(self) -> None:
        analyzer, mock_client = self.make_analyzer()
        mock_client.query_metrics.return_value = {"series": [{"pointlist": [[100, 95.0]]}]}
        result = analyzer._query_single(self._metric_def(), 0, 1000)
        assert result.status == "critical"
        assert result.value == 95.0

    def test_handles_query_error(self) -> None:
        analyzer, mock_client = self.make_analyzer()
        mock_client.query_metrics.side_effect = ConnectionError("API unreachable")
        result = analyzer._query_single(self._metric_def(), 0, 1000)
        assert result.status == "error"
        assert result.value is None


class TestCorrelations:
    """Test cross-metric correlation detection."""

    @staticmethod
    def make_analyzer() -> SREMetricsAnalyzer:
        return SREMetricsAnalyzer(client=MagicMock())

    @staticmethod
    def hlp(metric_id: str, status: str) -> MetricResult:
        return MetricResult(
            metric_id=metric_id,
            category="test",
            name=metric_id,
            value=50.0,
            unit="%",
            status=status,
            threshold_warning=50,
            threshold_critical=80,
            description="test",
            detail="",
        )

    def test_no_correlation_when_all_healthy(self) -> None:
        analyzer = self.make_analyzer()
        corrs = analyzer._find_correlations(
            [
                self.hlp("cpu_user", "ok"),
                self.hlp("latency_p50", "ok"),
            ]
        )
        assert len(corrs) == 0

    def test_resource_contention_detected(self) -> None:
        analyzer = self.make_analyzer()
        corrs = analyzer._find_correlations(
            [
                self.hlp("cpu_user", "critical"),
                self.hlp("latency_p50", "warning"),
                self.hlp("memory_used", "ok"),
            ]
        )
        found = [c for c in corrs if c.rule_id == "resource_contention"]
        assert len(found) == 1
        assert found[0].severity in ("warning", "critical")

    def test_disk_bottleneck_detected(self) -> None:
        analyzer = self.make_analyzer()
        corrs = analyzer._find_correlations(
            [
                self.hlp("cpu_iowait", "warning"),
                self.hlp("disk_io", "warning"),
            ]
        )
        found = [c for c in corrs if c.rule_id == "disk_bottleneck"]
        assert len(found) == 1

    def test_error_burst_detected(self) -> None:
        analyzer = self.make_analyzer()
        corrs = analyzer._find_correlations(
            [
                self.hlp("error_rate", "critical"),
                self.hlp("latency_p99", "warning"),
            ]
        )
        found = [c for c in corrs if c.rule_id == "error_burst"]
        assert len(found) == 1


class TestHealthScore:
    """Test _compute_health_score."""

    @staticmethod
    def make_analyzer() -> SREMetricsAnalyzer:
        return SREMetricsAnalyzer(client=MagicMock())

    @staticmethod
    def hlp(metric_id: str, status: str) -> MetricResult:
        return MetricResult(
            metric_id=metric_id,
            category="test",
            name=metric_id,
            value=50.0,
            unit="%",
            status=status,
            threshold_warning=50,
            threshold_critical=80,
            description="test",
            detail="",
        )

    def test_perfect_score(self) -> None:
        analyzer = self.make_analyzer()
        score = analyzer._compute_health_score([self.hlp("cpu", "ok"), self.hlp("mem", "ok")], [])
        assert score == 100.0

    def test_one_critical_reduces_score(self) -> None:
        analyzer = self.make_analyzer()
        score = analyzer._compute_health_score(
            [self.hlp("cpu", "critical"), self.hlp("mem", "ok")], []
        )
        assert score == 85.0

    def test_multiple_warnings(self) -> None:
        analyzer = self.make_analyzer()
        score = analyzer._compute_health_score(
            [self.hlp("cpu", "warning"), self.hlp("mem", "warning")], []
        )
        assert score == 90.0

    def test_score_never_below_zero(self) -> None:
        analyzer = self.make_analyzer()
        many_critical = [self.hlp(f"c{i}", "critical") for i in range(8)]
        score = analyzer._compute_health_score(many_critical, [])
        assert score >= 0.0

    def test_critical_correlation_penalty(self) -> None:
        analyzer = self.make_analyzer()
        corr = CorrelationFinding(
            rule_id="test",
            label="Test",
            description="test",
            severity="critical",
            involved_metrics=["cpu", "mem"],
        )
        score = analyzer._compute_health_score([self.hlp("cpu", "critical")], [corr])
        assert score == 75.0


class TestBuildTags:
    def test_with_service(self) -> None:
        a = SREMetricsAnalyzer(service="api-gateway", client=MagicMock())
        assert a._build_tags() == "service:api-gateway"

    def test_without_service(self) -> None:
        a = SREMetricsAnalyzer(service=None, client=MagicMock())
        assert a._build_tags() == "*"

    def test_with_explicit_tags(self) -> None:
        a = SREMetricsAnalyzer(
            tags="service:api-gateway,env:prod,tier:infra",
            client=MagicMock(),
        )
        assert a._build_tags() == "service:api-gateway,env:prod,tier:infra"

    def test_tags_overrides_service(self) -> None:
        a = SREMetricsAnalyzer(
            service="ignored-service",
            tags="service:api-gateway,env:prod",
            client=MagicMock(),
        )
        assert a._build_tags() == "service:api-gateway,env:prod"

    def test_tags_resolves_placeholder(self) -> None:
        """Verify ${TAGS} is replaced in metric query when tags is set."""
        mock_client = MagicMock()
        mock_client.query_metrics.return_value = {"series": [{"pointlist": [[100, 50.0]]}]}
        a = SREMetricsAnalyzer(
            tags="service:checkout,env:staging",
            client=mock_client,
        )
        a._query_single(
            {
                "id": "cpu_user",
                "category": "cpu",
                "name": "CPU",
                "query": "avg:system.cpu.user{${TAGS}}",
                "unit": "%",
                "warning_gt": 70,
                "critical_gt": 90,
                "description": "test",
            },
            0,
            1000,
        )
        # The query sent to Datadog should have tags resolved
        call_query = mock_client.query_metrics.call_args[1]["query"]
        assert "service:checkout" in call_query
        assert "env:staging" in call_query
        assert "{${TAGS}}" not in call_query  # placeholder was replaced


class TestAnalyzeAllSync:
    """Integration-style test for analyze_all_sync with mocked client."""

    def test_returns_all_sections(self) -> None:
        mock_client = MagicMock()
        mock_client.query_metrics.return_value = {"series": [{"pointlist": [[100, 50.0]]}]}

        analyzer = SREMetricsAnalyzer(client=mock_client)
        result = analyzer.analyze_all_sync()

        assert result.score > 0
        assert len(result.metrics) == len(SRE_METRICS)
        assert result.narrative
        assert result.findings
        assert result.recommendations is not None
        assert result.timestamp > 0

    def test_findings_have_correct_structure(self) -> None:
        mock_client = MagicMock()
        mock_client.query_metrics.return_value = {"series": [{"pointlist": [[100, 95.0]]}]}

        analyzer = SREMetricsAnalyzer(client=mock_client)
        result = analyzer.analyze_all_sync()

        sre_findings = [f for f in result.findings if f["type"] == "sre_metric"]
        assert all("metric_id" in f for f in sre_findings)
        assert all("status" in f for f in sre_findings)
        assert all("value" in f for f in sre_findings)
