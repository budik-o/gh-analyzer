"""Unit tests for gh_analyzer.security_scanner."""

from __future__ import annotations

from pathlib import Path

from gh_analyzer.security_scanner import scan_path


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
