"""Utility: human time range → epoch, parse helpers."""

from __future__ import annotations

from datetime import UTC, datetime

_UNITS = {
    "h": 3600,
    "d": 86400,
    "m": 60,
    "s": 1,
}


def parse_time(range_str: str) -> int:
    """Parse '1h', '30m', '7d' → unix epoch seconds (relative to now)."""
    now = int(datetime.now(UTC).timestamp())
    if not range_str:
        return now - 3600
    try:
        unit = range_str[-1]
        value = int(range_str[:-1])
        multiplier = _UNITS.get(unit, 3600)
        return now - value * multiplier
    except (ValueError, IndexError):
        return now - 3600
