"""
Datadog API client wrapper.

Uses the official datadog-api-client Python library with:
- Automatic rate-limit awareness
- Retry with exponential backoff via tenacity
- Singleton pattern for connection reuse
- Configurable site (US, EU, US3, US5, etc.)
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from collections.abc import Callable

from datadog_api_client import ApiClient, Configuration
from datadog_api_client.exceptions import ApiException
from datadog_api_client.v1.api.events_api import EventsApi
from datadog_api_client.v1.api.metrics_api import MetricsApi
from datadog_api_client.v1.api.monitors_api import MonitorsApi
from datadog_api_client.v1.api.service_level_objectives_api import ServiceLevelObjectivesApi
from datadog_api_client.v2.api.incidents_api import IncidentsApi
from datadog_api_client.v2.api.logs_api import LogsApi
from datadog_api_client.v2.api.spans_api import SpansApi
from tenacity import (
    Retrying,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

RETRYABLE_EXCEPTIONS = (ConnectionError, TimeoutError, ApiException)


class DatadogClient:
    """Thread-safe singleton wrapper for the Datadog API client.

    Initialised exactly once and reused across the process (FR-008). close()
    resets the singleton so the next acquisition transparently rebuilds the
    connection instead of reusing a closed client.
    """

    _instance: Self | None = None
    _lock = threading.Lock()

    def __new__(cls) -> Self:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialised = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialised:
            return
        self._initialised = True

        config = Configuration()
        config.api_key["apiKeyAuth"] = settings.DATADOG_API_KEY
        config.api_key["appKeyAuth"] = settings.DATADOG_APP_KEY
        config.server_variables["site"] = settings.DATADOG_SITE

        self._client = ApiClient(config)

        # V1 APIs
        self.events = EventsApi(self._client)
        self.metrics = MetricsApi(self._client)
        self.monitors = MonitorsApi(self._client)
        self.slos = ServiceLevelObjectivesApi(self._client)

        # V2 APIs
        self.incidents = IncidentsApi(self._client)
        self.logs = LogsApi(self._client)
        self.spans = SpansApi(self._client)

    def close(self) -> None:
        """Close underlying HTTP client and reset singleton."""
        if self._client:
            self._client.close()
        type(self)._instance = None
        self._initialised = False

    # V1 Events
    def get_events(self, **kwargs: Any) -> dict[str, Any]:
        """List events (V1 EventsApi)."""
        response = self.events.list_events(**kwargs)
        return response.to_dict()

    # V1 Metrics
    def query_metrics(
        self,
        query: str,
        _from: int,
        to: int,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Query timeseries metrics (V1 MetricsApi)."""
        response = self.metrics.query_metrics(
            _from=_from,
            to=to,
            query=query,
            **kwargs,
        )
        return response.to_dict()

    # V1 Monitors
    def list_monitors(self, **kwargs: Any) -> list[dict[str, Any]]:
        """List all monitors."""
        response = self.monitors.list_monitors(**kwargs)
        return [m.to_dict() for m in response]

    def get_monitor(self, monitor_id: int, **kwargs: Any) -> dict[str, Any]:
        """Get a single monitor by ID."""
        response = self.monitors.get_monitor(monitor_id=monitor_id, **kwargs)
        return response.to_dict()

    def create_monitor(self, **kwargs: Any) -> dict[str, Any]:
        """Create a new monitor."""
        response = self.monitors.create_monitor(**kwargs)
        return response.to_dict()

    def update_monitor(self, monitor_id: int, **kwargs: Any) -> dict[str, Any]:
        """Update an existing monitor."""
        response = self.monitors.update_monitor(monitor_id=monitor_id, **kwargs)
        return response.to_dict()

    def delete_monitor(self, monitor_id: int, **kwargs: Any) -> dict[str, Any]:
        """Delete a monitor."""
        response = self.monitors.delete_monitor(monitor_id=monitor_id, **kwargs)
        return response.to_dict()

    # V1 SLOs
    def list_slos(self, **kwargs: Any) -> dict[str, Any]:
        """List all SLOs."""
        response = self.slos.list_slos(**kwargs)
        return response.to_dict()

    def get_slo(self, slo_id: str, **kwargs: Any) -> dict[str, Any]:
        """Get a single SLO by ID."""
        response = self.slos.get_slo(slo_id=slo_id, **kwargs)
        return response.to_dict()

    def create_slo(self, **kwargs: Any) -> dict[str, Any]:
        """Create a new SLO."""
        response = self.slos.create_slo(**kwargs)
        return response.to_dict()

    # V2 Incidents
    def list_incidents(self, **kwargs: Any) -> dict[str, Any]:
        """List incidents with optional filters."""
        response = self.incidents.list_incidents(**kwargs)
        return response.to_dict()

    def get_incident(self, incident_id: str, **kwargs: Any) -> dict[str, Any]:
        """Get a single incident by ID."""
        response = self.incidents.get_incident(incident_id=incident_id, **kwargs)
        return response.to_dict()

    def create_incident(self, **kwargs: Any) -> dict[str, Any]:
        """Create a new incident."""
        response = self.incidents.create_incident(**kwargs)
        return response.to_dict()

    def update_incident(self, incident_id: str, **kwargs: Any) -> dict[str, Any]:
        """Update an incident."""
        response = self.incidents.update_incident(incident_id=incident_id, **kwargs)
        return response.to_dict()

    # V2 Logs
    def search_logs(self, query: str, **kwargs: Any) -> dict[str, Any]:
        """Search logs via Datadog Logs API (V2)."""
        from datetime import datetime

        from datadog_api_client.v2.model.logs_list_request import LogsListRequest
        from datadog_api_client.v2.model.logs_list_request_page import (
            LogsListRequestPage,
        )
        from datadog_api_client.v2.model.logs_query_filter import LogsQueryFilter

        filt = LogsQueryFilter(query=query)
        page = LogsListRequestPage()

        if "filter_from" in kwargs:
            val = kwargs.pop("filter_from")
            filt._from = val.isoformat() if isinstance(val, datetime) else val
        if "filter_to" in kwargs:
            val = kwargs.pop("filter_to")
            filt.to = val.isoformat() if isinstance(val, datetime) else val
        if "indexes" in kwargs:
            filt.indexes = kwargs.pop("indexes")
        if "limit" in kwargs:
            page.limit = kwargs.pop("limit")
        if "sort" in kwargs:
            page.sort = kwargs.pop("sort")

        request = LogsListRequest(filter=filt, page=page, **kwargs)
        response = self.logs.list_logs(body=request)
        return response.to_dict()

    # V2 Spans (APM)
    def list_spans(self, query: str, **kwargs: Any) -> dict[str, Any]:
        """Search APM spans (V2 SpansApi)."""
        from datetime import datetime

        from datadog_api_client.v2.model.spans_list_request import SpansListRequest

        filt: dict[str, Any] = {"query": query}
        if "filter_from" in kwargs:
            val = kwargs.pop("filter_from")
            filt["from"] = val.isoformat() if isinstance(val, datetime) else val
        if "filter_to" in kwargs:
            val = kwargs.pop("filter_to")
            filt["to"] = val.isoformat() if isinstance(val, datetime) else val
        body = {"filter": filt, **kwargs}
        request = SpansListRequest(**body)
        response = self.spans.list_spans(body=request)
        return response.to_dict()

    def aggregate_spans(self, **kwargs: Any) -> dict[str, Any]:
        """Aggregate APM spans."""
        from datadog_api_client.v2.model.spans_aggregate_request import SpansAggregateRequest

        body_filter = {"query": kwargs.pop("filter_query", None)}
        compute = kwargs.pop("compute", None)
        group_by = kwargs.pop("group_by", None)

        if compute:
            body_filter["compute"] = compute
        if group_by:
            body_filter["group_by"] = group_by

        request = SpansAggregateRequest(filter=body_filter, **kwargs)
        response = self.spans.aggregate_spans(body=request)
        return response.to_dict()

    @staticmethod
    def _is_retryable_api_error(exc: BaseException) -> bool:
        """True if the exception is retryable (rate-limit or server error)."""
        if not isinstance(exc, ApiException):
            return False
        if exc.status is None:
            return False
        return exc.status == 429 or 500 <= exc.status < 600

    async def call(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Run a synchronous SDK call in a thread with retry.

        Usage:
            result = await client.call(client.monitors.list_monitors, ...)
            result = await client.call(client.incidents.list_incidents, ...)
        """
        return await _call_with_retry(func, *args, **kwargs)


async def _call_with_retry(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Thread-offload wrapper with tenacity retry, including ApiException."""

    retryer = Retrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=(
            retry_if_exception_type(RETRYABLE_EXCEPTIONS)
            | retry_if_exception(DatadogClient._is_retryable_api_error)
        ),
    )

    for attempt in retryer:
        with attempt:
            return await asyncio.to_thread(func, *args, **kwargs)
    return None  # unreachable
