"""Tests for scan command (local vs remote dispatch)."""

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


@patch("gh_analyzer.cli.scan_github_repo")
def test_scan_remote_owner_repo(mock_scan: object, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    mock_scan.return_value = [{"file": "o/r:a", "line_number": 1, "rule": "token", "line": "x"}]
    code, out = _run(["scan", "o/r"])
    assert code == 1
    mock_scan.assert_called_once_with("o/r")
    payload = json.loads(out)
    assert len(payload) == 1


def test_scan_remote_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    code, out = _run(["scan", "nobody/nothing"])
    assert code == 2
    assert "GITHUB_TOKEN" in out
