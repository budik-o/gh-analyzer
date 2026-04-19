"""Tests for GitHub repository contents traversal (HTTP mocked)."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import pytest

from gh_analyzer.github_api import GitHubApiError
from gh_analyzer.github_repo_contents import parse_repo, scan_github_repo


def _ok_json(data: object) -> MagicMock:
    r = MagicMock()
    r.ok = True
    r.status_code = 200
    r.text = ""
    r.json.return_value = data
    return r


def _err(status: int, text: str = "") -> MagicMock:
    r = MagicMock()
    r.ok = False
    r.status_code = status
    r.text = text
    r.headers = {}
    r.json.return_value = {}
    return r


def test_parse_repo_rejects_multiple_slashes() -> None:
    with pytest.raises(ValueError, match="owner/repo"):
        parse_repo("a/b/c")


@patch("gh_analyzer.github_repo_contents.requests.get")
def test_scan_github_repo_recurses_and_scans_files(mock_get: MagicMock) -> None:
    """Root lists a directory and a file; nested file contains a match."""
    readme_b64 = base64.b64encode(b"hello world\n").decode("ascii")
    config_b64 = base64.b64encode(b"api_key = 1\n").decode("ascii")

    responses = [
        _ok_json(
            [
                {"type": "dir", "path": "src"},
                {"type": "file", "path": "README.md"},
            ]
        ),
        _ok_json([{"type": "file", "path": "src/config.py"}]),
        _ok_json(
            {
                "type": "file",
                "path": "src/config.py",
                "encoding": "base64",
                "content": config_b64,
            }
        ),
        _ok_json(
            {
                "type": "file",
                "path": "README.md",
                "encoding": "base64",
                "content": readme_b64,
            }
        ),
    ]
    mock_get.side_effect = responses

    findings = scan_github_repo("o/r")

    assert len(findings) == 1
    assert findings[0]["rule"] == "api_key"
    assert findings[0]["line_number"] == 1
    assert findings[0]["file"] == "o/r:src/config.py"
    assert findings[0]["line"] == "api_key = 1"
    assert mock_get.call_count == 4


@patch("gh_analyzer.github_repo_contents.requests.get")
def test_scan_github_repo_surfaces_rate_limit(mock_get: MagicMock) -> None:
    mock_get.return_value = _err(429, "rate limit")

    with pytest.raises(GitHubApiError, match="rate limit"):
        scan_github_repo("owner/name")
