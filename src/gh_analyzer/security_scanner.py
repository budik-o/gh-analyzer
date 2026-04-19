"""Minimal security scanner for keyword-based secret detection."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from pathlib import Path

IGNORE_DIRS = {".git", "__pycache__", "venv", ".venv", "node_modules"}
KEYWORD_SECRETS = ("password", "api_key", "token", "secret")


def build_patterns() -> dict[str, re.Pattern[str]]:
    patterns: dict[str, re.Pattern[str]] = {}
    for rule in KEYWORD_SECRETS:
        patterns[rule] = re.compile(rf"\b{re.escape(rule)}\b", re.IGNORECASE)
    return patterns


def list_files(root_path: Path) -> list[Path]:
    files: list[Path] = []
    for current_root, dirs, filenames in os.walk(root_path, topdown=True):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        current_dir = Path(current_root)
        for filename in filenames:
            files.append(current_dir / filename)
    return files


def scan_lines(
    file_label: str,
    lines: Iterable[str],
    patterns: dict[str, re.Pattern[str]],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\n")
        for rule, pattern in patterns.items():
            if pattern.search(line):
                findings.append(
                    {
                        "file": file_label,
                        "line_number": line_number,
                        "rule": rule,
                        "line": line,
                    }
                )
    return findings


def scan_text(
    file_label: str,
    text: str,
    patterns: dict[str, re.Pattern[str]],
) -> list[dict[str, object]]:
    return scan_lines(file_label, text.splitlines(), patterns)


def scan_file(file_path: Path, patterns: dict[str, re.Pattern[str]]) -> list[dict[str, object]]:
    try:
        with file_path.open("r", encoding="utf-8", errors="ignore") as file:
            return scan_lines(str(file_path), file, patterns)
    except OSError as e:
        return [
            {
                "file": str(file_path),
                "line_number": 0,
                "rule": "read_error_rule",
                "line": f"{type(e).__name__}: {e}",
            }
        ]


def scan_path(path: str) -> list[dict[str, object]]:
    root_path = Path(path)
    if not root_path.exists():
        raise ValueError(f"Path does not exist: {path}")

    patterns = build_patterns()

    if root_path.is_file():
        return scan_file(root_path, patterns)

    findings: list[dict[str, object]] = []
    for file_path in list_files(root_path):
        findings.extend(scan_file(file_path, patterns))
    return findings
