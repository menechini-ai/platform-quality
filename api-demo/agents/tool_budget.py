"""Tool-usage budget enforcement for MCP tool calls.

Tracks call count within a sliding time window and rejects calls when
the budget is exhausted.
"""

from __future__ import annotations

import time


class ToolBudget:
    """Sliding-window rate limiter for tool invocations.

    Args:
        max_calls: Maximum calls allowed within *window_seconds*.
        window_seconds: Width of the sliding window in seconds.
            ``0`` means no limit (``allow_call()`` always returns True).
    """

    def __init__(self, max_calls: int = 10, window_seconds: int = 60) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._timestamps: list[float] = []

    def allow_call(self) -> bool:
        """Check whether a new call is allowed.

        If allowed, records the call and returns True.
        If the budget is exhausted, returns False (does NOT record).
        """
        if self.window_seconds <= 0:
            return True

        now = time.time()
        cutoff = now - self.window_seconds
        self._timestamps = [t for t in self._timestamps if t > cutoff]

        if len(self._timestamps) >= self.max_calls:
            return False

        self._timestamps.append(now)
        return True

    def reset(self) -> None:
        """Clear all recorded timestamps."""
        self._timestamps.clear()


if __name__ == "__main__":
    import argparse
    import time

    parser = argparse.ArgumentParser(description="Tool budget demo")
    parser.add_argument("--max", type=int, default=5, help="Max calls per window")
    parser.add_argument("--window", type=int, default=10, help="Window in seconds")
    args = parser.parse_args()

    budget = ToolBudget(max_calls=args.max, window_seconds=args.window)
    print(f"ToolBudget: max={args.max}, window={args.window}s")

    for i in range(args.max + 2):
        ok = budget.allow_call()
        print(f"  Call {i+1}: {'ALLOWED' if ok else 'REJECTED'}")
        time.sleep(0.05)
