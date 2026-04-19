# gh-analyzer

Small Python CLI for **scanning repositories for potential secrets** and **analyzing pull request activity** via the GitHub API, designed to run in typical Unix/Linux environments and CI pipelines.

Built with a focus on **security, automation, and developer productivity**, the tool integrates well into **CI/CD pipelines**, produces **machine-readable outputs (JSON)**, and follows common engineering practices such as **testing, containerization (Docker), and Git-based workflows**.

## Motivation

This project was built to explore **software supply chain security** and **developer productivity metrics** using the GitHub API, with a focus on building tools that can be integrated into automated CI/CD workflows

## Key Features

- **CLI**: `argparse` subcommands (`scan`, `metrics`), stable exit codes for automation (`scan`: 0 clean, 1 findings, 2 configuration/API error; `metrics`: 2 on errors).
- **GitHub REST**: Bearer `GITHUB_TOKEN`; pulls list with pagination and optional `created_at` window (`--since` / `--since-days`); remote scan via Contents API with recursive tree walk.
- **CI/CD**: Scheduled and `workflow_dispatch` GitHub Actions workflows with configurable inputs. JSON output is written to disk and uploaded as workflow artifacts.
- **JSON**: `scan` always prints a JSON array; `metrics --json` prints sorted keys for automation and downstream processing.
- **Docker**: Slim Python image, package installed in-container, `ENTRYPOINT` set to `gh-analyzer`.
- **Tests**: `pytest` suite with mocked HTTP (no live API in tests) covering CLI dispatch, API client behavior, pagination/`since` early-stop, metrics math, and scanner rules.

## Example Usage

```bash
# Local tree or single file
gh-analyzer scan ./my-service
gh-analyzer scan ./src/config.yaml

# Remote repository (exactly one slash: owner/repo); requires GITHUB_TOKEN
export GITHUB_TOKEN=ghp_...
gh-analyzer scan kubernetes/kubernetes

# Metrics: human-readable summary
gh-analyzer metrics github/scientist

# Metrics: time window and machine-readable output
gh-analyzer metrics github/scientist --since 2024-01-01T00:00:00Z --json
gh-analyzer metrics github/scientist --since-days 30 --json

# Module invocation (no install)
python -m gh_analyzer scan .
python -m gh_analyzer metrics owner/repo --json
```

## Example Output

**`scan`** (array of findings; empty array `[]` when nothing matched):

```json
[
  {
    "file": "budik-o/gh-analyzer-demo-repo:server_log.txt",
    "line_number": 24,
    "rule": "api_key",
    "line": "[2026-04-19 08:14:12] DEBUG: Using API_KEY: sk_test_4eC39HqLyjWDarjtT1zdp7dc"
  }
]
```

**`metrics`**:

```text
Total PRs: 128
Merged PRs: 88
Avg cycle time (hours): 1481.45
```

**`metrics --json`**:

```json
{
  "average_cycle_time_seconds": 5333221.454545454,
  "merged_pr_count": 88,
  "total_pr_count": 128
}
```

When no merged PRs fall in the fetched set, `average_cycle_time_seconds` is JSON `null`.

## Architecture Overview

| Layer | Role |
|--------|------|
| **CLI** (`cli.py`) | Parses arguments, routes `scan` vs `metrics`, resolves `--since` / `--since-days`, prints JSON or short text, returns exit codes. |
| **GitHub client** (`github_client.py`) | Shared base URL, `Authorization: Bearer`, and HTTP error mapping (401/404/403/429) into `GitHubApiError`. |
| **GitHub API** (`github_api.py`) | Fetches PR pages from `/repos/{owner}/{repo}/pulls`, optional client-side `created_at` filter with pagination short-circuit when sorted `created` `desc`. |
| **Remote scan** (`github_repo_contents.py`) | Walks `/contents` recursively and scans for preset patterns.
| **Scanner** (`security_scanner.py`) | Applies simple keyword regex rules, ignores selected directories, and reads UTF-8 with replacement on decode errors. |
| **Metrics** (`metrics.py`) | Derives counts and mean cycle time (merged PRs only) from PR records (`created_at`, `merged_at`, `state`). |

## Project Structure

```
.
├── pyproject.toml          # package metadata, console script gh-analyzer
├── Dockerfile              # Python 3.12 slim, pip install .
├── .dockerignore
├── README.md
├── src/gh_analyzer/
│   ├── __main__.py         # python -m gh_analyzer
│   ├── cli.py              # entrypoint and argument parsing
│   ├── github_client.py    # auth + error handling
│   ├── github_api.py       # pull requests client
│   ├── github_repo_contents.py  # contents API + remote scan
│   ├── security_scanner.py # scan for keywords
│   ├── metrics.py          # metric computation
│   └── iso_datetime.py     # GitHub-style ISO timestamps
├── .github/workflows/
│   ├── metrics.yml         # scheduled + manual metrics → metrics.json artifact
│   └── scan.yml            # scheduled + manual scan → scan.json artifact
└── tests/                  # pytest;
```

## GitHub Actions Integration

- **Metrics** (`.github/workflows/metrics.yml`): Daily at 06:00 UTC; manual run with optional `repo`, `since`, and `since_days` inputs (workflow rejects both time filters together). Default repository when inputs are empty is `github/scientist`. Runs `gh-analyzer metrics … --json > metrics.json` and uploads `metrics` artifact.
- **Scan** (`.github/workflows/scan.yml`): Daily at 07:00 UTC; manual run with optional `repo`. Default when empty is `budik-o/gh-analyzer-demo-repo`. Writes `scan.json` and uploads `scan` artifact even on non-zero scan exit.
- Both workflows use `GITHUB_TOKEN` from the executing repository; target repos must be readable by that token (typically public repos).

## Docker Usage

```bash
docker build -t gh-analyzer .

# Default shows --help
docker run --rm gh-analyzer

docker run --rm -v "${PWD}:/repo:ro" gh-analyzer scan /repo

docker run --rm -e GITHUB_TOKEN gh-analyzer scan owner/public-repo
docker run --rm -e GITHUB_TOKEN gh-analyzer metrics owner/repo --since-days 7 --json
```

## Scope, trade-offs, and next steps

This project is intentionally small: **regex keyword matching** (high false positive and false negative rate, not a substitute for dedicated secret scanner), **a few PR aggregates** over the REST API, **no database** (each run is self-contained), and **synchronous** I/O. Optional time windows use **client-side** filtering on paginated pulls because the API has no `since` parameter. **Remote scans** walk the Contents API file-by-file, so big public repos are slow and rate-limit sensitive. Merge timestamp edge cases are not deeply modeled.

Reasonable extensions if the project grows: configurable rules or allowlists, bounded concurrency with backoff, richer metrics, and tighter file-type filters for remote scans.

## Quick Start

```bash
git clone <repository-url>
cd gh-analyzer
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install ".[dev]"

export GITHUB_TOKEN=<personal_access_token>   # Windows PowerShell: $env:GITHUB_TOKEN="..."

pytest -q
gh-analyzer scan .
gh-analyzer metrics owner/repo --json
```

Requires **Python 3.10+**; Docker image uses **Python 3.12**.
