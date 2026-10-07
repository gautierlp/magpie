"""Vault facts for the daily note: project and area cards, and the day's logs."""
import re
from pathlib import Path

from daily_git import repo_name

CARD_KINDS = (("10 Projects", "_project.md"), ("20 Areas", "_area.md"))


def _field(text, label):
    match = re.search(rf"^\*\*{re.escape(label)}:\*\*[ \t]*(.+)$", text, re.M)
    return (match.group(1).strip() or None) if match else None


BOX_UNDER_LABEL = re.compile(r"^\*\*Next action:\*\*[ \t]*\n[ \t]*[-*] \[ \] (.+)$", re.M)
MARKS = re.compile(r"📅\s*\d{4}-\d{2}-\d{2}|⏫")


def next_action(text):
    """The open checkbox under `**Next action:**`, or the old one-line text after the label."""
    match = BOX_UNDER_LABEL.search(text)
    if match:
        return " ".join(MARKS.sub("", match.group(1)).split()) or None
    return _field(text, "Next action")


def _repos(text):
    match = re.search(r"^repo:\s*(.+)$", text, re.M)
    if not match:
        return []
    return [repo_name(url) for url in match.group(1).split(",") if url.strip()]


def load_cards(vault):
    """One dict per card. `folder` is a Path for internal use; never put it in output."""
    vault = Path(vault)
    cards = []
    for folder, filename in CARD_KINDS:
        for path in sorted((vault / folder).glob(f"*/{filename}")):
            text = path.read_text(encoding="utf-8")
            name = path.parent.name
            target = path.relative_to(vault).with_suffix("").as_posix()
            cards.append({
                "name": name,
                "link": f"[[{target}|{name}]]",
                "repos": _repos(text),
                "next_action": next_action(text),
                "open_decisions": _field(text, "Open decisions"),
                "folder": path.parent,
            })
    return cards


def logs_for_day(cards, day):
    logs = {}
    for card in cards:
        path = card["folder"] / "log" / f"{day.isoformat()}.md"
        if path.exists():
            logs.setdefault(card["name"], []).append(path.read_text(encoding="utf-8"))
    return logs
