from __future__ import annotations

from typing import cast

import pytest
from pydantic import ValidationError

from app.datadog.filters import compose_filters, period_to_range, to_domain_kwargs
from app.datadog.schemas import DatadogFilter, Period


def test_datadogfilter_rejects_bad_period():
    with pytest.raises(ValidationError):
        # Intentionally invalid period to verify pydantic rejects it at runtime.
        DatadogFilter(tags=["env:prod"], period=cast("Period", "99d"))


def test_compose_filters_merges_tags_and_falls_back_to_global_period(monkeypatch):
    monkeypatch.setattr("app.datadog.filters.settings.DATADOG_DEFAULT_TAGS", ["team:sre"])
    monkeypatch.setattr("app.datadog.filters.settings.DATADOG_DEFAULT_PERIOD", "7d")
    composed = compose_filters(DatadogFilter(tags=["env:prod"], period=None))
    assert composed.tags == ["team:sre", "env:prod"]
    assert composed.period == "7d"


def test_compose_filters_request_period_overrides_global(monkeypatch):
    monkeypatch.setattr("app.datadog.filters.settings.DATADOG_DEFAULT_TAGS", ["team:sre"])
    monkeypatch.setattr("app.datadog.filters.settings.DATADOG_DEFAULT_PERIOD", "30d")
    composed = compose_filters(DatadogFilter(tags=["env:prod"], period="1d"))
    assert composed.tags == ["team:sre", "env:prod"]
    assert composed.period == "1d"


def test_compose_filters_no_global(monkeypatch):
    monkeypatch.setattr("app.datadog.filters.settings.DATADOG_DEFAULT_TAGS", [])
    monkeypatch.setattr("app.datadog.filters.settings.DATADOG_DEFAULT_PERIOD", None)
    composed = compose_filters(DatadogFilter(tags=["env:prod"], period="7d"))
    assert composed.tags == ["env:prod"]
    assert composed.period == "7d"


def test_period_to_range_7d():
    rng = period_to_range("7d")
    assert rng is not None
    frm, to = rng
    assert 0 < to - frm <= 7 * 86400 + 2


def test_to_domain_kwargs_monitors_csv():
    kw = to_domain_kwargs("monitors", DatadogFilter(tags=["env:prod", "team:sre"], period="7d"))
    assert kw["tags"] == "env:prod,team:sre"
    assert "from" not in kw  # monitors have no time window


def test_to_domain_kwargs_events_csv_and_range():
    kw = to_domain_kwargs("events", DatadogFilter(tags=["env:prod"], period="7d"))
    assert kw["tags"] == "env:prod"
    assert kw["start"] and kw["end"]


def test_to_domain_kwargs_incidents_query():
    kw = to_domain_kwargs("incidents", DatadogFilter(tags=["env:prod"], period=None))
    assert kw["query"] == "tags:env:prod"


def test_to_domain_kwargs_logs_query_and_range():
    kw = to_domain_kwargs("logs", DatadogFilter(tags=["env:prod"], period="7d"))
    assert kw["query"] == "tags:env:prod"
    assert kw["from"] and kw["to"]


def test_to_domain_kwargs_spans_query_and_range():
    kw = to_domain_kwargs("spans", DatadogFilter(tags=["service:api"], period="1d"))
    assert kw["query"] == "tags:service:api"
    assert kw["from"] and kw["to"]


def test_to_domain_kwargs_metrics_query_period():
    kw = to_domain_kwargs("metrics", DatadogFilter(tags=None, period="1d"))
    assert kw["from_ts"] and kw["to_ts"]


def test_to_domain_kwargs_metrics_explore_filter_tags():
    kw = to_domain_kwargs("metrics_explore", DatadogFilter(tags=["env:prod"], period="7d"))
    assert kw["filter_tags"] == "env:prod"
    assert kw["from"] and kw["to"]


def test_to_domain_kwargs_slos_tags_query():
    kw = to_domain_kwargs("slos", DatadogFilter(tags=["env:prod"], period=None))
    assert kw["tags_query"] == "env:prod"


def test_to_domain_kwargs_synthetics_tags():
    kw = to_domain_kwargs("synthetics", DatadogFilter(tags=["env:prod"], period=None))
    assert kw["tags"] == "env:prod"


def test_to_domain_kwargs_error_tracking_filter_tags():
    kw = to_domain_kwargs("error_tracking", DatadogFilter(tags=["env:prod"], period=None))
    assert kw["filter[tags]"] == ["env:prod"]
