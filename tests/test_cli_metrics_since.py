"""Tests for metrics --since / --since-days resolution in cli."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from gh_analyzer.cli import resolve_metrics_since_argument


def test_since_days_computes_cutoff() -> None:
    now = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    since, err = resolve_metrics_since_argument(None, 7, now_utc=now)
    assert err is None
    assert since == "2024-06-08T12:00:00Z"


def test_both_since_and_since_days_errors() -> None:
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    since, err = resolve_metrics_since_argument("2020-01-01T00:00:00Z", 3, now_utc=now)
    assert since is None
    assert err is not None
    assert "only one" in err.lower()


@pytest.mark.parametrize("bad_days", [0, -1, -100])
def test_non_positive_since_days_errors(bad_days: int) -> None:
    since, err = resolve_metrics_since_argument(None, bad_days, now_utc=datetime.now(timezone.utc))
    assert since is None
    assert err is not None
    assert "positive" in err.lower()


def test_explicit_since_only() -> None:
    since, err = resolve_metrics_since_argument("2021-05-01T00:00:00Z", None)
    assert err is None
    assert since == "2021-05-01T00:00:00Z"


def test_neither_window() -> None:
    since, err = resolve_metrics_since_argument(None, None)
    assert err is None
    assert since is None
