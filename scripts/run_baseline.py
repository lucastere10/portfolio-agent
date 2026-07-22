#!/usr/bin/env python3
"""A0 baseline runner — smoke golden queries against local portfolio-agent."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from src.evaluation.style_checks import (
    anti_pattern_hits,
    count_list_items,
    detect_response_lang,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = os.environ.get("BASELINE_BASE_URL", "http://127.0.0.1:8000")
DEFAULT_CASES = Path(
    os.environ.get("BASELINE_CASES", str(ROOT / "docs" / "baseline" / "golden-cases.json"))
)
RESULTS_DIR = ROOT / "docs" / "baseline" / "results"


def _load_cases(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "cases" not in data:
        raise SystemExit(f"Invalid cases file: {path}")
    return data


def _check_health(client: httpx.Client, base_url: str) -> dict:
    try:
        res = client.get(f"{base_url.rstrip('/')}/health")
    except httpx.HTTPError as exc:
        raise SystemExit(f"Health check failed: cannot reach {base_url} ({exc})") from exc

    try:
        body = res.json()
    except Exception as exc:
        raise SystemExit(f"Health check returned non-JSON (status={res.status_code})") from exc

    if res.status_code != 200 or body.get("status") != "ok":
        raise SystemExit(
            f"Health not ok (status_code={res.status_code}, body={body}). "
            "Start the agent with LLM credentials before running baseline."
        )
    if not body.get("llm_configured"):
        raise SystemExit("Health ok but llm_configured=false — baseline requires LLM.")
    return body


def _detect_response_lang(text: str) -> str:
    return detect_response_lang(text)


def _count_list_items(text: str) -> int:
    return count_list_items(text)


def _score_case(
    case: dict,
    response: dict,
    *,
    latency_ms: int,
    verbosity_threshold: int,
) -> dict:
    message = response.get("message") or ""
    selected = response.get("selected_project")
    expected = case.get("expected_primary")
    matches = response.get("matches") or []
    match_ids = [m.get("id") for m in matches[:3] if isinstance(m, dict)]

    primary_ok = True if expected is None else selected == expected
    response_len = len(message)
    verbosity_ok = response_len <= verbosity_threshold
    anti_hits = anti_pattern_hits(message)
    list_items = _count_list_items(message)
    # Flag long lists as anti-pattern signal for overview/intro families
    long_list = list_items >= 5 and case.get("family") in {"intro", "overview", "path"}
    anti_pattern_ok = not anti_hits and not long_list

    detected_lang = _detect_response_lang(message)
    expected_lang = case.get("lang")
    lang_ok = detected_lang == expected_lang or detected_lang == "unknown"

    return {
        "case_id": case["id"],
        "family": case.get("family"),
        "lang_expected": expected_lang,
        "lang_detected": detected_lang,
        "lang_ok": lang_ok,
        "message": case["message"],
        "expected_primary": expected,
        "selected_project": selected,
        "selected_type": response.get("selected_type"),
        "primary_ok": primary_ok,
        "match_ids": match_ids,
        "response_len": response_len,
        "verbosity_ok": verbosity_ok,
        "anti_pattern_ok": anti_pattern_ok,
        "anti_pattern_hits": anti_hits,
        "list_items": list_items,
        "tool_used": response.get("tool_used"),
        "latency_ms": latency_ms,
        "session_id": response.get("session_id"),
        "response_preview": message[:240],
        "response_full": message,
        "style_ok": "",
        "invented": "",
        "notes": "",
    }


def _chat(
    client: httpx.Client,
    base_url: str,
    message: str,
    session_id: str | None,
) -> tuple[dict, int]:
    payload: dict = {"message": message}
    if session_id:
        payload["session_id"] = session_id
    t0 = time.monotonic()
    res = client.post(f"{base_url.rstrip('/')}/api/v1/chat", json=payload)
    latency_ms = int((time.monotonic() - t0) * 1000)
    if res.status_code != 200:
        raise RuntimeError(f"chat failed status={res.status_code} body={res.text[:500]}")
    return res.json(), latency_ms


def _ordered_cases(cases: list[dict]) -> list[dict]:
    """Run pay-group in order (#4 then #9); others by id. Preserve relative order."""
    return sorted(cases, key=lambda c: (c["id"]))


def run() -> int:
    cases_doc = _load_cases(DEFAULT_CASES)
    cases = _ordered_cases(cases_doc["cases"])
    threshold = int(cases_doc.get("verbosity_char_threshold", 600))
    base_url = DEFAULT_BASE_URL

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    timeout = httpx.Timeout(120.0, connect=10.0)
    with httpx.Client(timeout=timeout) as client:
        health = _check_health(client, base_url)
        print(f"Health ok: catalog={health.get('catalog_size')} provider={health.get('provider')}")

        session_by_group: dict[str, str] = {}
        results: list[dict] = []

        for case in cases:
            group = case.get("session_group")
            session_id = session_by_group.get(group) if group else None
            print(f"[{case['id']:02d}] {case['message'][:60]}...")
            try:
                body, latency_ms = _chat(client, base_url, case["message"], session_id)
            except Exception as exc:
                results.append(
                    {
                        "case_id": case["id"],
                        "family": case.get("family"),
                        "message": case["message"],
                        "error": str(exc),
                        "primary_ok": False,
                        "verbosity_ok": False,
                        "anti_pattern_ok": False,
                        "lang_ok": False,
                        "style_ok": "",
                        "invented": "",
                        "notes": "request_error",
                    }
                )
                print(f"  ERROR: {exc}")
                continue

            if group and body.get("session_id"):
                session_by_group[group] = body["session_id"]

            scored = _score_case(case, body, latency_ms=latency_ms, verbosity_threshold=threshold)
            results.append(scored)
            status = "OK" if scored["primary_ok"] and scored["verbosity_ok"] else "REVIEW"
            print(
                f"  {status} primary={scored['selected_project']} "
                f"len={scored['response_len']} ms={latency_ms}"
            )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "health": health,
        "verbosity_char_threshold": threshold,
        "results": results,
        "summary": _summarize(results),
    }

    json_path = RESULTS_DIR / "latest.json"
    md_path = RESULTS_DIR / "latest.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(payload), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(json.dumps(payload["summary"], indent=2))
    return 0


def _summarize(results: list[dict]) -> dict:
    n = len(results)
    with_expected = [r for r in results if r.get("expected_primary") is not None and "error" not in r]
    return {
        "total": n,
        "errors": sum(1 for r in results if "error" in r),
        "primary_ok": sum(1 for r in with_expected if r.get("primary_ok")),
        "primary_total": len(with_expected),
        "verbosity_fail": sum(1 for r in results if not r.get("verbosity_ok", True)),
        "anti_pattern_fail": sum(1 for r in results if not r.get("anti_pattern_ok", True)),
        "lang_fail": sum(1 for r in results if not r.get("lang_ok", True)),
    }


def _render_markdown(payload: dict) -> str:
    s = payload["summary"]
    lines = [
        "# Baseline results (A0)",
        "",
        f"- Generated (UTC): `{payload['generated_at']}`",
        f"- Base URL: `{payload['base_url']}`",
        f"- Provider: `{payload.get('health', {}).get('provider')}`",
        f"- Verbosity threshold: `{payload['verbosity_char_threshold']}` chars",
        "",
        "## Summary",
        "",
        f"- Primary ok: **{s['primary_ok']}/{s['primary_total']}**",
        f"- Verbosity fails: **{s['verbosity_fail']}**",
        f"- Anti-pattern fails: **{s['anti_pattern_fail']}**",
        f"- Lang fails: **{s['lang_fail']}**",
        f"- Request errors: **{s['errors']}**",
        "",
        "## Cases",
        "",
        "| ID | Family | Primary OK | Selected | Expected | Len | Verb OK | Anti OK | Lang OK | Latency | style_ok | invented | notes |",
        "|----|--------|------------|----------|----------|-----|---------|---------|---------|---------|----------|----------|-------|",
    ]
    for r in payload["results"]:
        if "error" in r:
            lines.append(
                f"| {r['case_id']} | {r.get('family')} | ERR | — | — | — | — | — | — | — | | | `{r.get('error', '')[:40]}` |"
            )
            continue
        lines.append(
            "| {case_id} | {family} | {primary_ok} | `{selected}` | `{expected}` | {length} | {verbosity_ok} | "
            "{anti_ok} | {lang_ok} | {latency}ms | {style} | {invented} | {notes} |".format(
                case_id=r["case_id"],
                family=r.get("family"),
                primary_ok="Y" if r.get("primary_ok") else "N",
                selected=r.get("selected_project") or "—",
                expected=r.get("expected_primary") or "—",
                length=r.get("response_len"),
                verbosity_ok="Y" if r.get("verbosity_ok") else "N",
                anti_ok="Y" if r.get("anti_pattern_ok") else "N",
                lang_ok="Y" if r.get("lang_ok") else "N",
                latency=r.get("latency_ms"),
                style=r.get("style_ok") or "",
                invented=r.get("invented") or "",
                notes=r.get("notes") or "",
            )
        )

    lines.extend(["", "## Response previews", ""])
    for r in payload["results"]:
        if "error" in r:
            lines.append(f"### Case {r['case_id']} — ERROR\n\n```\n{r.get('error')}\n```\n")
            continue
        lines.append(f"### Case {r['case_id']} — {r.get('message')}")
        lines.append("")
        lines.append(f"- matches: `{r.get('match_ids')}`")
        lines.append(f"- tool_used: `{r.get('tool_used')}`")
        lines.append("")
        lines.append("```")
        lines.append(r.get("response_full") or r.get("response_preview") or "")
        lines.append("```")
        lines.append("")

    lines.extend(
        [
            "## Human review",
            "",
            "Preencha `style_ok` / `invented` / `notes` em [`../issues.md`](../issues.md) "
            "após ler os previews. Não altere instruction/KB para ‘passar’ neste baseline.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        raise SystemExit(130)
