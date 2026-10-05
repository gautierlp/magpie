"""Read and rewrite the Did / Blocked / Next sections of an Obsidian daily note."""
from pathlib import Path

KEYS = ("did", "blocked", "next")
MARKERS = ("**Did:**", "**Blocked:**", "**Next:**")


def note_path(vault, day, journal_dir="50 Journal/daily"):
    return Path(vault) / journal_dir / f"{day.isoformat()}.md"


def from_template(vault, day, template="90 Templates/daily.md"):
    text = (Path(vault) / template).read_text(encoding="utf-8")
    return text.replace("{{date:YYYY-MM-DD}}", day.isoformat())


def _positions(text):
    positions = []
    for marker in MARKERS:
        index = text.find(marker)
        if index == -1:
            raise ValueError(f"missing marker {marker}")
        positions.append(index)
    if positions != sorted(positions):
        raise ValueError("markers out of order")
    return positions


def read_sections(text):
    """Return {"did", "blocked", "next"} with the stripped text under each marker."""
    p = _positions(text)
    bounds = [(p[0], p[1]), (p[1], p[2]), (p[2], len(text))]
    return {
        key: text[start + len(marker):end].strip()
        for key, marker, (start, end) in zip(KEYS, MARKERS, bounds)
    }


def _render(marker, bullets):
    if not bullets:
        return f"{marker}\n"
    lines = "\n".join(f"- {bullet.removeprefix('- ').strip()}" for bullet in bullets)
    return f"{marker}\n\n{lines}\n"


def replace_sections(text, sections):
    """Rewrite the three sections from lists of bullets. The title above stays as it is.

    A blank line follows each list, so Obsidian does not fold the next marker into
    the last list item.
    """
    if not sections.get("did"):
        raise ValueError("did section is empty")
    head = text[: _positions(text)[0]]
    parts = [_render(marker, sections.get(key) or []) for key, marker in zip(KEYS, MARKERS)]
    return head + "\n".join(parts)
