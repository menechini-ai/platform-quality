"""Filter composition + per-domain translation.

Constitution P1: all filter logic lives in `app/datadog/` — routers stay thin and only
pass a `DatadogFilter`. `compose_filters` merges the global default filter (from settings)
with the per-request filter; `to_domain_kwargs` maps the uniform filter onto each domain's
native Datadog parameter.

Tag representation differs per domain (verified against datadog-api-client):
- comma string: monitors, events, metrics_explore (filter_tags), slos (tags_query), synthetics
- query string `tags:k`: logs, spans, rum, apm, incidents (search_incidents)
- list: error_tracking (filter[tags])
Time windows use `from`/`to` (logs/spans/rum/apm/metrics_explore/slos), `start`/`end`
(events), or `from_ts`/`to_ts` (metrics timeseries query).
"""

from datetime import datetime, timedelta
from typing import Any

from app.core.config import settings
from app.datadog.schemas import DatadogFilter, Period

PERIOD_DAYS: dict[Period, int] = {"1d": 1, "7d": 7, "15d": 15, "30d": 30}


def compose_filters(request: DatadogFilter | None = None) -> DatadogFilter:
    """Merge the global default filter (settings) with the per-request filter.

    Tags are AND-combined; the global period is the fallback when the request omits one.
    """
    gtags = list(settings.DATADOG_DEFAULT_TAGS or [])
    gperiod = settings.DATADOG_DEFAULT_PERIOD
    rtags = list(request.tags) if request and request.tags else []
    rperiod = request.period if request else None
    return DatadogFilter(tags=gtags + rtags, period=rperiod or gperiod)


def period_to_range(period: Period | None) -> tuple[int, int] | None:
    """Map a rolling period to (from_ts, to_ts) timestamps in seconds."""
    if not period:
        return None
    days = PERIOD_DAYS[period]
    to_ts = int(datetime.now().timestamp())
    from_ts = int((datetime.now() - timedelta(days=days)).timestamp())
    return (from_ts, to_ts)


def _tag_query(tags: list[str]) -> str:
    """Render Datadog tags as a query fragment: `tags:env:prod tags:service:api`."""
    return " ".join(f"tags:{t}" for t in tags)


def to_domain_kwargs(domain: str, filt: DatadogFilter) -> dict[str, Any]:
    """Translate a composed `DatadogFilter` into a domain's native Datadog kwargs."""
    tags = filt.tags or []
    rng = period_to_range(filt.period)
    kw: dict[str, Any] = {}

    if domain == "monitors":
        if tags:
            kw["tags"] = ",".join(tags)

    elif domain == "events":
        if tags:
            kw["tags"] = ",".join(tags)
        if rng:
            kw["start"], kw["end"] = rng

    elif domain == "incidents":
        # v2 list_incidents has no tag param; route tags through search_incidents(query)
        if tags:
            kw["query"] = _tag_query(tags)

    elif domain in ("logs", "spans", "rum", "apm"):
        if tags:
            kw["query"] = _tag_query(tags)
        if rng:
            kw["from"], kw["to"] = rng

    elif domain == "metrics":
        if rng:
            kw["from_ts"], kw["to_ts"] = rng

    elif domain == "metrics_explore":
        if tags:
            kw["filter_tags"] = ",".join(tags)
        if rng:
            kw["from"], kw["to"] = rng

    elif domain == "slos":
        if tags:
            kw["tags_query"] = ",".join(tags)

    elif domain == "synthetics":
        if tags:
            kw["tags"] = ",".join(tags)

    elif domain == "fleet":
        if tags:
            kw["filter"] = _tag_query(tags)

    elif domain == "error_tracking" and tags:
        kw["filter[tags]"] = tags

    return kw
