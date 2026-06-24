"""Build rich knowledge context blocks for the conversational agent."""

from __future__ import annotations

from src.domain.models import KBEntry, ProjectMatch
from src.knowledge_base.loader import get_by_id


def format_entry_details(entry: KBEntry, lang: str) -> str:
    """Compact but substantive context for a single catalog entry."""
    type_label = "Project" if entry.type == "project" else "Lab"

    lines = [
        f"[{type_label}] {entry.title} (id: {entry.id})",
        f"Domain: {entry.domain}",
        f"Summary: {entry.summary}",
    ]
    if entry.tagline:
        lines.append(f"Tagline: {entry.tagline}")
    if entry.context:
        lines.append(f"Context: {entry.context}")
    if entry.technologies:
        lines.append(f"Technologies: {', '.join(entry.technologies)}")
    if entry.challenges:
        lines.append("Challenges:")
        lines.extend(f"  - {c}" for c in entry.challenges[:3])
    if entry.learnings:
        label = "Aprendizados:" if lang == "pt" else "Learnings:"
        lines.append(label)
        lines.extend(f"  - {learning}" for learning in entry.learnings[:3])
    if entry.demonstrates:
        lines.append(f"Demonstrates: {', '.join(entry.demonstrates[:5])}")

    return "\n".join(lines)


def build_matches_context(
    matches: list[ProjectMatch],
    lang: str,
    primary_id: str | None,
) -> str:
    """Rich context block with enough detail for substantive answers."""
    if not matches:
        return "Nenhum case encontrado." if lang == "pt" else "No matching cases found."

    sections: list[str] = []
    for match in matches[:4]:
        entry = get_by_id(match.id)
        if entry is None:
            continue
        marker = "★ PRIMARY (shown in right panel)" if match.id == primary_id else "- Related"
        if lang == "pt" and match.id == primary_id:
            marker = "★ PRINCIPAL (destaque no painel à direita)"
        elif lang == "pt":
            marker = "- Relacionado"
        sections.append(f"{marker}\n{format_entry_details(entry, lang)}")

    return "\n\n".join(sections)


def build_profile_context(lang: str) -> str:
    """Short profile context for the system instruction."""
    from src.knowledge_base.loader import get_persona, get_profile, get_skills

    profile = get_profile()
    persona = get_persona()
    skills = get_skills()

    name = profile.get("name", "Lucas Caldas")
    about = profile.get("about_en", "")
    specialties = profile.get("specialties", [])
    voice = persona.get(f"voice_{lang}", persona.get("voice_en", ""))
    focus = persona.get(f"current_focus_{lang}", persona.get("current_focus_en", ""))
    highlights = persona.get(f"career_highlights_{lang}", persona.get("career_highlights_en", []))
    boundaries = persona.get(f"boundaries_{lang}", persona.get("boundaries_en", []))
    techs = ", ".join(skills.get("technologies", [])[:15])

    highlights_text = "\n".join(f"- {h}" for h in highlights[:4])
    boundaries_text = "\n".join(f"- {b}" for b in boundaries[:4])

    return f"""Name: {name}
About: {about}
Specialties: {', '.join(specialties)}
Technologies: {techs}
Current focus: {focus}
Voice: {voice}

Career highlights:
{highlights_text}

Boundaries:
{boundaries_text}"""
