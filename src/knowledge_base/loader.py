"""Load and cache knowledge base JSON files at application startup."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.domain.models import KBEntry

# Data lives alongside this module: src/knowledge_base/data/
_DATA_DIR = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, KBEntry]:
    """Load all projects and labs indexed by ID."""
    entries: dict[str, KBEntry] = {}
    for fname in ("projects.json", "labs.json"):
        path = _DATA_DIR / fname
        raw = json.loads(path.read_text(encoding="utf-8"))
        for item in raw:
            entry = KBEntry(**item)
            entries[entry.id] = entry
    return entries


def get_data_dir() -> Path:
    return _DATA_DIR


def get_all() -> list[KBEntry]:
    return list(load_catalog().values())


def get_by_id(entry_id: str) -> KBEntry | None:
    return load_catalog().get(entry_id)


def get_projects() -> list[KBEntry]:
    return [e for e in get_all() if e.type == "project"]


def get_labs() -> list[KBEntry]:
    return [e for e in get_all() if e.type == "lab"]


@lru_cache(maxsize=1)
def load_profile() -> dict[str, Any]:
    raw = json.loads((_DATA_DIR / "profile.json").read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def get_profile() -> dict[str, Any]:
    return load_profile()


@lru_cache(maxsize=1)
def load_persona() -> dict[str, Any]:
    path = _DATA_DIR / "persona.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def get_persona() -> dict[str, Any]:
    return load_persona()


@lru_cache(maxsize=1)
def load_skills() -> dict[str, Any]:
    path = _DATA_DIR / "skills.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def get_skills() -> dict[str, Any]:
    return load_skills()
