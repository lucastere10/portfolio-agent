#!/usr/bin/env python3
"""A4/A5 retrieval smoke — thin wrapper over the same checks as tests/test_search.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    # Prefer pytest gate when available; fall back to inline asserts.
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_search.py", "-q"],
            cwd=ROOT,
            check=False,
        )
        return int(result.returncode)
    except OSError:
        pass

    sys.path.insert(0, str(ROOT))
    from src.tools.search import search_projects  # noqa: E402

    queries = [
        ("Como você resolveu cold start no Cloud Run?", "ai-agents-adk"),
        ("cold start Cloud Run", "ai-agents-adk"),
    ]
    failed = 0
    for query, expected in queries:
        matches = search_projects(query, limit=5)
        got = matches[0].id if matches else None
        if got != expected:
            print(f"FAIL  expected={expected}  got={got}  | {query}")
            failed += 1
        else:
            print(f"OK    {expected}  | {query}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
