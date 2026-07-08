"""Datadog test configuration — skip tests if Datadog API keys aren't available."""

from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-mark tests in this directory as @pytest.mark.datadog."""
    for item in items:
        if item.fspath and "test_datadog" in str(item.fspath):
            item.add_marker(pytest.mark.datadog)


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "datadog: marks tests that need Datadog API access (skipped if DD_API_KEY not set)",
    )


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip datadog-marked tests if Datadog API keys aren't available."""
    if item.get_closest_marker("datadog") and not (
        os.environ.get("DD_API_KEY") and os.environ.get("DD_APP_KEY")
    ):
        pytest.skip("DD_API_KEY / DD_APP_KEY not set")
