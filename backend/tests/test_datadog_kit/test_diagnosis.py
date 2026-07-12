from __future__ import annotations

from app.datadog_kit.diagnosis import _fallback_diagnosis, _parse_rca_response, build_prompt
from app.datadog_kit.models import InvestigationResult, MonitorEntry, MonitorsResult


def test_fallback_no_data() -> None:
    result = InvestigationResult(query="test", time_range_minutes=60)
    d = _fallback_diagnosis(result)
    assert d.inconclusive is True
    assert d.confidence == 0.0


def test_fallback_with_alerts() -> None:
    result = InvestigationResult(
        query="test",
        time_range_minutes=60,
        monitors=MonitorsResult(
            monitors=[MonitorEntry(name="CPU Alert", overall_state="Alert")]
        ),
    )
    d = _fallback_diagnosis(result)
    assert d.inconclusive is True
    assert "CPU Alert" in d.root_cause or "monitors" in d.root_cause


def test_parse_rca_json() -> None:
    raw = '''{
        "root_cause": "memory leak in checkout service",
        "root_cause_category": "resource",
        "causal_chain": ["deploy v2.3.1", "memory spike", "OOM kills"],
        "severity": "P1",
        "confidence": 0.85,
        "evidence_refs": {"logs": ["OOM errors"], "metrics": ["memory.p95"]},
        "remediation_steps": ["rollback to v2.3.0", "add memory limit"],
        "inconclusive": false
    }'''
    d = _parse_rca_response(raw)
    assert d.root_cause == "memory leak in checkout service"
    assert d.root_cause_category == "resource"
    assert d.severity == "P1"
    assert d.confidence == 0.85
    assert d.inconclusive is False


def test_parse_rca_json_with_code_fence() -> None:
    raw = '''Some text
```json
{"root_cause": "db connection pool exhausted", "root_cause_category": "dependency",
 "causal_chain": [], "severity": "P1", "confidence": 0.7, "evidence_refs": {},
 "remediation_steps": [], "inconclusive": false}
```
more text'''
    d = _parse_rca_response(raw)
    assert d.root_cause == "db connection pool exhausted"
    assert d.confidence == 0.7


def test_build_prompt_returns_string() -> None:
    result = InvestigationResult(query="service:api", time_range_minutes=60)
    prompt = build_prompt(result)
    assert "service:api" in prompt
    assert "60 minutes" in prompt
