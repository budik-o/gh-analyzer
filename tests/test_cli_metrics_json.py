"""Tests for metrics --json CLI output."""

from __future__ import annotations

import contextlib
import json
import sys
from io import StringIO
from unittest.mock import patch

import pytest

from gh_analyzer.cli import main


def _run(argv: list[str]) -> tuple[int, str]:
    old_argv = sys.argv[:]
    sys.argv = ["gh-analyzer", *argv]
    buf = StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            code = main()
    finally:
        sys.argv = old_argv
    return code, buf.getvalue()


@patch("gh_analyzer.cli.fetch_pull_requests")
def test_metrics_json_matches_compute_pr_metrics_shape(
    mock_fetch: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    prs = [
        {
            "created_at": "2020-01-01T00:00:00Z",
            "merged_at": "2020-01-02T00:00:00Z",
            "state": "closed",
        },
    ]
    mock_fetch.return_value = prs

    code, out = _run(["metrics", "owner/repo", "--json"])

    assert code == 0
    parsed = json.loads(out)
    assert parsed == {
        "average_cycle_time_seconds": 86400.0,
        "merged_pr_count": 1,
        "total_pr_count": 1,
    }
    assert out == json.dumps(parsed, indent=2, sort_keys=True) + "\n"
