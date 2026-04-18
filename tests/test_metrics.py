"""Unit tests for gh_analyzer.metrics.compute_pr_metrics"""

import pytest

from gh_analyzer.metrics import compute_pr_metrics


def test_compute_pr_metrics_mixed_prs() -> None:
    prs = [
        {
            "created_at": "2020-01-01T00:00:00Z",
            "merged_at": "2020-01-02T00:00:00Z",
            "state": "closed",
        },
        {
            "created_at": "2020-01-03T00:00:00Z",
            "merged_at": None,
            "state": "open",
        },
        {
            "created_at": "2020-01-01T00:00:00Z",
            "merged_at": "2020-01-04T00:00:00Z",
            "state": "closed",
        },
    ]

    result = compute_pr_metrics(prs)

    assert result["total_pr_count"] == 3
    assert result["merged_pr_count"] == 2
    assert result["average_cycle_time_seconds"] == pytest.approx(172800.0)


def test_compute_pr_metrics_no_merged_prs() -> None:
    prs = [
        {
            "created_at": "2020-01-01T00:00:00Z",
            "merged_at": None,
            "state": "open",
        },
        {
            "created_at": "2020-01-02T00:00:00Z",
            "merged_at": None,
            "state": "closed",
        },
    ]

    result = compute_pr_metrics(prs)

    assert result["total_pr_count"] == 2
    assert result["merged_pr_count"] == 0
    assert result["average_cycle_time_seconds"] is None


def test_compute_pr_metrics_empty_input() -> None:
    result = compute_pr_metrics([])

    assert result["total_pr_count"] == 0
    assert result["merged_pr_count"] == 0
    assert result["average_cycle_time_seconds"] is None


def test_compute_pr_metrics_single_merged_pr() -> None:
    prs = [
        {
            "created_at": "2020-01-01T00:00:00Z",
            "merged_at": "2020-01-01T12:00:00Z",
            "state": "closed",
        }
    ]

    result = compute_pr_metrics(prs)

    assert result["total_pr_count"] == 1
    assert result["merged_pr_count"] == 1
    assert result["average_cycle_time_seconds"] == pytest.approx(43200.0)

def test_invalid_datetime_raises() -> None:
    prs = [
        {
            "created_at": "invalid",
            "merged_at": "2020-01-01T12:00:00Z",
            "state": "closed",
        }
    ]

    with pytest.raises(ValueError):
        compute_pr_metrics(prs)