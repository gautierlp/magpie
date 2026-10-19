"""The weekly note: ISO week bounds, the week's daily notes, and the cards they name."""
import re
from datetime import timedelta
from pathlib import Path

import daily_note

CARD_FIELDS = ("name", "link", "next_action", "open_decisions")


def week_bounds(day):
    """Monday and Sunday of the ISO week that holds `day`."""
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def week_id(day):
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def note_path(vault, day, weekly_dir="50 Journal/weekly"):
    return Path(vault) / weekly_dir / f"{week_id(day)}.md"


def blank(day):
    """The text of a new weekly note: the title line, then the three empty markers."""
    start, end = week_bounds(day)
    markers = "".join(f"{marker}\n" for _, marker in daily_note.WEEKLY)
    return f"# {week_id(day)} ({start.isoformat()} to {end.isoformat()})\n\n{markers}"


def _day_entry(path, current, today):
    """One day's entry, and the error text when its note cannot be read."""
    entry = {"date": current.isoformat()}
    if current > today:
        entry["status"] = "future"
        return entry, None
    if not path.exists():
        entry["status"] = "missing"
        return entry, None
    try:
        sections = daily_note.read_sections(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        entry["status"] = "unreadable"
        return entry, str(exc)
    if not any(sections.values()):
        entry["status"] = "missing"
        return entry, None
    entry["status"] = "ok"
    entry.update(sections)
    return entry, None


def read_days(vault, day, today, journal_dir="50 Journal/daily"):
    """The 7 days of the week of `day`, Monday first, and the errors of unreadable notes."""
    start, _ = week_bounds(day)
    days, errors = [], {}
    for offset in range(7):
        current = start + timedelta(days=offset)
        path = daily_note.note_path(vault, current, journal_dir)
        entry, error = _day_entry(path, current, today)
        days.append(entry)
        if error:
            errors[current.isoformat()] = error
    return days, errors


def cards_named(cards, days):
    """The cards whose link, or whole-word name, appears in one of the week's notes."""
    text = "\n".join(day.get(key, "") for day in days for key in daily_note.KEYS)
    return [
        {field: card[field] for field in CARD_FIELDS}
        for card in cards
        if card["link"] in text or re.search(rf"\b{re.escape(card['name'])}\b", text)
    ]
