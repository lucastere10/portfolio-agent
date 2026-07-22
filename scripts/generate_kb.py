#!/usr/bin/env python3
"""Generate portfolio-agent KB JSON from portfolio/content (A1)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "src" / "knowledge_base" / "data"
DEFAULT_CONTENT = ROOT.parent / "portfolio" / "content"

# Allow running without installing the package editable.
sys.path.insert(0, str(ROOT))

from src.domain.models import KBEntry  # noqa: E402

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def _slugify_token(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r"[^a-z0-9]+", "-", t)
    return t.strip("-")


def _parse_frontmatter(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    m = _FM_RE.match(raw)
    if not m:
        raise ValueError(f"No frontmatter in {path}")
    try:
        import yaml  # type: ignore
    except ImportError:
        yaml = None

    body = m.group(1)
    if yaml is not None:
        data = yaml.safe_load(body)
        if not isinstance(data, dict):
            raise ValueError(f"Frontmatter is not a mapping: {path}")
        return data

    # Minimal fallback without PyYAML (flat scalars / simple lists only).
    return _parse_frontmatter_minimal(body, path)


def _parse_frontmatter_minimal(body: str, path: Path) -> dict[str, Any]:
    """Best-effort YAML-ish parser for our MDX frontmatter shapes."""
    try:
        import yaml  # noqa: F401
    except ImportError:
        pass

    # Prefer installing PyYAML — fail clearly if complex structures needed.
    raise SystemExit(
        f"PyYAML is required to parse {path}. "
        "Install with: uv pip install pyyaml  (or pip install pyyaml)"
    )


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_existing_by_id() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for name in ("projects.json", "personal_projects.json", "labs.json"):
        raw = _load_json(DATA_DIR / name)
        if not isinstance(raw, list):
            continue
        for item in raw:
            if isinstance(item, dict) and "id" in item:
                out[item["id"]] = item
    return out


def _read_meta(dir_path: Path) -> dict[str, Any]:
    meta_path = dir_path / "meta.json"
    data = _load_json(meta_path)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid meta.json: {meta_path}")
    return data


def _read_locale(dir_path: Path, locale: str = "en") -> dict[str, Any]:
    path = dir_path / f"{locale}.mdx"
    if not path.exists():
        raise FileNotFoundError(path)
    return _parse_frontmatter(path)


def _require_dual_locale(dir_path: Path) -> None:
    for loc in ("en.mdx", "pt-BR.mdx"):
        if not (dir_path / loc).exists():
            raise FileNotFoundError(f"Missing {dir_path / loc}")


def _tags_from_techs(entry_id: str, domain: str, technologies: list[str]) -> list[str]:
    tags: set[str] = set()
    tags.add(_slugify_token(entry_id))
    for part in re.split(r"[\s/&]+", domain):
        s = _slugify_token(part)
        if s:
            tags.add(s)
    for tech in technologies:
        s = _slugify_token(tech)
        if s:
            tags.add(s)
            # also short token without version numbers
            base = re.sub(r"-\d.*$", "", s)
            if base:
                tags.add(base)
    return sorted(tags)


def _related(
    entry_id: str,
    existing: dict[str, dict[str, Any]],
    all_ids: set[str],
    *,
    domain: str,
    tags: list[str],
    catalog: list[KBEntry] | None = None,
) -> list[str]:
    prev = existing.get(entry_id, {}).get("related_projects") or []
    kept = [r for r in prev if r in all_ids and r != entry_id]
    if kept:
        return kept[:5]
    # Fallback: overlap by domain/tags among catalog being built
    if not catalog:
        return []
    tag_set = set(tags)
    scored: list[tuple[int, str]] = []
    for other in catalog:
        if other.id == entry_id:
            continue
        score = 0
        if other.domain == domain:
            score += 2
        score += len(tag_set & set(other.tags))
        if score:
            scored.append((score, other.id))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [i for _, i in scored[:3]]


def _metrics(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for m in raw:
        if isinstance(m, dict) and "label" in m and "value" in m:
            out.append({"label": str(m["label"]), "value": str(m["value"])})
    return out


def _decisions(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for d in raw:
        if isinstance(d, dict) and d.get("title") and d.get("reasoning"):
            out.append({"title": str(d["title"]), "reasoning": str(d["reasoning"])})
    return out


def _difficulty(entry_id: str, existing: dict[str, dict[str, Any]]) -> str:
    d = existing.get(entry_id, {}).get("difficulty", "intermediate")
    if d in ("beginner", "intermediate", "advanced"):
        return d
    return "intermediate"


def build_work(
    content_dir: Path,
    existing: dict[str, dict[str, Any]],
) -> list[KBEntry]:
    work_root = content_dir / "work"
    entries: list[KBEntry] = []
    for slug_dir in sorted(p for p in work_root.iterdir() if p.is_dir()):
        _require_dual_locale(slug_dir)
        meta = _read_meta(slug_dir)
        en = _read_locale(slug_dir, "en")
        slug = meta["slug"]
        assert slug == slug_dir.name, f"slug mismatch {slug} vs {slug_dir.name}"
        techs = list(meta.get("stack") or [])
        tags = _tags_from_techs(slug, meta["domain"], techs)
        demonstrates = [d["title"] for d in _decisions(en.get("decisions"))][:6]
        if not demonstrates:
            demonstrates = techs[:5]
        entries.append(
            KBEntry(
                id=slug,
                type="project",
                title=str(en["name"]),
                domain=str(meta["domain"]),
                summary=str(en["impact"]),
                slug=f"/work/{slug}",
                technologies=techs,
                tags=tags,
                categories=[str(meta["domain"])],
                difficulty=_difficulty(slug, existing),  # type: ignore[arg-type]
                featured=bool(meta.get("featured", False)),
                related_projects=[],  # filled in second pass
                tagline=str(en.get("tagline") or ""),
                context=str(en.get("context") or ""),
                challenges=[str(c) for c in (en.get("challenges") or [])],
                learnings=[str(c) for c in (en.get("learnings") or [])],
                metrics=_metrics(en.get("metrics")),  # type: ignore[arg-type]
                demonstrates=demonstrates,
                decisions=_decisions(en.get("decisions")),  # type: ignore[arg-type]
                tradeoffs=str(en.get("tradeoffs") or ""),
                implementation=str(en.get("implementation") or ""),
                narrative=[],
            )
        )
    return entries


def build_personal(
    content_dir: Path,
    existing: dict[str, dict[str, Any]],
) -> list[KBEntry]:
    root = content_dir / "projects"
    entries: list[KBEntry] = []
    for slug_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        _require_dual_locale(slug_dir)
        meta = _read_meta(slug_dir)
        en = _read_locale(slug_dir, "en")
        slug = meta["slug"]
        assert slug == slug_dir.name
        techs = list(meta.get("stack") or [])
        tags = _tags_from_techs(slug, meta["domain"], techs)
        overview = str(en.get("overview") or "")
        links = meta.get("links") or {}
        highlights = [str(h) for h in (en.get("highlights") or [])]
        features = [str(f) for f in (en.get("features") or [])]
        learnings = [str(x) for x in (en.get("learnings") or [])]
        entries.append(
            KBEntry(
                id=slug,
                type="personal_project",
                title=str(en["name"]),
                domain=str(meta["domain"]),
                summary=overview,
                slug=f"/projects/{slug}",
                technologies=techs,
                tags=tags,
                categories=[str(meta["domain"]), "Personal Projects"],
                difficulty=_difficulty(slug, existing),  # type: ignore[arg-type]
                featured=bool(meta.get("featured", False)),
                related_projects=[],
                tagline=str(en.get("tagline") or ""),
                context=overview,
                challenges=highlights,
                learnings=learnings,
                metrics=_metrics(en.get("metrics")),  # type: ignore[arg-type]
                demonstrates=features[:8],
                decisions=[],
                tradeoffs="",
                implementation=str(en.get("technicalNotes") or ""),
                narrative=[],
                demo_url=str(links.get("demo") or ""),
                github_url=str(links.get("github") or ""),
                repo_url=str(links.get("repo") or ""),
            )
        )
    return entries


def build_labs(
    content_dir: Path,
    existing: dict[str, dict[str, Any]],
) -> list[KBEntry]:
    root = content_dir / "labs"
    entries: list[KBEntry] = []
    for slug_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        _require_dual_locale(slug_dir)
        meta = _read_meta(slug_dir)
        en = _read_locale(slug_dir, "en")
        slug = meta["slug"]
        assert slug == slug_dir.name
        tags = [str(t).lower() for t in (meta.get("tags") or [])]
        narrative_raw = en.get("narrative") or []
        narrative = [str(n) for n in narrative_raw]
        techs = list(existing.get(slug, {}).get("technologies") or [])
        if not techs:
            techs = [t.replace("-", " ").title() for t in tags[:4]]
        entries.append(
            KBEntry(
                id=slug,
                type="lab",
                title=str(en["title"]),
                domain=str(meta["domain"]),
                summary=str(en["summary"]),
                slug=f"/labs/{slug}",
                technologies=techs,
                tags=sorted(set(tags)),
                categories=[str(meta["domain"])],
                difficulty=_difficulty(slug, existing),  # type: ignore[arg-type]
                featured=False,
                related_projects=[],
                tagline=str(en.get("summary") or "")[:120],
                context="",
                challenges=[],
                learnings=[],
                metrics=[],
                demonstrates=[str(d) for d in (en.get("demonstrates") or [])],
                decisions=[],
                tradeoffs="",
                implementation="",
                narrative=narrative,
                interaction_prompt=str(en.get("interactionPrompt") or ""),
            )
        )
    return entries


def build_profile(content_dir: Path) -> dict[str, Any]:
    about_dir = content_dir / "pages" / "about"
    en = _parse_frontmatter(about_dir / "en.mdx")
    pt = _parse_frontmatter(about_dir / "pt-BR.mdx")
    existing = _load_json(DATA_DIR / "profile.json") or {}
    if not isinstance(existing, dict):
        existing = {}
    focus = en.get("focusAreas") or []
    specialties = []
    for f in focus:
        if isinstance(f, dict) and f.get("title"):
            specialties.append(str(f["title"]))
    intro_en = en.get("intro") or []
    about_en = (
        " ".join(str(p) for p in intro_en) if isinstance(intro_en, list) else str(intro_en)
    )
    intro_pt = pt.get("intro") or []
    about_pt = (
        " ".join(str(p) for p in intro_pt) if isinstance(intro_pt, list) else str(intro_pt)
    )
    return {
        "name": str(en.get("title") or existing.get("name") or "Lucas Caldas"),
        "headline": existing.get(
            "headline",
            "Software engineer focused on backend, applied AI, cloud architecture, and MLOps.",
        ),
        "about_en": about_en or existing.get("about_en", ""),
        "about_pt": about_pt or existing.get("about_pt", ""),
        "specialties": specialties or existing.get("specialties", []),
        "availability": existing.get(
            "availability", "Available for engineering and architecture roles."
        ),
        "links": existing.get(
            "links",
            {
                "about": "/about",
                "work": "/work",
                "contact": "/contact",
                "linkedin": "https://linkedin.com/in/lucas-caldas50",
                "github": "https://github.com/lucastere10",
                "email": "lucastere10@gmail.com",
            },
        ),
    }


def build_skills(entries: list[KBEntry]) -> dict[str, Any]:
    techs: list[str] = []
    seen: set[str] = set()
    for e in entries:
        for t in e.technologies:
            key = t.lower()
            if key not in seen:
                seen.add(key)
                techs.append(t)
    return {"technologies": techs}


def _dump_entries(entries: list[KBEntry]) -> list[dict[str, Any]]:
    # Stable field order via model_dump
    return [e.model_dump(mode="json") for e in sorted(entries, key=lambda x: x.id)]


def _fill_related(
    groups: list[list[KBEntry]],
    existing: dict[str, dict[str, Any]],
) -> None:
    all_entries = [e for g in groups for e in g]
    all_ids = {e.id for e in all_entries}
    for e in all_entries:
        e.related_projects = _related(
            e.id,
            existing,
            all_ids,
            domain=e.domain,
            tags=e.tags,
            catalog=all_entries,
        )


def generate(content_dir: Path) -> dict[str, Any]:
    if not content_dir.is_dir():
        raise SystemExit(f"Content dir not found: {content_dir}")

    existing = _load_existing_by_id()
    work = build_work(content_dir, existing)
    personal = build_personal(content_dir, existing)
    labs = build_labs(content_dir, existing)
    _fill_related([work, personal, labs], existing)

    # Validate
    for e in work + personal + labs:
        KBEntry.model_validate(e.model_dump())

    expected_work = {p.name for p in (content_dir / "work").iterdir() if p.is_dir()}
    expected_personal = {p.name for p in (content_dir / "projects").iterdir() if p.is_dir()}
    expected_labs = {p.name for p in (content_dir / "labs").iterdir() if p.is_dir()}
    assert {e.id for e in work} == expected_work, "work slug mismatch"
    assert {e.id for e in personal} == expected_personal, "personal slug mismatch"
    assert {e.id for e in labs} == expected_labs, "labs slug mismatch"

    profile = build_profile(content_dir)
    skills = build_skills(work + personal + labs)

    return {
        "projects": _dump_entries(work),
        "personal_projects": _dump_entries(personal),
        "labs": _dump_entries(labs),
        "profile": profile,
        "skills": skills,
    }


def _write_outputs(payload: dict[str, Any]) -> None:
    mapping = {
        "projects": DATA_DIR / "projects.json",
        "personal_projects": DATA_DIR / "personal_projects.json",
        "labs": DATA_DIR / "labs.json",
        "profile": DATA_DIR / "profile.json",
        "skills": DATA_DIR / "skills.json",
    }
    for key, path in mapping.items():
        text = json.dumps(payload[key], ensure_ascii=False, indent=2) + "\n"
        path.write_text(text, encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)}")


def _check_drift(payload: dict[str, Any]) -> int:
    mapping = {
        "projects": DATA_DIR / "projects.json",
        "personal_projects": DATA_DIR / "personal_projects.json",
        "labs": DATA_DIR / "labs.json",
        "profile": DATA_DIR / "profile.json",
        "skills": DATA_DIR / "skills.json",
    }
    drifted = False
    for key, path in mapping.items():
        new_text = json.dumps(payload[key], ensure_ascii=False, indent=2) + "\n"
        old_text = path.read_text(encoding="utf-8") if path.exists() else ""
        if old_text != new_text:
            print(f"DRIFT: {path.relative_to(ROOT)}")
            drifted = True
        else:
            print(f"OK: {path.relative_to(ROOT)}")
    return 1 if drifted else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate agent KB from portfolio content")
    parser.add_argument(
        "--content-dir",
        type=Path,
        default=Path(
            __import__("os").environ.get("PORTFOLIO_CONTENT_DIR", str(DEFAULT_CONTENT))
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate drift only (exit 1 if generated output differs from files)",
    )
    args = parser.parse_args()
    payload = generate(args.content_dir.resolve())
    counts = (
        len(payload["projects"]),
        len(payload["personal_projects"]),
        len(payload["labs"]),
    )
    print(f"Generated work={counts[0]} personal={counts[1]} labs={counts[2]} total={sum(counts)}")

    # Cold-start regression hint (A0 case 7 content)
    adk = next((p for p in payload["projects"] if p["id"] == "ai-agents-adk"), None)
    if adk:
        blob = " ".join(
            adk.get("challenges", [])
            + [adk.get("implementation", ""), adk.get("context", "")]
        ).lower()
        if "cold start" not in blob and "cold-start" not in blob:
            print("WARNING: ai-agents-adk missing cold start mention after sync")

    if args.check:
        return _check_drift(payload)
    _write_outputs(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
