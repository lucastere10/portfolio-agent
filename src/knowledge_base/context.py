"""Build compact knowledge context blocks for the conversational agent."""

from __future__ import annotations

from src.domain.models import KBEntry, ProjectMatch
from src.knowledge_base.loader import get_by_id


def _type_label(entry: KBEntry, lang: str) -> str:
    if entry.type == "personal_project":
        return "Projeto pessoal" if lang == "pt" else "Personal project"
    if entry.type == "project":
        return "Projeto profissional" if lang == "pt" else "Work project"
    return "Lab"


def _entry_links_line(entry: KBEntry, lang: str) -> str | None:
    parts: list[str] = []
    if entry.demo_url:
        label = "demo" if lang == "en" else "demo"
        parts.append(f"[{label}]({entry.demo_url})")
    if entry.github_url:
        label = "código" if lang == "pt" else "code"
        parts.append(f"[{label}]({entry.github_url})")
    elif entry.repo_url:
        label = "repo" if lang == "en" else "repo"
        parts.append(f"[{label}]({entry.repo_url})")
    if entry.slug:
        path = entry.slug if entry.slug.startswith("/") else f"/{entry.slug}"
        label = "página" if lang == "pt" else "page"
        parts.append(f"[{label}]({path})")
    if not parts:
        return None
    return "Links: " + " · ".join(parts)


def format_entry_details(entry: KBEntry, lang: str, *, compact: bool = False) -> str:
    """Context for a catalog entry. compact=True for related items."""
    type_label = _type_label(entry, lang)
    summary = entry.summary.strip()
    if compact and len(summary) > 160:
        summary = summary[:157].rstrip() + "..."

    lines = [
        f"[{type_label}] {entry.title} (id: {entry.id})",
        f"Domain: {entry.domain}",
        f"Summary: {summary}",
    ]
    if entry.technologies:
        lines.append(f"Technologies: {', '.join(entry.technologies[:8])}")

    links = _entry_links_line(entry, lang)
    if links:
        lines.append(links)

    if compact:
        if entry.learnings:
            label = "Aprendizado:" if lang == "pt" else "Learning:"
            lines.append(f"{label} {entry.learnings[0]}")
        return "\n".join(lines)

    if entry.tagline:
        lines.append(f"Tagline: {entry.tagline}")
    if entry.context and entry.context != entry.summary:
        ctx = entry.context.strip()
        if len(ctx) > 220:
            ctx = ctx[:217].rstrip() + "..."
        lines.append(f"Context: {ctx}")
    if entry.challenges:
        lines.append("Challenges:")
        lines.extend(f"  - {c}" for c in entry.challenges[:3])
    if entry.decisions:
        lines.append("Decisions:")
        for d in entry.decisions[:2]:
            reasoning = d.reasoning
            if len(reasoning) > 180:
                reasoning = reasoning[:177].rstrip() + "..."
            lines.append(f"  - {d.title}: {reasoning}")
    if entry.tradeoffs:
        tradeoffs = entry.tradeoffs.strip()
        if len(tradeoffs) > 200:
            tradeoffs = tradeoffs[:197].rstrip() + "..."
        lines.append(f"Tradeoffs: {tradeoffs}")
    if entry.implementation:
        impl = entry.implementation.strip()
        if len(impl) > 220:
            impl = impl[:217].rstrip() + "..."
        lines.append(f"Implementation: {impl}")
    if entry.narrative:
        lines.append("Narrative:")
        lines.extend(f"  - {n}" for n in entry.narrative[:4])
    if entry.learnings:
        label = "Aprendizados:" if lang == "pt" else "Learnings:"
        lines.append(label)
        lines.extend(f"  - {learning}" for learning in entry.learnings[:3])
    if entry.demonstrates:
        lines.append(f"Demonstrates: {', '.join(entry.demonstrates[:5])}")

    return "\n".join(lines)


def format_overview_line(entry: KBEntry) -> str:
    """One-liner for portfolio browse context."""
    tag = entry.tagline or entry.summary
    if len(tag) > 90:
        tag = tag[:87].rstrip() + "..."
    return f"- {entry.title} ({entry.id}, {entry.domain}): {tag}"


def build_matches_context(
    matches: list[ProjectMatch],
    lang: str,
    primary_id: str | None,
) -> str:
    """Primary + at most one related entry."""
    if not matches:
        return "Nenhum case encontrado." if lang == "pt" else "No matching cases found."

    ordered: list[ProjectMatch] = []
    if primary_id:
        for m in matches:
            if m.id == primary_id:
                ordered.append(m)
                break
    for m in matches:
        if primary_id and m.id == primary_id:
            continue
        ordered.append(m)
        if len(ordered) >= 2:
            break
    if not ordered:
        ordered = matches[:2]

    sections: list[str] = []
    for match in ordered:
        entry = get_by_id(match.id)
        if entry is None:
            continue
        is_primary = match.id == primary_id
        if lang == "pt":
            marker = (
                "★ PRINCIPAL (destaque no painel à direita)"
                if is_primary
                else "- Relacionado"
            )
        else:
            marker = (
                "★ PRIMARY (shown in right panel)"
                if is_primary
                else "- Related"
            )
        details = format_entry_details(entry, lang, compact=not is_primary)
        sections.append(f"{marker}\n{details}")

    return "\n\n".join(sections)


def build_overview_context(
    matches: list[ProjectMatch],
    lang: str,
    primary_id: str | None,
) -> str:
    """Browse intent: short answer guidance + compact name list (not full essays)."""
    _ = primary_id
    if lang == "pt":
        header = (
            "MODO OVERVIEW — limite rígido: no máximo 4 frases no total (~80 palavras). "
            "Formato: uma frase de enquadramento + até 4 nomes com meia linha. "
            "PROIBIDO escrever um parágrafo por projeto. "
            "PROIBIDO começar com Claro/Sure/Certainly. "
            "Convide a aprofundar um item. "
            "NÃO diga que nenhum projeto foi encontrado se a lista abaixo não estiver vazia."
        )
    else:
        header = (
            "OVERVIEW MODE — hard limit: at most 4 sentences total (~80 words). "
            "Format: one framing sentence + up to 4 names with a half-line each. "
            "FORBIDDEN: a paragraph per project. "
            "FORBIDDEN openings: Claro/Sure/Certainly. "
            "Invite them to go deeper on one item. "
            "Do NOT say that no projects were found if the list below is non-empty."
        )

    lines: list[str] = []
    for match in matches[:6]:
        entry = get_by_id(match.id)
        if entry is None:
            continue
        lines.append(format_overview_line(entry))

    body = "\n".join(lines) if lines else (
        "Nenhum item." if lang == "pt" else "No items."
    )
    label = "Destaques disponíveis:" if lang == "pt" else "Available highlights:"
    return f"{header}\n\n{label}\n{body}"


def build_profile_context(lang: str) -> str:
    """Short profile context for the system instruction (lang-aware)."""
    from src.knowledge_base.loader import get_persona, get_profile, get_skills

    profile = get_profile()
    persona = get_persona()
    skills = get_skills()

    name = profile.get("name", "Lucas Caldas")
    about = profile.get(f"about_{lang}") or profile.get("about_en", "")
    specialties = profile.get("specialties", [])
    voice = persona.get(f"voice_{lang}", persona.get("voice_en", ""))
    focus = persona.get(f"current_focus_{lang}", persona.get("current_focus_en", ""))
    highlights = persona.get(
        f"career_highlights_{lang}", persona.get("career_highlights_en", [])
    )
    preferred = persona.get(
        f"preferred_projects_{lang}", persona.get("preferred_projects_en", [])
    )
    hooks = persona.get(
        f"conversation_hooks_{lang}", persona.get("conversation_hooks_en", [])
    )
    boundaries = persona.get(f"boundaries_{lang}", persona.get("boundaries_en", []))
    techs = ", ".join(skills.get("technologies", [])[:15])
    links = profile.get("links") or {}
    contact_path = "/en/contact" if lang == "en" else "/contact"
    linkedin = links.get("linkedin") or "https://linkedin.com/in/lucas-caldas50"
    github = links.get("github") or "https://github.com/lucastere10"

    highlights_text = "\n".join(f"- {h}" for h in highlights[:4])
    preferred_text = "\n".join(f"- {p}" for p in preferred[:5])
    hooks_text = "\n".join(f"- {h}" for h in hooks[:3])
    boundaries_text = "\n".join(f"- {b}" for b in boundaries[:4])

    return f"""Name: {name}
About: {about}
Specialties: {', '.join(specialties)}
Technologies: {techs}
Current focus: {focus}
Voice: {voice}

Links (always use markdown in replies):
- LinkedIn: [{linkedin}]({linkedin})
- GitHub: [{github}]({github})
- Contact page: [{contact_path}]({contact_path})

Preferred projects (use when recommending):
{preferred_text}

Conversation hooks:
{hooks_text}

Career highlights:
{highlights_text}

Boundaries:
{boundaries_text}"""
