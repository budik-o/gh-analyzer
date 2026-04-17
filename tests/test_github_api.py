"""Unit tests for gh_analyzer.github_api.fetch_pull_requests (HTTP mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from gh_analyzer.github_api import GitHubApiError, fetch_pull_requests

REQUIRED_KEYS = frozenset({"created_at", "merged_at", "state"})


def _http_response(
    *,
    ok: bool = True,
    status_code: int = 200,
    json_data: list | None = None,
    text: str = "",
) -> MagicMock:
    r = MagicMock()
    r.ok = ok
    r.status_code = status_code
    r.text = text
    if json_data is not None:
        r.json.return_value = json_data
    return r


@patch("gh_analyzer.github_api.requests.get")
def test_single_page_two_prs(mock_get: MagicMock) -> None:
    """One GET returns two PRs; output length and fields match _pr_slice."""
    payload = [
        {
            "created_at": "2020-01-01T00:00:00Z",
            "merged_at": "2020-01-02T00:00:00Z",
            "state": "closed",
            "id": 1,
            "title": "extra field",
        },
        {
            "created_at": "2020-01-03T00:00:00Z",
            "merged_at": None,
            "state": "open",
            "number": 2,
        },
    ]
    mock_get.return_value = _http_response(json_data=payload)

    result = fetch_pull_requests("o/r")

    assert len(result) == 2
    for row in result:
        assert set(row.keys()) == REQUIRED_KEYS
    assert result[0] == {
        "created_at": "2020-01-01T00:00:00Z",
        "merged_at": "2020-01-02T00:00:00Z",
        "state": "closed",
    }
    assert result[1] == {
        "created_at": "2020-01-03T00:00:00Z",
        "merged_at": None,
        "state": "open",
    }
    mock_get.assert_called_once()


@patch("gh_analyzer.github_api.requests.get")
def test_pagination_three_pages(mock_get: MagicMock) -> None:
    """Full pages 1–2 (100 items each) then empty page 3; all items merged in order."""
    def side_effect(
        url: str,
        headers: dict | None = None,
        params: dict | None = None,
        timeout: int | None = None,
    ) -> MagicMock:
        assert params is not None
        page = params["page"]
        assert params["state"] == "all"
        assert params["per_page"] == 100
        if page == 1:
            batch = [
                {"created_at": f"2020-p1-{i}", "merged_at": None, "state": "open"}
                for i in range(100)
            ]
            return _http_response(json_data=batch)
        if page == 2:
            batch = [
                {"created_at": f"2020-p2-{i}", "merged_at": None, "state": "open"}
                for i in range(100)
            ]
            return _http_response(json_data=batch)
        if page == 3:
            return _http_response(json_data=[])
        raise AssertionError(f"unexpected page {page}")

    mock_get.side_effect = side_effect

    result = fetch_pull_requests("owner/repo")

    assert len(result) == 200
    assert result[0]["created_at"] == "2020-p1-0"
    assert result[99]["created_at"] == "2020-p1-99"
    assert result[100]["created_at"] == "2020-p2-0"
    assert result[199]["created_at"] == "2020-p2-99"
    assert mock_get.call_count == 3


@patch("gh_analyzer.github_api.requests.get")
def test_merged_at_null(mock_get: MagicMock) -> None:
    """PRs with merged_at null still yield dicts with merged_at None."""
    mock_get.return_value = _http_response(
        json_data=[
            {
                "created_at": "2021-06-01T12:00:00Z",
                "merged_at": None,
                "state": "closed",
            },
        ],
    )

    result = fetch_pull_requests("a/b")

    assert len(result) == 1
    assert result[0]["merged_at"] is None
    assert set(result[0].keys()) == REQUIRED_KEYS


@patch("gh_analyzer.github_api.requests.get")
def test_api_error_raises(mock_get: MagicMock) -> None:
    """Non-success HTTP response raises GitHubApiError."""
    mock_get.return_value = _http_response(
        ok=False,
        status_code=404,
        text="Not Found",
    )

    with pytest.raises(GitHubApiError) as excinfo:
        fetch_pull_requests("missing/repo")

    assert "404" in str(excinfo.value)
    mock_get.assert_called_once()
