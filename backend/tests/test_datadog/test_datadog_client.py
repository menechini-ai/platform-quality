"""Tests for the Datadog client wrapper."""

from __future__ import annotations

from app.datadog.client import DatadogClient


def test_singleton_pattern():
    """DatadogClient follows singleton pattern."""
    client1 = DatadogClient()
    client2 = DatadogClient()
    assert client1 is client2


def test_client_initialization():
    """Client initializes with API key references."""
    client = DatadogClient()
    assert hasattr(client, "metrics")
    assert hasattr(client, "monitors")
    assert hasattr(client, "incidents")
    assert hasattr(client, "slos")
    assert hasattr(client, "logs")
