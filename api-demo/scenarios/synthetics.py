"""Scenario: Synthetics — API + browser test creation."""

from __future__ import annotations

from client import DdClient


def run_api_test_create(client: DdClient) -> dict[str, int | str]:
    """Create a synthetic API test."""
    if not client.app_key:
        return {"error": "APP_KEY required"}
    result = client.create_synthetics_test(
        "ObservAI — Health Check",
        "http://localhost:3000/",
    )
    if result:
        return {"test_id": result.get("public_id", "unknown")}
    return {"error": "create failed"}


def run_multiple_tests(client: DdClient) -> list[dict[str, int | str]]:
    """Create several endpoint tests."""
    if not client.app_key:
        return [{"error": "APP_KEY required"}]
    urls = [
        ("ObservAI API Health", "http://localhost:8000/health"),
        ("ObservAI Dashboard", "http://localhost:3000/"),
        ("Datadog API", "https://api.us5.datadoghq.com/"),
    ]
    results = []
    for name, url in urls:
        r = client.create_synthetics_test(name, url)
        if r:
            results.append({"test": name, "id": r.get("public_id", "unknown")})
    return results
