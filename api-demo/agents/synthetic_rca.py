"""Synthetic RCA testing — evaluates LangGraph pipeline against known incidents.

Loads incidents from ``api-demo/data/incidents.json``, runs the pipeline,
and compares the output against expected root causes to compute an accuracy
score.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agents.langgraph_pipeline import run_pipeline

_INCIDENTS_PATH = Path(__file__).resolve().parent.parent / "data" / "incidents.json"


def load_incidents(path: str | None = None) -> list[dict[str, Any]]:
    """Load incidents from JSON file."""
    p = Path(path) if path else _INCIDENTS_PATH
    with open(p, encoding="utf-8") as f:
        return json.load(f)


async def evaluate_pipeline(
    incidents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the full LangGraph pipeline against known incidents.

    Args:
        incidents: List of incident dicts (each with ``id``, ``title``,
            ``description``, ``expected_root_cause``, ``expected_runbook``).
            Defaults to loading from ``incidents.json``.

    Returns:
        Dict with ``total``, ``correct_rca``, ``has_runbook``, ``accuracy``,
        and ``results`` per incident.
    """
    if incidents is None:
        incidents = load_incidents()

    results: list[dict[str, Any]] = []
    correct_rca = 0
    has_runbook = 0

    for inc in incidents:
        inc_id = inc.get("id", "unknown")
        desc = inc.get("description", inc.get("title", ""))
        expected = inc.get("expected_root_cause", "")

        state = await run_pipeline(incident_id=inc_id, description=desc)

        analysis = (state.get("analysis") or "").lower()
        rca_match = expected.lower() in analysis if expected else False
        if rca_match:
            correct_rca += 1

        if state.get("recommendation"):
            has_runbook += 1

        results.append(
            {
                "id": inc_id,
                "rca_match": rca_match,
                "has_runbook": bool(state.get("recommendation")),
            }
        )

    total = len(incidents)
    return {
        "total": total,
        "correct_rca": correct_rca,
        "has_runbook": has_runbook,
        "accuracy": round(correct_rca / total, 2) if total > 0 else 0.0,
        "results": results,
    }


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        description="Evaluate LangGraph pipeline against known incidents"
    )
    parser.add_argument("--data", help="Path to incidents JSON (default: data/incidents.json)")
    args = parser.parse_args()

    incidents = load_incidents(args.data) if args.data else None
    report = asyncio.run(evaluate_pipeline(incidents))
    print(f"Total incidents: {report['total']}")
    print(f"Correct RCA:     {report['correct_rca']}")
    print(f"Has runbook:     {report['has_runbook']}")
    print(f"Accuracy:        {report['accuracy']}")
