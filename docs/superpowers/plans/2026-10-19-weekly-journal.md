# Weekly Journal Note Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/magpie week` drafts a weekly note (Moved / Still blocked / Focus) from the week's daily notes, after it fills the missing days with the daily run.

**Architecture:** `daily_note.py` takes a marker set, so the daily and weekly notes share read, render and replace. A new `daily_week.py` holds the week logic (ISO bounds, the 7 daily notes, the cards they name). `daily.py` gets a `week` subcommand and a `write --week` flag. The skill gets a "Weekly run" section that does the gap filling and the drafting.

**Tech Stack:** Python 3 stdlib only, pytest, `just`.

**Spec:** `docs/superpowers/specs/2026-10-19-weekly-journal-design.md`

## Global Constraints

- Stdlib only at runtime. Imports are flat (`import daily_week`), `conftest.py` puts `src/` on `sys.path`.
- The repo is public: no personal value (names, projects, paths under a real home) in code, tests or skill text.
- `src/` is the source of truth. `skills/magpie/*.py` are copies made by `just install`; never edit them by hand.
- One test file per module. TDD: failing test first.
- No em dashes or en dashes anywhere (code, comments, docs, commit messages).
- The daily note behavior must not change: every existing test stays green with no edit.
- Weekly file: `<vault>/<weekly_dir>/YYYY-Www.md`, title line `# YYYY-Www (YYYY-MM-DD to YYYY-MM-DD)`, markers `**Moved:**`, `**Still blocked:**`, `**Focus:**`.
- Week = ISO week, Monday to Sunday. Default date for `week` = yesterday in the configured timezone.
- Conventional commits, no Co-Authored-By trailer.

**User decisions (already made):**
- The weekly note does both: a look back per project and up to 3 focus items.
- Missing days are filled first with the daily run; a day with no activity gets no note.
- Started by hand (`/magpie week`), no schedule.
- No monthly note, no vault template, no checkboxes in Focus.

**Deviation from the spec, on purpose:** the spec lists the week tests in `test_daily.py`. The repo rule is one test file per module, so the week logic lives in `src/daily_week.py` with `tests/test_daily_week.py`; only the CLI tests go in `test_daily.py`.

---

## File structure

- Modify `src/daily_note.py`: marker sets `DAILY` and `WEEKLY`; `read_sections` and `replace_sections` take one as an optional argument (default `DAILY`).
- Modify `src/daily_config.py`: new key `weekly_dir`.
- Create `src/daily_week.py`: `week_bounds`, `week_id`, `note_path`, `blank`, `read_days`, `cards_named`.
- Modify `src/daily.py`: `_today`, `week()`, `write()` with `--week`, `week` subparser, `resolve` changes.
- Modify `skills/magpie/SKILL.md`, `README.md`, `CLAUDE.md`.
- Tests: `tests/test_daily_note.py`, `tests/test_daily_config.py`, `tests/test_daily_week.py` (new), `tests/test_daily.py`.

---

### Task 1: Marker sets in `daily_note.py`

**Goal:** `read_sections` and `replace_sections` work with the daily markers (default) and the weekly markers.

**Files:**
- Modify: `src/daily_note.py`
- Test: `tests/test_daily_note.py`

**Acceptance Criteria:**
- [ ] `daily_note.WEEKLY` is `(("moved", "**Moved:**"), ("blocked", "**Still blocked:**"), ("focus", "**Focus:**"))`.
- [ ] `read_sections(text, daily_note.WEEKLY)` returns `{"moved", "blocked", "focus"}`.
- [ ] `replace_sections(text, {...}, daily_note.WEEKLY)` with an empty `moved` raises `ValueError("moved section is empty")`.
- [ ] All existing tests in `tests/test_daily_note.py` and `tests/test_daily.py` pass with no edit.

**Verify:** `.venv/bin/pytest tests/test_daily_note.py -v` → all pass

**Steps:**

- [ ] **Step 0: Make the venv (worktree only, once)**

Run: `python3 -m venv .venv && .venv/bin/pip install -q -r requirements-dev.txt && just test`
Expected: all existing tests pass.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_daily_note.py`)

```python
WEEK_NOTE = (
    "# 2026-W42 (2026-10-12 to 2026-10-18)\n\n"
    "**Moved:**\n\n- site: form split\n\n**Still blocked:**\n\n**Focus:**\n\n- fix the blockers\n"
)


def test_read_sections_with_the_weekly_markers():
    assert daily_note.read_sections(WEEK_NOTE, daily_note.WEEKLY) == {
        "moved": "- site: form split",
        "blocked": "",
        "focus": "- fix the blockers",
    }


def test_replace_sections_with_the_weekly_markers_keeps_the_title():
    out = daily_note.replace_sections(
        WEEK_NOTE, {"moved": ["a"], "blocked": ["b"], "focus": []}, daily_note.WEEKLY)
    assert out == (
        "# 2026-W42 (2026-10-12 to 2026-10-18)\n\n"
        "**Moved:**\n\n- a\n\n**Still blocked:**\n\n- b\n\n**Focus:**\n"
    )


def test_replace_sections_refuses_an_empty_moved():
    with pytest.raises(ValueError, match="moved section is empty"):
        daily_note.replace_sections(
            WEEK_NOTE, {"moved": [], "blocked": [], "focus": ["x"]}, daily_note.WEEKLY)


def test_the_daily_markers_are_not_found_in_a_weekly_note():
    with pytest.raises(ValueError, match="Did"):
        daily_note.read_sections(WEEK_NOTE)
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `.venv/bin/pytest tests/test_daily_note.py -v`
Expected: FAIL with `AttributeError: module 'daily_note' has no attribute 'WEEKLY'`.

- [ ] **Step 3: Write the implementation** (replace the top constants and the four functions below `from_template`)

```python
"""Read and rewrite the three marked sections of an Obsidian daily or weekly note."""
from pathlib import Path

DAILY = (("did", "**Did:**"), ("blocked", "**Blocked:**"), ("next", "**Next:**"))
WEEKLY = (("moved", "**Moved:**"), ("blocked", "**Still blocked:**"), ("focus", "**Focus:**"))
KEYS = tuple(key for key, _ in DAILY)
MARKERS = tuple(marker for _, marker in DAILY)
```

`note_path` and `from_template` stay as they are. Then:

```python
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


def read_sections(text, kind=DAILY):
    """Return {key: stripped text under its marker} for the three markers of `kind`."""
    keys = [key for key, _ in kind]
    markers = [marker for _, marker in kind]
    p = _positions(text, markers)
    bounds = [(p[0], p[1]), (p[1], p[2]), (p[2], len(text))]
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
    """Rewrite the three sections from lists of bullets. The title above stays as it is.

    The first section must not be empty. A blank line follows each list, so Obsidian
    does not fold the next marker into the last list item.
    """
    first = kind[0][0]
    if not sections.get(first):
        raise ValueError(f"{first} section is empty")
    head = text[: _positions(text, [marker for _, marker in kind])[0]]
    parts = [_render(marker, sections.get(key) or []) for key, marker in kind]
    return head + "\n".join(parts)
```

- [ ] **Step 4: Run all tests**

Run: `just test`
Expected: all pass, including the 4 new ones.

- [ ] **Step 5: Commit**

```bash
git add src/daily_note.py tests/test_daily_note.py
git commit -m "refactor(note): take the marker set as a parameter"
```

```json:metadata
{"files": ["src/daily_note.py", "tests/test_daily_note.py"], "verifyCommand": ".venv/bin/pytest -v", "acceptanceCriteria": ["WEEKLY marker set defined", "read_sections with WEEKLY returns moved/blocked/focus", "empty moved raises 'moved section is empty'", "existing tests pass unchanged"], "modelTier": "mechanical"}
```

---

### Task 2: `weekly_dir` config key

**Goal:** The config accepts `weekly_dir`, default `50 Journal/weekly`.

**Files:**
- Modify: `src/daily_config.py`
- Test: `tests/test_daily_config.py`

**Acceptance Criteria:**
- [ ] `daily_config.DEFAULTS["weekly_dir"] == "50 Journal/weekly"`.
- [ ] A config file with `{"weekly_dir": "J/w"}` loads with no error and gives `"J/w"`.

**Verify:** `.venv/bin/pytest tests/test_daily_config.py -v` → all pass

**Steps:**

- [ ] **Step 1: Write the failing tests** (append to `tests/test_daily_config.py`)

```python
def test_weekly_dir_has_a_default():
    assert daily_config.DEFAULTS["weekly_dir"] == "50 Journal/weekly"


def test_weekly_dir_can_be_overridden(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"weekly_dir": "J/w"}), encoding="utf-8")
    assert daily_config.load(path)["weekly_dir"] == "J/w"
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/pytest tests/test_daily_config.py -v`
Expected: FAIL with `KeyError: 'weekly_dir'` and `ValueError: unknown config keys: weekly_dir`.

- [ ] **Step 3: Add the key** in `DEFAULTS`, right after `"journal_dir"`:

```python
    "weekly_dir": "50 Journal/weekly",
```

- [ ] **Step 4: Run all tests**

Run: `just test`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/daily_config.py tests/test_daily_config.py
git commit -m "feat(config): add weekly_dir"
```

```json:metadata
{"files": ["src/daily_config.py", "tests/test_daily_config.py"], "verifyCommand": ".venv/bin/pytest -v", "acceptanceCriteria": ["weekly_dir default is '50 Journal/weekly'", "weekly_dir override loads"], "modelTier": "mechanical"}
```

---

### Task 3: Week logic (`daily_week.py`)

**Goal:** A module that gives the ISO week of a date, the weekly note path and blank text, the status of the 7 daily notes, and the cards they name.

**Files:**
- Create: `src/daily_week.py`
- Test: `tests/test_daily_week.py`

**Acceptance Criteria:**
- [ ] `week_bounds(date(2026, 10, 14)) == (date(2026, 10, 12), date(2026, 10, 18))`; a Monday and a Sunday map to the same week.
- [ ] `week_id(date(2026, 12, 31)) == "2026-W53"` and `week_id(date(2026, 10, 14)) == "2026-W42"`.
- [ ] `read_days` gives `ok`, `missing` (no file or three empty sections), `unreadable` (with the reason in errors) and `future` (after `today`; `today` itself is not future).
- [ ] `cards_named` keeps a card whose link or whole-word name is in the week's text, and drops `folder` and `repos`.

**Verify:** `.venv/bin/pytest tests/test_daily_week.py -v` → all pass

**Steps:**

- [ ] **Step 1: Write the failing tests** (`tests/test_daily_week.py`)

```python
from datetime import date

import daily_week

DAY = "# {d}\n\n**Did:**\n\n- {did}\n\n**Blocked:**\n\n**Next:**\n"


def _daily(vault, iso, text):
    folder = vault / "50 Journal" / "daily"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{iso}.md").write_text(text, encoding="utf-8")


def test_week_bounds_runs_monday_to_sunday():
    assert daily_week.week_bounds(date(2026, 10, 14)) == (date(2026, 10, 12), date(2026, 10, 18))
    assert daily_week.week_bounds(date(2026, 10, 12)) == (date(2026, 10, 12), date(2026, 10, 18))
    assert daily_week.week_bounds(date(2026, 10, 18)) == (date(2026, 10, 12), date(2026, 10, 18))


def test_week_id_uses_the_iso_year_and_week():
    assert daily_week.week_id(date(2026, 10, 14)) == "2026-W42"
    assert daily_week.week_id(date(2026, 12, 31)) == "2026-W53"
    assert daily_week.week_id(date(2027, 1, 4)) == "2027-W01"


def test_note_path_and_blank(tmp_path):
    day = date(2026, 10, 14)
    assert daily_week.note_path(tmp_path, day) == tmp_path / "50 Journal" / "weekly" / "2026-W42.md"
    assert daily_week.blank(day) == (
        "# 2026-W42 (2026-10-12 to 2026-10-18)\n\n"
        "**Moved:**\n**Still blocked:**\n**Focus:**\n"
    )


def test_read_days_gives_each_status(tmp_path):
    _daily(tmp_path, "2026-10-12", DAY.format(d="2026-10-12", did="wrote the spec"))
    _daily(tmp_path, "2026-10-13", "# 2026-10-13\n\n**Did:** \n**Blocked:** \n**Next:** \n")
    _daily(tmp_path, "2026-10-14", "# 2026-10-14\n\nno markers here\n")
    days, errors = daily_week.read_days(tmp_path, date(2026, 10, 14), today=date(2026, 10, 16))
    assert [d["status"] for d in days] == [
        "ok", "missing", "unreadable", "missing", "missing", "future", "future"]
    assert days[0] == {"date": "2026-10-12", "status": "ok",
                       "did": "- wrote the spec", "blocked": "", "next": ""}
    assert days[1] == {"date": "2026-10-13", "status": "missing"}
    assert "missing marker" in errors["2026-10-14"]


def test_cards_named_matches_a_link_or_a_whole_word_name():
    cards = [
        {"name": "site", "link": "[[10 Projects/site/_project|site]]", "repos": ["x"],
         "next_action": "ship", "open_decisions": "none.", "folder": "/tmp/x"},
        {"name": "dog", "link": "[[20 Areas/dog/_area|dog]]", "repos": [],
         "next_action": None, "open_decisions": None, "folder": "/tmp/y"},
        {"name": "house", "link": "[[10 Projects/house/_project|house]]", "repos": [],
         "next_action": "measure", "open_decisions": "roof", "folder": "/tmp/z"},
    ]
    days = [
        {"date": "2026-10-12", "status": "ok", "did": "- [[10 Projects/site/_project|site]]: form",
         "blocked": "", "next": "- dog: book the vet"},
        {"date": "2026-10-13", "status": "missing"},
        {"date": "2026-10-14", "status": "ok", "did": "- read about housekeeping", "blocked": "", "next": ""},
    ]
    assert daily_week.cards_named(cards, days) == [
        {"name": "site", "link": "[[10 Projects/site/_project|site]]",
         "next_action": "ship", "open_decisions": "none."},
        {"name": "dog", "link": "[[20 Areas/dog/_area|dog]]",
         "next_action": None, "open_decisions": None},
    ]
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/pytest tests/test_daily_week.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'daily_week'`.

- [ ] **Step 3: Write `src/daily_week.py`**

```python
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
```

- [ ] **Step 4: Run all tests**

Run: `just test`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/daily_week.py tests/test_daily_week.py
git commit -m "feat(week): read the week's daily notes and the cards they name"
```

```json:metadata
{"files": ["src/daily_week.py", "tests/test_daily_week.py"], "verifyCommand": ".venv/bin/pytest -v", "acceptanceCriteria": ["week_bounds Monday to Sunday", "week_id 2026-12-31 is 2026-W53", "read_days statuses ok/missing/unreadable/future", "cards_named by link or whole-word name, without folder and repos"], "modelTier": "standard"}
```

---

### Task 4: `week` command and `write --week` in `daily.py`

**Goal:** `daily.py week` prints the week's JSON payload; `daily.py write --week` writes the weekly note; `week` defaults to yesterday.

**Files:**
- Modify: `src/daily.py`
- Test: `tests/test_daily.py`

**Acceptance Criteria:**
- [ ] `daily.py week --date 2026-10-14` prints JSON with keys `week`, `start`, `end`, `note_path`, `manual`, `days`, `cards`, `errors`, and `week == "2026-W42"`.
- [ ] `manual` holds the text under each weekly marker of an existing weekly note, else three empty strings.
- [ ] With no `--date`, `week` takes yesterday and `gather` still takes today.
- [ ] `write --week` on a missing file writes `blank(day)` filled with the bullets; on an existing file it keeps the title and prints the old sections.
- [ ] `write --week` with an empty `moved` exits 1, prints `moved section is empty`, and leaves the file.
- [ ] Every existing test in `tests/test_daily.py` passes unchanged.

**Verify:** `.venv/bin/pytest tests/test_daily.py -v` → all pass

**Steps:**

- [ ] **Step 1: Write the failing tests** (append to `tests/test_daily.py`; `from datetime import date` goes with the other imports at the top)

```python
WEEK = "# 2026-W42 (2026-10-12 to 2026-10-18)\n\n**Moved:**\n\n- my bullet\n\n**Still blocked:**\n\n**Focus:**\n"


def _week_args(tmp_path, vault, *extra):
    return daily.parse_args(["week", "--config", str(tmp_path / "none.json"),
                             "--vault", str(vault), *extra])


def test_week_reads_the_days_and_the_named_cards(tmp_path):
    vault, _, _ = _setup(tmp_path)
    (vault / "50 Journal" / "daily" / "2026-10-06.md").write_text(
        "# 2026-10-06\n\n**Did:**\n\n- [[10 Projects/vault-setup/_project|vault-setup]]: spec\n\n"
        "**Blocked:**\n\n**Next:**\n", encoding="utf-8")
    args = _week_args(tmp_path, vault, "--date", "2026-10-07")
    args.today = date(2026, 10, 8)
    payload = daily.week(args)
    assert payload["week"] == "2026-W41"
    assert (payload["start"], payload["end"]) == ("2026-10-05", "2026-10-11")
    assert payload["note_path"].endswith("50 Journal/weekly/2026-W41.md")
    assert payload["manual"] == {"moved": "", "blocked": "", "focus": ""}
    assert [d["status"] for d in payload["days"]] == [
        "ok", "ok", "missing", "missing", "future", "future", "future"]
    assert [c["name"] for c in payload["cards"]] == ["vault-setup"]
    assert payload["errors"] == {}


def test_week_reads_the_manual_bullets_of_an_existing_weekly_note(tmp_path):
    vault, _, _ = _setup(tmp_path)
    folder = vault / "50 Journal" / "weekly"
    folder.mkdir(parents=True)
    (folder / "2026-W42.md").write_text(WEEK, encoding="utf-8")
    args = _week_args(tmp_path, vault, "--date", "2026-10-14")
    args.today = date(2026, 10, 19)
    assert daily.week(args)["manual"] == {"moved": "- my bullet", "blocked": "", "focus": ""}


def test_week_defaults_to_yesterday_and_gather_to_today(tmp_path, monkeypatch):
    vault, _, _ = _setup(tmp_path)
    monkeypatch.setattr(daily, "_today", lambda tz: date(2026, 10, 19))
    assert _week_args(tmp_path, vault).date == date(2026, 10, 18)
    gather = daily.parse_args(["gather", "--config", str(tmp_path / "none.json"), "--vault", str(vault)])
    assert gather.date == date(2026, 10, 19)


def test_week_main_prints_json(tmp_path, capsys):
    vault, _, _ = _setup(tmp_path)
    assert daily.main(["week", "--config", str(tmp_path / "none.json"), "--vault", str(vault),
                       "--date", "2026-10-14"]) == 0
    assert json.loads(capsys.readouterr().out)["week"] == "2026-W42"


def test_write_week_creates_the_weekly_note(tmp_path, capsys, monkeypatch):
    vault, _, _ = _setup(tmp_path)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"moved": ["a"], "blocked": [], "focus": ["b"]})))
    assert daily.main(["write", "--week", "--config", str(tmp_path / "none.json"),
                       "--date", "2026-10-14", "--vault", str(vault)]) == 0
    assert json.loads(capsys.readouterr().out) == {"old": {"moved": "", "blocked": "", "focus": ""}}
    text = (vault / "50 Journal" / "weekly" / "2026-W42.md").read_text(encoding="utf-8")
    assert text == (
        "# 2026-W42 (2026-10-12 to 2026-10-18)\n\n"
        "**Moved:**\n\n- a\n\n**Still blocked:**\n\n**Focus:**\n\n- b\n"
    )


def test_write_week_replaces_an_existing_weekly_note(tmp_path, capsys, monkeypatch):
    vault, _, _ = _setup(tmp_path)
    folder = vault / "50 Journal" / "weekly"
    folder.mkdir(parents=True)
    (folder / "2026-W42.md").write_text(WEEK, encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"moved": ["my bullet", "new"], "blocked": [], "focus": []})))
    assert daily.main(["write", "--week", "--config", str(tmp_path / "none.json"),
                       "--date", "2026-10-14", "--vault", str(vault)]) == 0
    assert json.loads(capsys.readouterr().out)["old"]["moved"] == "- my bullet"
    assert (folder / "2026-W42.md").read_text(encoding="utf-8").startswith(
        "# 2026-W42 (2026-10-12 to 2026-10-18)\n\n**Moved:**\n\n- my bullet\n- new\n")


def test_write_week_refuses_an_empty_moved_and_leaves_the_file(tmp_path, capsys, monkeypatch):
    vault, _, _ = _setup(tmp_path)
    folder = vault / "50 Journal" / "weekly"
    folder.mkdir(parents=True)
    (folder / "2026-W42.md").write_text(WEEK, encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"moved": [], "blocked": ["x"], "focus": []})))
    assert daily.main(["write", "--week", "--config", str(tmp_path / "none.json"),
                       "--date", "2026-10-14", "--vault", str(vault)]) == 1
    assert "moved section is empty" in capsys.readouterr().err
    assert (folder / "2026-W42.md").read_text(encoding="utf-8") == WEEK
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/pytest tests/test_daily.py -v`
Expected: the 7 new tests FAIL (`invalid choice: 'week'`, `unrecognized arguments: --week`, or no attribute `_today`); the old tests pass.

- [ ] **Step 3: Write the implementation in `src/daily.py`**

Add `import daily_week` to the flat imports (alphabetical, after `import daily_vault`).

Add after `_zone`:

```python
def _today(tz):
    return datetime.now(_zone(tz)).date()
```

Add after `gather`:

```python
def week(args):
    """The week's daily notes, the cards they name, and the weekly note's own text."""
    vault = Path(args.vault)
    days, errors = daily_week.read_days(vault, args.date, args.today, args.journal_dir)
    try:
        cards = daily_week.cards_named(daily_vault.load_cards(vault), days)
    except Exception as exc:
        errors["vault"] = f"{type(exc).__name__}: {exc}"
        cards = []
    path = daily_week.note_path(vault, args.date, args.weekly_dir)
    manual = {key: "" for key, _ in daily_note.WEEKLY}
    if path.exists():
        try:
            manual = daily_note.read_sections(path.read_text(encoding="utf-8"), daily_note.WEEKLY)
        except ValueError:
            pass
    start, end = daily_week.week_bounds(args.date)
    return {
        "week": daily_week.week_id(args.date),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "note_path": str(path),
        "manual": manual,
        "days": days,
        "cards": cards,
        "errors": errors,
    }
```

Replace `write` with:

```python
def write(args):
    try:
        sections = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"error: bad JSON on stdin: {exc}", file=sys.stderr)
        return 1
    if args.week:
        kind = daily_note.WEEKLY
        path = daily_week.note_path(args.vault, args.date, args.weekly_dir)
    else:
        kind = daily_note.DAILY
        path = daily_note.note_path(args.vault, args.date, args.journal_dir)
    if path.exists():
        text = path.read_text(encoding="utf-8")
    elif args.week:
        text = daily_week.blank(args.date)
    else:
        text = daily_note.from_template(args.vault, args.date, args.template)
    try:
        old = daily_note.read_sections(text, kind)
        new = daily_note.replace_sections(text, sections, kind)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"old": old}, ensure_ascii=False, indent=2))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new, encoding="utf-8")
    return 0
```

In `parse_args`, change the `--date` help to `"YYYY-MM-DD, default today (yesterday for week)"`, replace the `write` subparser line, and add the `week` subparser:

```python
    w = sub.add_parser("write", parents=[common], help="replace the note sections from JSON on stdin")
    w.add_argument("--week", action="store_true", help="write the weekly note of --date's week")
    sub.add_parser("week", parents=[common], help="print the week's daily notes as JSON")
```

In `resolve`, replace the date block and add `weekly_dir` and `today`:

```python
    args.journal_dir = cfg["journal_dir"]
    args.weekly_dir = cfg["weekly_dir"]
    args.template = cfg["template"]
    args.today = _today(args.tz)
    if args.date is None:
        args.date = args.today - timedelta(days=1) if args.command == "week" else args.today
```

In `main`, before `return write(args)`:

```python
    if args.command == "week":
        print(json.dumps(week(args), ensure_ascii=False, indent=2))
        return 0
```

`gather` and `week` subparsers have no `--week`, so `write` is the only reader of `args.week`.

- [ ] **Step 4: Run all tests**

Run: `just test`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/daily.py tests/test_daily.py
git commit -m "feat(week): add the week command and write --week"
```

```json:metadata
{"files": ["src/daily.py", "tests/test_daily.py"], "verifyCommand": ".venv/bin/pytest -v", "acceptanceCriteria": ["week prints week/start/end/note_path/manual/days/cards/errors", "manual from an existing weekly note", "week defaults to yesterday, gather to today", "write --week creates and replaces the weekly note", "empty moved exits 1 and leaves the file", "existing tests pass unchanged"], "modelTier": "standard"}
```

---

### Task 5: Skill text, docs and install

**Goal:** `/magpie week` works in Claude Code: the skill explains the weekly run, the docs mention it, and `just install` copies the new module.

**Files:**
- Modify: `skills/magpie/SKILL.md`
- Modify: `README.md`
- Modify: `CLAUDE.md`

**Acceptance Criteria:**
- [ ] The SKILL.md frontmatter `description` also triggers on "/magpie week" and "weekly note".
- [ ] SKILL.md has a "## Weekly run" section with the 4 steps of the spec, word for word on the rules (gap filling, the no-activity test, the three sections, the merge, the report).
- [ ] README.md has a short "Weekly note" paragraph under the usage part; CLAUDE.md names the new spec.
- [ ] After `just install`, `~/.claude/skills/magpie/daily_week.py` exists and `python3 ~/.claude/skills/magpie/daily.py week --date 2026-10-14` prints JSON with `"week": "2026-W42"`.
- [ ] `grep -nP '\x{2014}|\x{2013}' skills/magpie/SKILL.md README.md CLAUDE.md` finds nothing new.

**Verify:** `just test && just install && python3 ~/.claude/skills/magpie/daily.py week --date 2026-10-14 | head -5`

**Steps:**

- [ ] **Step 1: Change the frontmatter description of `skills/magpie/SKILL.md`** to:

```
description: Use when the user runs /magpie or /magpie week, or asks to pre-fill, draft or fill the daily note, the journal, or the weekly note for a day or a week. Gathers the day's vault logs, git commits, Claude Code sessions, ActivityWatch time, calendar events and sent mail, then writes a Did / Blocked / Next draft into the Obsidian daily note; the weekly run sums the week's daily notes into Moved / Still blocked / Focus.
```

- [ ] **Step 2: Add this section at the end of `skills/magpie/SKILL.md`**

````markdown
## Weekly run

`/magpie week` drafts the weekly note from the week's daily notes. `/magpie week
2026-10-14` takes the ISO week (Monday to Sunday) that holds that date. With no date,
the script takes the week that holds yesterday.

### Step W1: Read the week

```bash
python3 ~/.claude/skills/magpie/daily.py week [--date <YYYY-MM-DD>]
```

If `errors` is not empty, name each failed day or source in one line.

### Step W2: Fill the gaps

For each entry of `days` with `status` `missing`, do Steps 1 to 3 of the daily run for
that date. Skip Step 4 (the daily report). A day gets no note when its gather has no
groups, no activity row of 30 minutes or more, no calendar event and no sent mail:
remember the date for the report and go to the next day. A day with `status`
`unreadable` is never rewritten. When all gaps are done, run Step W1 again.

### Step W3: Draft

- **Moved:** one bullet per project or area, from the **Did:** bullets of the week.
  Start with the card's `link` from `cards`. State results, not each step. Work with no
  card keeps one short bullet.
- **Still blocked:** at most 3. Use a **Blocked:** bullet of the week only when no
  later daily note or card shows it as resolved. Add a card's `open_decisions` only when
  it holds up work.
- **Focus:** at most 3, plain text with links, never checkboxes. Take them from the
  `next_action` of the cards with the most work in the week and from the last **Next:**
  bullets.
- Merge `manual` as in the daily run: every fact in the user's bullets survives, and
  nothing appears twice.

### Step W4: Write and report

```bash
python3 ~/.claude/skills/magpie/daily.py write --week --date <YYYY-MM-DD> <<'EOF'
{"moved": ["..."], "blocked": ["..."], "focus": ["..."]}
EOF
```

`moved` must not be empty. If the command fails, show the error and stop. Then show the
weekly note as it is in the file, and one line: which days were filled, which had no
activity, and what changed compared with the old sections.
````

- [ ] **Step 3: README.md.** After the paragraph that starts "A magpie saw it all", add:

```markdown
`/magpie week` sums up a week. It fills any day of that week that has no daily note,
then writes **Moved:**, **Still blocked:** and **Focus:** into
`50 Journal/weekly/YYYY-Www.md` (set the folder with `weekly_dir`).
```

In the Configuration part, add `weekly_dir` (default `50 Journal/weekly`) to the list of keys, in the same format as `journal_dir`.

- [ ] **Step 4: CLAUDE.md.** Replace the first paragraph with:

```markdown
magpie: a Claude Code skill, `/magpie`, that drafts the Did / Blocked / Next sections of
an Obsidian daily note from the day's traceable work, and with `/magpie week` a weekly
note from the daily notes. Specs: `docs/superpowers/specs/2026-10-05-daily-journal-design.md`,
`docs/superpowers/specs/2026-10-19-weekly-journal-design.md`.
```

- [ ] **Step 5: Install and check**

Run: `just test && just install && python3 ~/.claude/skills/magpie/daily.py week --date 2026-10-14 | head -5`
Expected: tests pass; the JSON starts with `"week": "2026-W42"`.

Note: `~/.claude/skills/magpie` is a symlink to the repo folder that ran `just install`. In a worktree, that points the live skill at the worktree. That is fine until the merge; after the merge, run `just install` again from the main checkout.

- [ ] **Step 6: Commit**

```bash
git add skills/magpie/SKILL.md skills/magpie/*.py README.md CLAUDE.md
git commit -m "feat(skill): add the weekly run to /magpie"
```

```json:metadata
{"files": ["skills/magpie/SKILL.md", "README.md", "CLAUDE.md"], "verifyCommand": "just test && just install && python3 ~/.claude/skills/magpie/daily.py week --date 2026-10-14", "acceptanceCriteria": ["description triggers on /magpie week", "Weekly run section with steps W1 to W4", "README and CLAUDE.md updated", "installed daily.py week prints 2026-W42", "no em or en dash added"], "modelTier": "standard"}
```

---

### Task 6: Acceptance on the real vault

**Goal:** One real `/magpie week 2026-10-14` run produces `~/vault/50 Journal/weekly/2026-W42.md`.

**Files:**
- None in the repo. Writes `~/vault/50 Journal/weekly/2026-W42.md` (and a daily note for 2026-10-15 only if that day has activity).

**Acceptance Criteria:**
- [ ] `~/vault/50 Journal/weekly/2026-W42.md` exists, its first line is `# 2026-W42 (2026-10-12 to 2026-10-18)`, and **Moved:** is not empty.
- [ ] `grep -c '\- \[ \]' ~/vault/50\ Journal/weekly/2026-W42.md` prints 0 (no checkbox).
- [ ] The run report names 2026-10-15 as filled or as a day with no activity.
- [ ] No daily note of 2026-10-12 to 2026-10-18 lost a bullet: `diff` against the copy made in Step 0 shows no removed `- ` line. Never run git in the vault.

**Verify:** `head -1 ~/vault/50\ Journal/weekly/2026-W42.md && grep -c '\- \[ \]' ~/vault/50\ Journal/weekly/2026-W42.md`

**Steps:**

- [ ] **Step 0:** Copy the week's daily notes: `mkdir -p /tmp/w42 && cp ~/vault/50\ Journal/daily/2026-10-1[2-8].md /tmp/w42/`
- [ ] **Step 1:** In a Claude Code session in `~/vault`, run `/magpie week 2026-10-14` and follow the skill.
- [ ] **Step 2:** Run the Verify command. Expected: the title line, then `0`. Then run `for f in /tmp/w42/*.md; do diff "$f" ~/vault/50\ Journal/daily/$(basename "$f") | grep '^< - '; done`. Expected: no output.
- [ ] **Step 3:** Show the note to the user. No commit (the vault commits itself every 5 minutes; never run git writes in the vault).

```json:metadata
{"files": [], "verifyCommand": "head -1 ~/vault/50\\ Journal/weekly/2026-W42.md && grep -c '\\- \\[ \\]' ~/vault/50\\ Journal/weekly/2026-W42.md", "acceptanceCriteria": ["2026-W42.md exists with the title line and a non-empty Moved", "no checkbox in the weekly note", "2026-10-15 named as filled or no activity", "no daily note lost a bullet"], "modelTier": "standard"}
```
