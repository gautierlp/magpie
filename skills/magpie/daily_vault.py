"""Vault facts for the daily note: project and area cards, and the day's logs."""
import re
from pathlib import Path

from daily_git import repo_name

CARD_KINDS = (("10 Projects", "_project.md"), ("20 Areas", "_area.md"))


def _field(text, label):
    match = re.search(rf"^\*\*{re.escape(label)}:\*\*\s*(.+)$", text, re.M)
    return match.group(1).strip() if match else None


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
                "next_action": _field(text, "Next action"),
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
