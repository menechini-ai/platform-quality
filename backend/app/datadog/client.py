"""
Datadog API client wrapper.

Uses the official datadog-api-client Python library with:
- Automatic rate-limit awareness
- Retry with exponential backoff via tenacity
- Singleton pattern for connection reuse
- Configurable site (US, EU, US3, US5, etc.)
"""

from __future__ import annotations

import logging
from typing import Any

from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v1.api.events_api import EventsApi
from datadog_api_client.v1.api.metrics_api import MetricsApi
from datadog_api_client.v1.api.monitors_api import MonitorsApi
from datadog_api_client.v1.api.service_level_objectives_api import ServiceLevelObjectivesApi
from datadog_api_client.v2.api.incidents_api import IncidentsApi
from datadog_api_client.v2.api.logs_api import LogsApi
from datadog_api_client.v2.api.spans_api import SpansApi
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)

RETRYABLE_EXCEPTIONS = (ConnectionError, TimeoutError)


class DatadogClient:
    """Thread-safe singleton wrapper for the Datadog API client."""

    _instance: DatadogClient | None = None

    def __new__(cls, *_args: Any, **_kwargs: Any) -> DatadogClient:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        config = Configuration()
        config.api_key["apiKeyAuth"] = settings.DATADOG_API_KEY or ""
        config.api_key["appKeyAuth"] = settings.DATADOG_APP_KEY or ""
        config.server_variables["site"] = settings.DATADOG_SITE

        if not settings.DATADOG_API_KEY or not settings.DATADOG_APP_KEY:
            logger.warning("Datadog API / APP keys not configured — client will fail on calls")

        self._api_client = ApiClient(config)

        self.metrics = MetricsApi(self._api_client)
        self.monitors = MonitorsApi(self._api_client)
        self.events = EventsApi(self._api_client)
        self.slos = ServiceLevelObjectivesApi(self._api_client)
        self.incidents = IncidentsApi(self._api_client)
        self.logs = LogsApi(self._api_client)
        self.spans = SpansApi(self._api_client)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    )
    def query_metrics(self, query: str, from_ts: int, to_ts: int) -> dict[str, Any]:
        """Query Datadog metrics timeseries."""
        response = self.metrics.query_metrics(query=query, from_ts=from_ts, to=to_ts)
        return response.to_dict()

    def list_monitors(self, **kwargs: Any) -> list[dict[str, Any]]:
        """List all Datadog monitors."""
        response = self.monitors.list_monitors(**kwargs)
        return [m.to_dict() for m in response]

    def list_incidents(self, **kwargs: Any) -> list[dict[str, Any]]:
        """List Datadog incidents."""
        response = self.incidents.list_incidents(**kwargs)
        return [i.to_dict() for i in (response.to_dict().get("data", []))]

    def get_incident(self, incident_id: str) -> dict[str, Any]:
        """Get a single incident by ID."""
        response = self.incidents.get_incident(incident_id=incident_id)
        return response.to_dict()

    def search_logs(self, query: str, **kwargs: Any) -> dict[str, Any]:
        """Search logs via Datadog Logs API (V2)."""
        from datadog_api_client.v2.model.logs_list_request import LogsListRequest

        body = {"filter": {"query": query}, **kwargs}
        request = LogsListRequest(**body)
        response = self.logs.list_logs(body=request)
        return response.to_dict()

    def list_slos(self, **kwargs: Any) -> list[dict[str, Any]]:
        """List all SLOs."""
        response = self.slos.list_slos(**kwargs)
        return [s.to_dict() for s in (response.to_dict().get("data", []))]

    def create_event(self, title: str, text: str, **kwargs: Any) -> dict[str, Any]:
        """Post an event to Datadog."""
        from datadog_api_client.v1.model.event_create_request import EventCreateRequest

        body = EventCreateRequest(title=title, text=text, **kwargs)
        response = self.events.create_event(body=body)
        return response.to_dict()

    def list_spans(self, query: str, **kwargs: Any) -> dict[str, Any]:
        """Search APM spans (V2 SpansApi)."""
        from datadog_api_client.v2.model.spans_list_request import SpansListRequest

        body = {"filter": {"query": query}, **kwargs}
        request = SpansListRequest(**body)
        response = self.spans.list_spans(body=request)
        return response.to_dict()

    def aggregate_spans(self, **kwargs: Any) -> dict[str, Any]:
        """Aggregate APM spans."""
        from datadog_api_client.v2.model.spans_aggregate_request import SpansAggregateRequest

        body_filter = {"query": kwargs.pop("filter_query", None)}
        compute = kwargs.pop("compute", None)
        group_by = kwargs.pop("group_by", None)

        body = {}
        if body_filter["query"]:
            body["filter"] = body_filter
        if compute:
            from datadog_api_client.v2.model.spans_aggregate_request_compute import (
                SpansAggregateRequestCompute,
            )

            body["compute"] = [SpansAggregateRequestCompute(**compute)]
        if group_by:
            body["group_by"] = group_by
        # Pass timestamps
        for key in ("filter_from", "filter_to"):
            val = kwargs.pop(key, None)
            if val is not None and "filter" in body:
                body["filter"][key.replace("filter_", "")] = val

        request = SpansAggregateRequest(**body) if body else SpansAggregateRequest()
        response = self.spans.aggregate_spans(body=request)
        return response.to_dict()

    def aggregate_logs(self, **kwargs: Any) -> dict[str, Any]:
        """Aggregate logs count by group_by facets."""
        from datadog_api_client.v2.model.logs_aggregate_request import LogsAggregateRequest

        body_filter = {"query": kwargs.pop("filter_query", None)}
        compute = kwargs.pop("compute", None)
        group_by = kwargs.pop("group_by", None)

        body = {}
        if body_filter["query"]:
            body["filter"] = body_filter
        if compute:
            from datadog_api_client.v2.model.logs_aggregate_request_compute import (
                LogsAggregateRequestCompute,
            )

            body["compute"] = [LogsAggregateRequestCompute(**compute)]
        if group_by:
            body["group_by"] = group_by
        for key in ("filter_from", "filter_to"):
            val = kwargs.pop(key, None)
            if val is not None and "filter" in body:
                body["filter"][key.replace("filter_", "")] = val

        request = LogsAggregateRequest(**body) if body else LogsAggregateRequest()
        response = self.logs.aggregate_logs(body=request)
        return response.to_dict()

    def close(self) -> None:
        """Close the underlying API client."""
        if hasattr(self, "_api_client"):
            self._api_client.close()
            DatadogClient._instance = None
