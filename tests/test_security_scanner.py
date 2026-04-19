"""Unit tests for gh_analyzer.security_scanner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from gh_analyzer.security_scanner import build_patterns, scan_file, scan_path, scan_text


def test_detects_password_keyword(tmp_path: Path) -> None:
    """A line with a standalone password assignment is reported with rule, line, and file."""
    target = tmp_path / "config.txt"
    target.write_text('password = "123"\n', encoding="utf-8")

    findings = scan_path(str(tmp_path))

    assert len(findings) == 1
    row = findings[0]
    assert row["rule"] == "password"
    assert row["line_number"] == 1
    assert Path(row["file"]) == target
    assert row["line"] == 'password = "123"'


def test_api_key_case_insensitive(tmp_path: Path) -> None:
    """Uppercase API_KEY still matches the api_key rule (IGNORECASE patterns)."""
    target = tmp_path / "env.txt"
    target.write_text("API_KEY = 'abc'\n", encoding="utf-8")

    findings = scan_path(str(tmp_path))

    assert len(findings) == 1
    assert findings[0]["rule"] == "api_key"
    assert findings[0]["line_number"] == 1


def test_skips_ignored_directories(tmp_path: Path) -> None:
    """Files under .git and venv are never opened; only normal_dir is eligible."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "venv").mkdir()
    normal = tmp_path / "normal_dir"
    normal.mkdir()

    (tmp_path / ".git" / "leak.txt").write_text('password = "nope"\n', encoding="utf-8")
    (tmp_path / "venv" / "leak.txt").write_text('password = "nope"\n', encoding="utf-8")
    (normal / "clean.txt").write_text("nothing suspicious\n", encoding="utf-8")

    findings = scan_path(str(tmp_path))

    assert findings == []


def test_multiple_findings_on_separate_lines(tmp_path: Path) -> None:
    """Each matching line produces a separate finding for the correct rule."""
    target = tmp_path / "multi.txt"
    target.write_text(
        'password = "123"\n'
        'token = "abc"\n',
        encoding="utf-8",
    )

    findings = scan_path(str(tmp_path))

    assert len(findings) == 2
    assert findings[0]["rule"] == "password"
    assert findings[0]["line_number"] == 1
    assert findings[1]["rule"] == "token"
    assert findings[1]["line_number"] == 2


def test_scan_path_accepts_single_file(tmp_path: Path) -> None:
    """A direct file path is scanned without requiring directory walk."""
    target = tmp_path / "single.txt"
    target.write_text('secret = "x"\n', encoding="utf-8")

    findings = scan_path(str(target))

    assert len(findings) == 1
    assert findings[0]["rule"] == "secret"
    assert Path(findings[0]["file"]) == target


def test_scan_text_matches_scan_file(tmp_path: Path) -> None:
    """scan_text uses the same rules as scan_file for an equivalent body."""
    target = tmp_path / "x.txt"
    target.write_text("token = 9\n", encoding="utf-8")
    patterns = build_patterns()
    a = scan_file(target, patterns)
    b = scan_text("virtual", "token = 9\n", patterns)
    assert len(a) == 1 and len(b) == 1
    assert a[0]["rule"] == b[0]["rule"] == "token"
    assert a[0]["line_number"] == b[0]["line_number"] == 1
    assert a[0]["line"] == b[0]["line"]
    assert Path(a[0]["file"]) == target
    assert b[0]["file"] == "virtual"


def test_scan_file_records_read_error(tmp_path: Path) -> None:
    """Unreadable files produce a ``read_error`` finding instead of failing silently."""
    target = tmp_path / "locked.txt"
    target.write_text("password = x\n", encoding="utf-8")
    patterns = build_patterns()

    with patch("gh_analyzer.security_scanner.Path.open", side_effect=PermissionError("denied")):
        rows = scan_file(target, patterns)

    assert len(rows) == 1
    assert rows[0]["rule"] == "read_error_rule"
    assert rows[0]["line_number"] == 0
    assert "PermissionError" in str(rows[0]["line"])
    assert str(target) == rows[0]["file"]


def test_scan_path_missing_path_raises_value_error(tmp_path: Path) -> None:
    """Missing input path fails fast with ValueError."""
    missing = tmp_path / "does_not_exist"

    with pytest.raises(ValueError) as excinfo:
        scan_path(str(missing))

    assert "Path does not exist" in str(excinfo.value)
