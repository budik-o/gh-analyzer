"""Mocked tests for GitHub API HTTP error mapping (no real network)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from gh_analyzer.github_api import GitHubApiError, fetch_pull_requests


def _http_response(
    *,
    ok: bool = True,
    status_code: int = 200,
    json_data: list | None = None,
    text: str = "",
    headers: dict[str, str] | None = None,
) -> MagicMock:
    r = MagicMock()
    r.ok = ok
    r.status_code = status_code
    r.text = text
    r.headers = headers or {}
    if json_data is not None:
        r.json.return_value = json_data
    return r


@patch("gh_analyzer.github_api.requests.get")
def test_401_raises_clear_auth_message(mock_get: MagicMock) -> None:
    mock_get.return_value = _http_response(ok=False, status_code=401, text="Bad credentials")

    with pytest.raises(GitHubApiError) as excinfo:
        fetch_pull_requests("o/r")

    assert "401" in str(excinfo.value)
    assert "GITHUB_TOKEN" in str(excinfo.value)


@patch("gh_analyzer.github_api.requests.get")
def test_404_raises_clear_not_found_message(mock_get: MagicMock) -> None:
    mock_get.return_value = _http_response(ok=False, status_code=404, text="Not Found")

    with pytest.raises(GitHubApiError) as excinfo:
        fetch_pull_requests("ghost/missing")

    assert "404" in str(excinfo.value)
    assert "owner/repo" in str(excinfo.value).lower() or "Repository" in str(excinfo.value)


@patch("gh_analyzer.github_api.requests.get")
def test_429_raises_rate_limit_message(mock_get: MagicMock) -> None:
    mock_get.return_value = _http_response(ok=False, status_code=429, text="Too Many Requests")

    with pytest.raises(GitHubApiError) as excinfo:
        fetch_pull_requests("o/r")

    assert "429" in str(excinfo.value)
    assert "rate limit" in str(excinfo.value).lower()


@patch("gh_analyzer.github_api.requests.get")
def test_403_with_zero_remaining_raises_rate_limit_message(mock_get: MagicMock) -> None:
    mock_get.return_value = _http_response(
        ok=False,
        status_code=403,
        text="API rate limit exceeded",
        headers={"X-RateLimit-Remaining": "0"},
    )

    with pytest.raises(GitHubApiError) as excinfo:
        fetch_pull_requests("o/r")

    assert "rate limit" in str(excinfo.value).lower()


@patch("gh_analyzer.github_api.requests.get")
def test_since_filters_by_created_at(mock_get: MagicMock) -> None:
    payload = [
        {
            "created_at": "2019-12-31T00:00:00Z",
            "merged_at": None,
            "state": "closed",
        },
        {
            "created_at": "2020-06-01T00:00:00Z",
            "merged_at": "2020-06-02T00:00:00Z",
            "state": "closed",
        },
    ]
    mock_get.return_value = _http_response(json_data=payload)

    result = fetch_pull_requests("o/r", since="2020-01-01T00:00:00Z")

    assert len(result) == 1
    assert result[0]["created_at"] == "2020-06-01T00:00:00Z"


def test_invalid_since_raises_value_error() -> None:
    with pytest.raises(ValueError) as excinfo:
        fetch_pull_requests("o/r", since="not-a-date")

    assert "since" in str(excinfo.value).lower() or "ISO" in str(excinfo.value)
