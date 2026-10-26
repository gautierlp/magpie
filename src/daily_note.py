"""Read and rewrite the three marked sections of an Obsidian daily or weekly note."""
import re
from pathlib import Path

DAILY = (("did", "**Did:**"), ("blocked", "**Blocked:**"), ("next", "**Next:**"))
WEEKLY = (("moved", "**Moved:**"), ("blocked", "**Still blocked:**"), ("focus", "**Focus:**"))
KEYS = tuple(key for key, _ in DAILY)
HEADING = re.compile(r"^#{1,6}\s", re.MULTILINE)


def note_path(vault, day, journal_dir="50 Journal/daily"):
    return Path(vault) / journal_dir / f"{day.isoformat()}.md"


def from_template(vault, day, template="90 Templates/daily.md"):
    text = (Path(vault) / template).read_text(encoding="utf-8")
    return text.replace("{{date:YYYY-MM-DD}}", day.isoformat())


def _positions(text, markers):
    positions = []
    for marker in markers:
        index = text.find(marker)
        if index == -1:
            raise ValueError(f"missing marker {marker}")
        positions.append(index)
    if positions != sorted(positions):
        raise ValueError("markers out of order")
    return positions


def _tail_start(text, start):
    """Index of the first heading line after `start`, or the end of the text."""
    match = HEADING.search(text, start)
    return match.start() if match else len(text)


def read_sections(text, kind=DAILY):
    """Return {key: stripped text under its marker} for the three markers of `kind`."""
    keys = [key for key, _ in kind]
    markers = [marker for _, marker in kind]
    p = _positions(text, markers)
    bounds = [(p[0], p[1]), (p[1], p[2]), (p[2], _tail_start(text, p[2]))]
    return {
        key: text[start + len(marker):end].strip()
        for key, marker, (start, end) in zip(keys, markers, bounds)
    }


def _render(marker, bullets):
    if not bullets:
        return f"{marker}\n"
    lines = "\n".join(f"- {bullet.removeprefix('- ').strip()}" for bullet in bullets)
    return f"{marker}\n\n{lines}\n"


def replace_sections(text, sections, kind=DAILY):
    """Rewrite the three sections from lists of bullets. The title above and any
    heading below the last section, with its text, stay as they are.

    The first section must not be empty. A blank line follows each list, so Obsidian
    does not fold the next marker into the last list item.
    """
    first = kind[0][0]
    if not sections.get(first):
        raise ValueError(f"{first} section is empty")
    p = _positions(text, [marker for _, marker in kind])
    head = text[: p[0]]
    tail = text[_tail_start(text, p[2]) :]
    parts = [_render(marker, sections.get(key) or []) for key, marker in kind]
    return head + "\n".join(parts + ([tail] if tail else []))
