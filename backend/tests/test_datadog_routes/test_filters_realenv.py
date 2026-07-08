"""Real-environment tests for tag + period filtering across Datadog proxy paths.

Auto-skipped without DD_API_KEY / DD_APP_KEY (see conftest). When credentials are
present, these hit the live Datadog org that the api-demo sandbox seeds - services
tagged env:{prod,staging,dev} and team:observai (see api-demo/client.py APIS registry).
Each test asserts the new `tags` / `period` params are accepted (no 422) and the proxy
forwards them without crashing (200 or 502 from the upstream Datadog call).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient

P = "/api/v1/datadog"

# Known sandbox tags (see api-demo/client.py APIS registry)
SANDBOX_ENV = "env:prod"
SANDBOX_PERIOD = "7d"


@pytest.mark.asyncio
async def test_monitors_tag_and_period(client: AsyncClient):
    resp = await client.get(
        f"{P}/monitors", params={"tags": [SANDBOX_ENV], "period": SANDBOX_PERIOD}
    )
    assert resp.status_code != 422
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_incidents_tag_and_period(client: AsyncClient):
    resp = await client.get(
        f"{P}/incidents", params={"tags": [SANDBOX_ENV], "period": SANDBOX_PERIOD}
    )
    assert resp.status_code != 422
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_events_tag_and_period(client: AsyncClient):
    resp = await client.get(f"{P}/events", params={"tags": [SANDBOX_ENV], "period": SANDBOX_PERIOD})
    assert resp.status_code != 422
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_metrics_filter_tags_and_period(client: AsyncClient):
    # metrics timeseries uses filter_tags (UST) alongside the scope `tags` string
    resp = await client.get(
        f"{P}/metrics",
        params={
            "metric": "system.cpu.user",
            "filter_tags": [SANDBOX_ENV],
            "period": SANDBOX_PERIOD,
        },
    )
    assert resp.status_code != 422
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_metrics_list_filter_tags_and_period(client: AsyncClient):
    resp = await client.get(
        f"{P}/metrics/list", params={"tags": [SANDBOX_ENV], "period": SANDBOX_PERIOD}
    )
    assert resp.status_code != 422
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_logs_tag_and_period(client: AsyncClient):
    resp = await client.get(f"{P}/logs", params={"tags": [SANDBOX_ENV], "period": SANDBOX_PERIOD})
    assert resp.status_code != 422
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_slos_tag_and_period(client: AsyncClient):
    resp = await client.get(f"{P}/slos", params={"tags": [SANDBOX_ENV], "period": SANDBOX_PERIOD})
    assert resp.status_code != 422
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_apm_services_tag_and_period(client: AsyncClient):
    resp = await client.get(
        f"{P}/apm/services", params={"tags": [SANDBOX_ENV], "period": SANDBOX_PERIOD}
    )
    assert resp.status_code != 422
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_apm_spans_tag_and_period(client: AsyncClient):
    resp = await client.get(
        f"{P}/apm/spans", params={"tags": [SANDBOX_ENV], "period": SANDBOX_PERIOD}
    )
    assert resp.status_code != 422
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_apm_resources_tag_and_period(client: AsyncClient):
    resp = await client.get(
        f"{P}/apm/resources", params={"tags": [SANDBOX_ENV], "period": SANDBOX_PERIOD}
    )
    assert resp.status_code != 422
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_rum_tag_and_period(client: AsyncClient):
    resp = await client.get(f"{P}/rum", params={"tags": [SANDBOX_ENV], "period": SANDBOX_PERIOD})
    assert resp.status_code != 422
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_fleet_tag_and_period(client: AsyncClient):
    resp = await client.get(
        f"{P}/fleet/agents", params={"tags": [SANDBOX_ENV], "period": SANDBOX_PERIOD}
    )
    assert resp.status_code != 422
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_synthetics_tag_and_period(client: AsyncClient):
    resp = await client.get(
        f"{P}/synthetics", params={"tags": [SANDBOX_ENV], "period": SANDBOX_PERIOD}
    )
    assert resp.status_code != 422
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_error_tracking_trackers_tag_and_period(client: AsyncClient):
    resp = await client.get(
        f"{P}/error-tracking/trackers",
        params={"tags": [SANDBOX_ENV], "period": SANDBOX_PERIOD},
    )
    assert resp.status_code != 422
    assert resp.status_code in (200, 502)


@pytest.mark.asyncio
async def test_error_tracking_events_tag_and_period(client: AsyncClient):
    resp = await client.post(
        f"{P}/error-tracking/events",
        params={"tags": [SANDBOX_ENV], "period": SANDBOX_PERIOD},
    )
    assert resp.status_code != 422
    assert resp.status_code in (200, 502)
