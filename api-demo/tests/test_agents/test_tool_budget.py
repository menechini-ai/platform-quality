"""Tests for agents.tool_budget — sliding-window rate limiter."""

from __future__ import annotations

from unittest.mock import patch

from agents.tool_budget import ToolBudget


class TestToolBudget:
    def test_allows_up_to_max_calls(self) -> None:
        budget = ToolBudget(max_calls=3, window_seconds=60)
        assert budget.allow_call() is True
        assert budget.allow_call() is True
        assert budget.allow_call() is True

    def test_rejects_n_plus_one(self) -> None:
        budget = ToolBudget(max_calls=2, window_seconds=60)
        assert budget.allow_call() is True
        assert budget.allow_call() is True
        assert budget.allow_call() is False

    def test_resets_after_window(self) -> None:
        budget = ToolBudget(max_calls=1, window_seconds=10)

        with patch("time.time", side_effect=[100.0, 100.0, 115.0]):
            assert budget.allow_call() is True
            assert budget.allow_call() is False  # still within window
            assert budget.allow_call() is True  # outside window

    def test_reset_clears_timestamps(self) -> None:
        budget = ToolBudget(max_calls=1, window_seconds=60)
        budget.allow_call()
        budget.reset()
        assert budget.allow_call() is True

    def test_window_zero_means_no_limit(self) -> None:
        budget = ToolBudget(max_calls=5, window_seconds=0)
        for _ in range(100):
            assert budget.allow_call() is True
