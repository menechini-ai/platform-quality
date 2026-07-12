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
from datadog_api_client.v1.model.slo_threshold import SLOThreshold
from datadog_api_client.v1.model.slo_timeframe import SLOTimeframe
from datadog_api_client.v1.model.slo_type import SLOType
from datadog_api_client.v2.api.incidents_api import IncidentsApi
from datadog_api_client.v2.api.logs_api import LogsApi
from datadog_api_client.v2.api.spans_api import SpansApi
from tenacity import (
    Retrying,
    retry_any,
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

    def __new__(cls, *_args: Any, **_kwargs: Any) -> Self:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._connect()

    def _connect(self) -> None:
        config = Configuration()
        config.api_key["apiKeyAuth"] = settings.DATADOG_API_KEY or ""
        config.api_key["appKeyAuth"] = settings.DATADOG_APP_KEY or ""
        config.server_variables["site"] = settings.DATADOG_SITE
        config.unstable_operations["list_incidents"] = True
        config.unstable_operations["search_incidents"] = True

        if not settings.DATADOG_API_KEY or not settings.DATADOG_APP_KEY:
            logger.warning(
                "DATADOG_API_KEY / DATADOG_APP_KEY not set; client may fail to authenticate"
            )

        self._api_client = ApiClient(config)
        self.metrics = MetricsApi(self._api_client)
        self.monitors = MonitorsApi(self._api_client)
        self.events = EventsApi(self._api_client)
        self.slos = ServiceLevelObjectivesApi(self._api_client)
        self.incidents = IncidentsApi(self._api_client)
        self.logs = LogsApi(self._api_client)
        self.spans = SpansApi(self._api_client)

    @classmethod
    def get_instance(cls) -> Self:
        """Return the shared singleton, creating it on first use."""
        return cls()

    async def query_metrics(self, query: str, from_ts: int, to_ts: int) -> Any:
        """Query Datadog metrics via the shared retry/thread-offload path."""
        return await self.call(self.metrics.query_metrics, query=query, _from=from_ts, to=to_ts)

    def list_monitors(self, **kwargs: Any) -> list[dict[str, Any]]:
        """List all Datadog monitors."""
        response = self.monitors.list_monitors(**kwargs)
        return [m.to_dict() for m in response]

    def list_incidents(self, **kwargs: Any) -> list[dict[str, Any]]:
        """List Datadog incidents."""
        # Map page_number -> page_offset for SDK
        if "page_number" in kwargs:
            kwargs["page_offset"] = kwargs.pop("page_number")
        response = self.incidents.list_incidents(**kwargs)
        # Unstable operations return raw dict, not SDK wrapper
        if hasattr(response, "to_dict"):
            raw = response.to_dict()
            data = raw.get("data", [])
            return [i.to_dict() if hasattr(i, "to_dict") else i for i in data]
        data = response.get("data", [])
        return [i.to_dict() if hasattr(i, "to_dict") else i for i in data]

    def get_incident(self, incident_id: str) -> dict[str, Any]:
        """Get a single incident by ID."""
        response = self.incidents.get_incident(incident_id=incident_id)
        return response.to_dict()

    def search_incidents(self, query: str) -> list[dict[str, Any]]:
        """Search incidents by query string."""
        response = self.incidents.search_incidents(query=query)
        return [i.to_dict() for i in (response.data or [])]

    def search_logs(self, query: str, **kwargs: Any) -> dict[str, Any]:
        """Search logs via Datadog Logs API (V2)."""
        from datetime import datetime

        from datadog_api_client.v2.model.logs_list_request import LogsListRequest
        from datadog_api_client.v2.model.logs_list_request_page import (
            LogsListRequestPage,
        )
        from datadog_api_client.v2.model.logs_query_filter import LogsQueryFilter
        from datadog_api_client.v2.model.logs_sort import LogsSort

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

        body = {"filter": filt, "page": page}

        if "sort" in kwargs:
            sort_val = kwargs.pop("sort")
            if sort_val == "-timestamp":
                body["sort"] = LogsSort.TIMESTAMP_DESCENDING
            elif sort_val == "timestamp":
                body["sort"] = LogsSort.TIMESTAMP_ASCENDING
            elif isinstance(sort_val, LogsSort):
                body["sort"] = sort_val

        request = LogsListRequest(**body)
        response = self.logs.list_logs(body=request)
        return response.to_dict()

    def list_slos(self, **kwargs: Any) -> list[dict[str, Any]]:
        """List all SLOs."""
        response = self.slos.list_slos(**kwargs)
        raw = response.to_dict()
        data = raw.get("data", [])
        return [s.to_dict() if hasattr(s, "to_dict") else s for s in data]

    def create_slo(
        self,
        name: str,
        monitor_ids: list[int],
        target: float = 99.0,
        warning: float | None = None,
        timeframe: str = "30d",
        tags: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Create a monitor-based SLO. Warning must be > target."""
        if not self._api_client:
            return None
        from datadog_api_client.v1.model.service_level_objective_request import (
            ServiceLevelObjectiveRequest,
        )

        if warning is not None and warning <= target:
            warning = target + 0.5
        timeframe_map = {
            "7d": SLOTimeframe.SEVEN_DAYS,
            "30d": SLOTimeframe.THIRTY_DAYS,
            "90d": SLOTimeframe.NINETY_DAYS,
        }
        body = ServiceLevelObjectiveRequest(
            type=SLOType.MONITOR,
            name=name,
            thresholds=[
                SLOThreshold(
                    target=target,
                    timeframe=timeframe_map.get(timeframe, SLOTimeframe.THIRTY_DAYS),
                    warning=warning or target + 0.5,
                )
            ],
            monitor_ids=monitor_ids,
            tags=tags or ["team:observai"],
        )
        response = self.slos.create_slo(body=body)
        return response.to_dict()

    def create_event(self, title: str, text: str, **kwargs: Any) -> dict[str, Any]:
        """Post an event to Datadog."""
        from datadog_api_client.v1.model.event_create_request import EventCreateRequest

        body = EventCreateRequest(title=title, text=text, **kwargs)
        response = self.events.create_event(body=body)
        return response.to_dict()

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

        body = {}
        if body_filter["query"]:
            body["filter"] = body_filter
        if compute:
            from datadog_api_client.v2.model.spans_compute import SpansCompute

            body["compute"] = [SpansCompute(**compute)]
        if group_by:
            body["group_by"] = group_by
        # Pass timestamps (SDK uses _from/_to to avoid `from` reserved word)
        for key, dest in (("filter_from", "_from"), ("filter_to", "_to")):
            val = kwargs.pop(key, None)
            if val is not None and "filter" in body:
                body["filter"][dest] = val

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
            from datadog_api_client.v2.model.logs_compute import LogsCompute

            body["compute"] = [LogsCompute(**compute)]
        if group_by:
            body["group_by"] = group_by
        for key, dest in (("filter_from", "_from"), ("filter_to", "_to")):
            val = kwargs.pop(key, None)
            if val is not None and "filter" in body:
                body["filter"][dest] = val

        request = LogsAggregateRequest(**body) if body else LogsAggregateRequest()
        response = self.logs.aggregate_logs(body=request)
        return response.to_dict()

    def close(self) -> None:
        """Close the underlying API client and reset the singleton.

        The next DatadogClient() acquisition transparently rebuilds a fresh
        connection, so close() never permanently breaks acquisition (FR-008).
        """
        if getattr(self, "_api_client", None) is not None:
            self._api_client.close()
        type(self)._instance = None

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
        retry=retry_any(
            retry_if_exception_type(RETRYABLE_EXCEPTIONS),
            retry_if_exception(DatadogClient._is_retryable_api_error),
        ),
    )

    for attempt in retryer:
        with attempt:
            return await asyncio.to_thread(func, *args, **kwargs)
    return None  # unreachable
