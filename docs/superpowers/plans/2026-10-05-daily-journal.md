# Daily Journal Pre-fill (`/daily`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** magpie, a `/daily` Claude Code skill that drafts the Did / Blocked / Next sections of the Obsidian daily note from the day's traceable work.

**Architecture:** A standalone, open-source repo (`magpie`). Seven small stdlib modules in `src/` each gather one source (note sections, git, vault cards and logs, Claude Code sessions, ActivityWatch, sent mail, config). Personal values (time zone, folders, mail accounts, calendars, excluded domains) live in `~/.config/magpie/config.json`, never in the code. `src/daily.py` is the CLI: `gather` prints one JSON payload grouped by project card, `write` replaces the three note sections from JSON on stdin. The skill (`skills/daily/SKILL.md`) runs `gather`, reads the calendar through the Google Calendar MCP connector, drafts the bullets, and pipes them to `write`.

**Tech Stack:** Python 3.14 standard library only (`subprocess`, `urllib`, `imaplib`, `email`, `zoneinfo`), pytest, just.

**Global Constraints:**
- Spec: `docs/superpowers/specs/2026-10-05-daily-journal-design.md`. Read it before any task.
- Stdlib only at runtime. `pytest` is the only dev dependency.
- Flat imports (`import daily_git`, not `from src import daily_git`): `conftest.py` puts `src/` on `sys.path`.
- The repo will be public. No personal value (email address, calendar ID, path under a real home folder, time zone) in code, tests or skill text. Personal values go only in `~/.config/magpie/config.json`, which is outside the repo.
- `src/transcript.py` is a copy of `session_reviewer/src/transcript.py` plus `parse_ts` and `is_injected` (from its `digest.py` and `signals.py`). It is a copy on purpose: the two repos ship separately.
- Never modify or delete anything under `~/.claude/projects/`. It is read-only input.
- No em dashes anywhere: code, comments, skill text, generated bullets.
- `src/` is the source of truth. `skills/daily/*.py` are copies made by `just install` and are committed. Never edit the copies.
- The note sections are exactly `**Did:**`, `**Blocked:**`, `**Next:**`, in that order.
- The day is the local calendar day in the configured time zone (tests use `Europe/Paris`). Transcript timestamps are UTC and are compared as aware datetimes.
- Run tests with `just test` (it runs `.venv/bin/pytest -v`). If `.venv` is missing: `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`.
- The repo is `~/projects/personal/magpie`. Task 0 creates its base on `main`; Tasks 1 to 10 run in a Superset workspace for this repo, never in the main checkout.

**User decisions (already made):**
- "one bullet per project", with a wikilink to the project card.
- Manual bullets are merged: "the agent reads the bullet and rewrites with those in mind". Every fact survives.
- Blocked and Next are pre-filled too: "I'll edit it anyway and it can get the ball rolling".
- Own repo, separate from `session_reviewer`, so each can be open-sourced alone ("one aimed at making the Claude setup better, the other simply a daily update assistant"). The transcript parser is copied, not shared.
- Run by hand (`/daily`), not scheduled.
- Sources: vault logs, git commits, Claude Code sessions, ActivityWatch (window, AFK, Chrome web watcher), both Google calendars, sent mail headers on both accounts. No raw Chrome History file, no Screenpipe, no received mail.
- Both of the user's calendars are read by ID, from the config `calendars` list (share done 2026-10-05).

---

## File structure

| File | Responsibility |
|---|---|
| `src/daily_note.py` | Find, read and rewrite the three sections of a note; note path; template. |
| `src/daily_git.py` | Run git, repo names from remote URLs, find repos, the day's commit subjects. |
| `src/daily_vault.py` | Project and area cards (link, repos, next action, open decisions); the day's logs. |
| `src/daily_sessions.py` | The day's Claude Code sessions, compacted; covered and `/daily` sessions dropped. |
| `src/daily_aw.py` | ActivityWatch REST reads and the noise and privacy filters. |
| `src/daily_mail.py` | Sent mail headers over IMAP, Keychain passwords. |
| `src/daily_config.py` | Load `~/.config/magpie/config.json` over the defaults. |
| `src/transcript.py` | Claude Code `.jsonl` parser, `parse_ts`, `is_injected` (copied from session_reviewer). |
| `src/daily.py` | CLI: `gather` (assemble, group by card, size cap) and `write`. |
| `skills/daily/SKILL.md` | The reasoning steps Claude follows for `/daily`. |
| `tests/test_daily_*.py`, `tests/test_daily.py` | One test file per module. |
| `justfile` | `help`, `test`, `install` (copies `src/*.py` into `skills/daily/`, symlinks `~/.claude/skills/daily`). |
| `README.md`, `CLAUDE.md`, `LICENSE` | Public docs, agent guide, MIT license. |

---

### Task 0: Repo base and transcript parser

**Goal:** A working repo on `main` with the copied transcript parser, its tests, and `just test` green.

**Files:**
- Already present (copied 2026-10-05): `LICENSE`, `conftest.py`, `requirements-dev.txt`, `docs/superpowers/`
- Create: `src/transcript.py`, `tests/test_transcript.py`, `tests/fixtures/basic.jsonl`, `tests/fixtures/blocks.jsonl` (copies)
- Create: `.gitignore`, `justfile`, `CLAUDE.md`

**Acceptance Criteria:**
- [ ] `src/transcript.py` has the session_reviewer functions plus `parse_ts` and `is_injected`.
- [ ] `just test` passes.
- [ ] `git log` on `main` shows the base commit.

**Verify:** `just test` → all passed

**Steps:**

- [ ] **Step 1: Copy the parser, its tests and fixtures**

```bash
O=~/projects/personal/session_reviewer
cp $O/src/transcript.py src/
cp $O/tests/test_transcript.py tests/
mkdir -p tests/fixtures && cp $O/tests/fixtures/basic.jsonl $O/tests/fixtures/blocks.jsonl tests/fixtures/
```

- [ ] **Step 2: Write the failing tests for the two new functions**

Append to `tests/test_transcript.py`:

```python
from datetime import datetime, timezone


def test_parse_ts_handles_z_and_bad_input():
    assert transcript.parse_ts("2026-07-01T09:00:00.000Z") == datetime(2026, 7, 1, 9, tzinfo=timezone.utc)
    assert transcript.parse_ts("") is None
    assert transcript.parse_ts("garbage") is None


def test_is_injected_flags_harness_text_only():
    assert transcript.is_injected("<command-name>/clear</command-name>")
    assert transcript.is_injected("Base directory for this skill: /x")
    assert not transcript.is_injected("fix the parser")
```

Run: `python3 -m venv .venv && .venv/bin/pip install -q -r requirements-dev.txt && .venv/bin/pytest tests/test_transcript.py -v`
Expected: the 2 new tests FAIL with `AttributeError`, the copied tests pass.

- [ ] **Step 3: Add the two functions**

Prepend after `import json` at the top of `src/transcript.py`:

```python
from datetime import datetime

# Markers of harness- or skill-injected user text (copied from session_reviewer's signals.py).
_INJECTION_MARKERS = [
    "Base directory for this skill:",
    "<task-notification>",
    "<command-name>",
    "<command-message>",
    "<local-command-stdout>",
    "Caveat: The messages below",
    "[Request interrupted by user",
]


def parse_ts(value):
    """Parse an ISO8601 timestamp (trailing 'Z' allowed) to an aware datetime, or None."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def is_injected(text):
    """True if this user text was injected by the harness or a skill, not typed."""
    return any(marker in text for marker in _INJECTION_MARKERS)
```

- [ ] **Step 4: Base files**

`.gitignore`:

```gitignore
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.DS_Store
```

`justfile`:

```just
# List the recipes
help:
    @just --list

# Run the test suite
test:
    .venv/bin/pytest -v
```

`CLAUDE.md`:

```markdown
# CLAUDE.md

A Claude Code skill, `/daily`, that drafts the Did / Blocked / Next sections of an
Obsidian daily note from the day's traceable work. Spec:
`docs/superpowers/specs/2026-10-05-daily-journal-design.md`.

## Commands

    just test       # full suite (.venv/bin/pytest -v)
    just install    # copy src/*.py into skills/daily/ and symlink ~/.claude/skills/daily

Stdlib only at runtime; `pytest` is the only dev dependency. Imports are flat
(`import daily_git`) because `conftest.py` puts `src/` on `sys.path`.

## Rules

- This repo is public. No personal value in code, tests or skill text: they go in
  `~/.config/magpie/config.json`.
- `src/` is the source of truth; `skills/daily/*.py` are copies made by `just install`.
- Never modify anything under `~/.claude/projects/`. It is read-only input.
- TDD, one test file per module. No em dashes anywhere.
```

- [ ] **Step 5: Run the tests**

Run: `just test`
Expected: all passed.

- [ ] **Step 6: Commit on main**

```bash
git add .gitignore justfile CLAUDE.md LICENSE conftest.py requirements-dev.txt src tests docs
git commit -m "chore: repo base with the transcript parser copied from session_reviewer"
```

---

### Task 1: Note sections (`daily_note.py`)

**Goal:** Read and rewrite the Did / Blocked / Next sections of a daily note without touching the title.

**Files:**
- Create: `src/daily_note.py`
- Test: `tests/test_daily_note.py`

**Acceptance Criteria:**
- [ ] `read_sections` returns the stripped text of each section, and raises `ValueError` naming a missing marker.
- [ ] `replace_sections` renders each list with a blank line after it, writes a marker alone for an empty list, keeps everything above `**Did:**` byte for byte, and raises `ValueError("did section is empty")` for an empty `did`.
- [ ] `from_template` replaces `{{date:YYYY-MM-DD}}`; `note_path` points to `50 Journal/daily/<date>.md`.

**Verify:** `.venv/bin/pytest tests/test_daily_note.py -v` → 7 passed

**Steps:**

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_daily_note.py
from datetime import date

import pytest

import daily_note

TEMPLATE = "# {{date:YYYY-MM-DD}}\n\n**Did:** \n**Blocked:** \n**Next:** \n"
NOTE = "# 2026-10-05\n\n**Did:** \n\n- set up the vault\n- inbox zero\n**Blocked:** \n**Next:** \n"


def test_read_sections_strips_each_section():
    assert daily_note.read_sections(NOTE) == {
        "did": "- set up the vault\n- inbox zero",
        "blocked": "",
        "next": "",
    }


def test_read_sections_refuses_a_missing_marker():
    with pytest.raises(ValueError, match="Next"):
        daily_note.read_sections("# x\n\n**Did:** \n**Blocked:** \n")


def test_replace_sections_renders_all_three_and_keeps_the_title():
    out = daily_note.replace_sections(NOTE, {"did": ["a", "b"], "blocked": [], "next": ["x"]})
    assert out == "# 2026-10-05\n\n**Did:**\n\n- a\n- b\n\n**Blocked:**\n\n**Next:**\n\n- x\n"


def test_replace_sections_strips_a_leading_dash():
    out = daily_note.replace_sections(NOTE, {"did": ["- a"], "blocked": [], "next": []})
    assert "\n- a\n" in out
    assert "- - a" not in out


def test_replace_sections_refuses_an_empty_did():
    with pytest.raises(ValueError, match="did section is empty"):
        daily_note.replace_sections(NOTE, {"did": [], "blocked": ["x"], "next": []})


def test_from_template_fills_the_date(tmp_path):
    (tmp_path / "90 Templates").mkdir()
    (tmp_path / "90 Templates" / "daily.md").write_text(TEMPLATE, encoding="utf-8")
    assert daily_note.from_template(tmp_path, date(2026, 10, 5)).startswith("# 2026-10-05\n")


def test_note_path(tmp_path):
    expected = tmp_path / "50 Journal" / "daily" / "2026-10-05.md"
    assert daily_note.note_path(tmp_path, date(2026, 10, 5)) == expected
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `.venv/bin/pytest tests/test_daily_note.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'daily_note'`

- [ ] **Step 3: Write the module**

```python
# src/daily_note.py
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
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `.venv/bin/pytest tests/test_daily_note.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/daily_note.py tests/test_daily_note.py
git commit -m "feat(daily): read and rewrite the daily note sections"
```

---

### Task 2: Git facts (`daily_git.py`)

**Goal:** Find local repos, name them from their `origin` URL, and list one author's commit subjects for a day.

**Files:**
- Create: `src/daily_git.py`
- Test: `tests/test_daily_git.py`

**Acceptance Criteria:**
- [ ] `repo_name` handles https, ssh, trailing slash, `.git` suffix and a trailing newline.
- [ ] `find_repos` returns the folders with a `.git` under the root, then the extra repos that exist.
- [ ] `commits_for_day` returns subjects newest first, only inside `[start, end)`, only for the given author, and `None` when git fails.
- [ ] `origin_name` returns `None` for a repo with no `origin`.

**Verify:** `.venv/bin/pytest tests/test_daily_git.py -v` → 5 passed

**Steps:**

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_daily_git.py
import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

import daily_git

PARIS = ZoneInfo("Europe/Paris")
START = datetime(2026, 10, 5, tzinfo=PARIS)
END = datetime(2026, 10, 6, tzinfo=PARIS)


def _git(repo, *args, env=None):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


def _repo(path, origin="https://github.com/me/alpha.git"):
    path.mkdir()
    _git(path, "init", "-q", "-b", "main")
    if origin:
        _git(path, "remote", "add", "origin", origin)
    return path


def _commit(repo, message, when, email="me@x.com"):
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Me",
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": "Me",
        "GIT_COMMITTER_EMAIL": email,
        "GIT_AUTHOR_DATE": when,
        "GIT_COMMITTER_DATE": when,
    }
    _git(repo, "-c", "commit.gpgsign=false", "commit", "--allow-empty", "--no-verify",
         "-q", "-m", message, env=env)


def test_repo_name_handles_https_ssh_and_git_suffix():
    assert daily_git.repo_name("https://github.com/me/alpha.git\n") == "alpha"
    assert daily_git.repo_name("git@github.com:me/beta.git") == "beta"
    assert daily_git.repo_name("https://github.com/me/gamma/") == "gamma"


def test_find_repos_lists_git_folders_then_extras(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    alpha = _repo(root / "alpha")
    (root / "notes").mkdir()
    dot = _repo(tmp_path / "dot", origin=None)
    assert daily_git.find_repos(root, [dot, tmp_path / "missing"]) == [alpha, dot]


def test_commits_for_day_filters_the_day_and_the_author(tmp_path):
    repo = _repo(tmp_path / "alpha")
    _commit(repo, "before", "2026-10-04T23:30:00+02:00")
    _commit(repo, "on the day", "2026-10-05T10:00:00+02:00")
    _commit(repo, "late on the day", "2026-10-05T23:30:00+02:00")
    _commit(repo, "someone else", "2026-10-05T11:00:00+02:00", email="other@x.com")
    _commit(repo, "after", "2026-10-06T00:30:00+02:00")
    assert daily_git.commits_for_day(repo, START, END, "me@x.com") == [
        "late on the day",
        "on the day",
    ]


def test_commits_for_day_returns_none_when_git_fails(tmp_path):
    assert daily_git.commits_for_day(tmp_path / "nope", START, END, "me@x.com") is None


def test_origin_name(tmp_path):
    assert daily_git.origin_name(_repo(tmp_path / "alpha")) == "alpha"
    assert daily_git.origin_name(_repo(tmp_path / "bare", origin=None)) is None
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `.venv/bin/pytest tests/test_daily_git.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'daily_git'`

- [ ] **Step 3: Write the module**

```python
# src/daily_git.py
"""Local git facts for the daily note: repos, origin names, and the day's commits."""
import subprocess
from pathlib import Path


def run_git(repo, *args):
    """Run git in `repo`. Return stdout, or None when git fails or is missing."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=20
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def repo_name(url):
    """'https://github.com/me/alpha.git' and 'git@github.com:me/alpha' both give 'alpha'."""
    tail = url.strip().rstrip("/").split("/")[-1].split(":")[-1]
    return tail.removesuffix(".git")


def origin_name(path):
    out = run_git(path, "remote", "get-url", "origin")
    return repo_name(out) if out and out.strip() else None


def find_repos(root, extra=()):
    root = Path(root)
    repos = [p for p in sorted(root.iterdir()) if (p / ".git").exists()] if root.is_dir() else []
    return repos + [Path(e) for e in extra if (Path(e) / ".git").exists()]


def author_email():
    out = run_git(Path.home(), "config", "--global", "user.email")
    return out.strip() if out and out.strip() else None


def commits_for_day(repo, start, end, author):
    """Subjects of `author`'s commits in [start, end), newest first. None if git fails.

    `--all` covers branches made in Superset workspaces, because a worktree shares
    the main clone's refs. The stash is excluded: its commits are not work.
    """
    out = run_git(
        repo, "log", "--exclude=refs/stash", "--all",
        f"--since={start.isoformat()}", f"--until={end.isoformat()}",
        f"--author={author}", "--format=%s",
    )
    if out is None:
        return None
    return list(dict.fromkeys(line for line in out.splitlines() if line.strip()))
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `.venv/bin/pytest tests/test_daily_git.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/daily_git.py tests/test_daily_git.py
git commit -m "feat(daily): list the day's commits in local repos"
```

---

### Task 3: Vault cards and logs (`daily_vault.py`)

**Goal:** Read every project and area card (link, repos, next action, open decisions) and the day's log files.

**Files:**
- Create: `src/daily_vault.py`
- Test: `tests/test_daily_vault.py`

**Acceptance Criteria:**
- [ ] A project card gives `[[10 Projects/<name>/_project|<name>]]`, an area card `[[20 Areas/<name>/_area|<name>]]`.
- [ ] A comma-separated `repo:` line gives a list of repo names.
- [ ] A missing `**Next action:**` or `**Open decisions:**` line gives `None`.
- [ ] `logs_for_day` maps a card name to its `log/<date>.md` text, and returns `{}` when no log exists.

**Verify:** `.venv/bin/pytest tests/test_daily_vault.py -v` → 2 passed

**Steps:**

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_daily_vault.py
from datetime import date

import daily_vault

PROJECT_CARD = (
    "---\nstatus: active\nrepo: https://github.com/me/vault\n---\n# Vault setup\n"
    "**Next action:** rewrite the finance notes.\n**Open decisions:** none.\n"
)
AREA_CARD = (
    "---\ntype: area\nrepo: https://github.com/me/alpha, https://github.com/me/beta.git\n"
    "---\n# Learning\n**Current goals:** code.\n"
)


def _vault(tmp_path):
    project = tmp_path / "10 Projects" / "vault-setup"
    (project / "log").mkdir(parents=True)
    (project / "_project.md").write_text(PROJECT_CARD, encoding="utf-8")
    (project / "log" / "2026-10-05.md").write_text("# 2026-10-05\n\nWrote the spec.\n", encoding="utf-8")
    area = tmp_path / "20 Areas" / "learning"
    area.mkdir(parents=True)
    (area / "_area.md").write_text(AREA_CARD, encoding="utf-8")
    return tmp_path


def test_load_cards_reads_links_repos_and_fields(tmp_path):
    cards = daily_vault.load_cards(_vault(tmp_path))
    assert [c["name"] for c in cards] == ["vault-setup", "learning"]
    project, area = cards
    assert project["link"] == "[[10 Projects/vault-setup/_project|vault-setup]]"
    assert project["repos"] == ["vault"]
    assert project["next_action"] == "rewrite the finance notes."
    assert project["open_decisions"] == "none."
    assert area["link"] == "[[20 Areas/learning/_area|learning]]"
    assert area["repos"] == ["alpha", "beta"]
    assert area["next_action"] is None


def test_logs_for_day_maps_a_card_to_its_log_text(tmp_path):
    cards = daily_vault.load_cards(_vault(tmp_path))
    assert daily_vault.logs_for_day(cards, date(2026, 10, 5)) == {
        "vault-setup": ["# 2026-10-05\n\nWrote the spec.\n"]
    }
    assert daily_vault.logs_for_day(cards, date(2026, 10, 4)) == {}
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `.venv/bin/pytest tests/test_daily_vault.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'daily_vault'`

- [ ] **Step 3: Write the module**

```python
# src/daily_vault.py
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
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `.venv/bin/pytest tests/test_daily_vault.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/daily_vault.py tests/test_daily_vault.py
git commit -m "feat(daily): read vault cards and the day's logs"
```

---

### Task 4: The day's sessions (`daily_sessions.py`)

**Goal:** Compact each Claude Code session of the day to its working directory, its human turns and its last reply, and drop covered sessions, `/daily` runs and subagents.

**Files:**
- Create: `src/daily_sessions.py`
- Test: `tests/test_daily_sessions.py`

**Acceptance Criteria:**
- [ ] Only records inside `[start, end)` count; a UTC record at 22:30 on the previous day counts for the Paris day.
- [ ] Injected text (`transcript.is_injected`) is not a turn. At most 8 turns, each cut to 300 chars. The last reply is cut to 500 chars.
- [ ] A session with a `Write` or `Edit` on `<vault>/(10 Projects|20 Areas)/<name>/log/<date>.md` goes to `covered`, by id only. A log for another date does not cover.
- [ ] A session with `<command-name>/daily</command-name>` is dropped. Paths with `subagents` are skipped.

**Verify:** `.venv/bin/pytest tests/test_daily_sessions.py -v` → 5 passed

**Steps:**

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_daily_sessions.py
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import daily_sessions

PARIS = ZoneInfo("Europe/Paris")
START = datetime(2026, 10, 5, tzinfo=PARIS)
END = datetime(2026, 10, 6, tzinfo=PARIS)
VAULT = "/v"


def _user(ts, text, cwd="/w/alpha"):
    return {"type": "user", "timestamp": ts, "cwd": cwd, "message": {"content": text}}


def _assistant(ts, *blocks):
    return {"type": "assistant", "timestamp": ts, "message": {"content": list(blocks)}}


def _write(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def test_keeps_the_day_turns_and_the_last_reply(tmp_path):
    _write(tmp_path / "p" / "s1.jsonl", [
        _user("2026-10-04T21:30:00Z", "yesterday at 23:30 Paris"),
        _user("2026-10-04T22:30:00Z", "fix the parser"),
        _user("2026-10-05T08:00:00Z", "<command-name>/clear</command-name>"),
        _assistant("2026-10-05T08:01:00Z", {"type": "text", "text": "First reply"}),
        _assistant("2026-10-05T09:00:00Z", {"type": "text", "text": "Parser fixed, tests pass."}),
    ])
    sessions, covered = daily_sessions.sessions_for_day(tmp_path, START, END, VAULT)
    assert covered == []
    assert sessions == [{
        "id": "s1",
        "cwd": "/w/alpha",
        "turns": ["fix the parser"],
        "last_reply": "Parser fixed, tests pass.",
    }]


def test_a_session_that_wrote_a_vault_log_is_covered(tmp_path):
    _write(tmp_path / "p" / "s2.jsonl", [
        _user("2026-10-05T10:00:00Z", "log this"),
        _assistant("2026-10-05T10:01:00Z", {
            "type": "tool_use", "name": "Write",
            "input": {"file_path": "/v/10 Projects/vault-setup/log/2026-10-05.md"},
        }),
    ])
    assert daily_sessions.sessions_for_day(tmp_path, START, END, VAULT) == ([], ["s2"])


def test_a_log_for_another_day_does_not_cover(tmp_path):
    _write(tmp_path / "p" / "s3.jsonl", [
        _user("2026-10-05T10:00:00Z", "log this"),
        _assistant("2026-10-05T10:01:00Z", {
            "type": "tool_use", "name": "Edit",
            "input": {"file_path": "/v/20 Areas/homelab/log/2026-10-04.md"},
        }),
    ])
    sessions, covered = daily_sessions.sessions_for_day(tmp_path, START, END, VAULT)
    assert covered == []
    assert [s["id"] for s in sessions] == ["s3"]


def test_daily_runs_subagents_and_other_days_are_dropped(tmp_path):
    _write(tmp_path / "p" / "d.jsonl", [
        _user("2026-10-05T18:00:00Z",
              "<command-message>daily</command-message>\n<command-name>/daily</command-name>"),
    ])
    _write(tmp_path / "p" / "s9" / "subagents" / "a.jsonl", [_user("2026-10-05T10:00:00Z", "sub work")])
    _write(tmp_path / "p" / "old.jsonl", [_user("2026-10-03T10:00:00Z", "old work")])
    assert daily_sessions.sessions_for_day(tmp_path, START, END, VAULT) == ([], [])


def test_turns_are_cut_and_capped(tmp_path):
    _write(tmp_path / "p" / "s4.jsonl",
           [_user(f"2026-10-05T10:{i:02d}:00Z", "x" * 400) for i in range(10)])
    (session,), _ = daily_sessions.sessions_for_day(tmp_path, START, END, VAULT)
    assert len(session["turns"]) == 8
    assert all(len(turn) == 300 for turn in session["turns"])
    assert session["last_reply"] is None
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `.venv/bin/pytest tests/test_daily_sessions.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'daily_sessions'`

- [ ] **Step 3: Write the module**

```python
# src/daily_sessions.py
"""Claude Code sessions of one day, compacted for the daily note."""
import re
from pathlib import Path

import transcript

MAX_TURNS = 8
TURN_CHARS = 300
REPLY_CHARS = 500
DAILY_MARKER = "<command-name>/daily</command-name>"


def _log_pattern(vault, day):
    return re.compile(
        re.escape(str(vault)) + r"/(10 Projects|20 Areas)/[^/]+/log/"
        + re.escape(day.isoformat()) + r"\.md$"
    )


def _read(path, start, end, log_re):
    info = {"id": path.stem, "cwd": None, "turns": [], "last_reply": None,
            "covered": False, "is_daily": False}
    seen = False
    for record in transcript.iter_records(path):
        if info["cwd"] is None and record.get("cwd"):
            info["cwd"] = record["cwd"]
        moment = transcript.parse_ts(record.get("timestamp"))
        if moment is None or not start <= moment < end:
            continue
        seen = True
        if transcript.is_human_turn(record):
            text = transcript.human_text(record).strip()
            if DAILY_MARKER in text or text.startswith("/daily"):
                info["is_daily"] = True
            elif text and not transcript.is_injected(text) and len(info["turns"]) < MAX_TURNS:
                info["turns"].append(text[:TURN_CHARS])
        for block in transcript.assistant_blocks(record):
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and block.get("text", "").strip():
                info["last_reply"] = block["text"].strip()[:REPLY_CHARS]
            elif block.get("type") == "tool_use" and block.get("name") in ("Write", "Edit"):
                target = str((block.get("input") or {}).get("file_path", ""))
                if log_re.search(target):
                    info["covered"] = True
    return info if seen else None


def sessions_for_day(projects_dir, start, end, vault):
    """Return (sessions, covered_ids) for the day [start, end).

    A covered session wrote that day's vault log, so the log already describes it.
    A /daily session is this tool itself, not work. Subagent transcripts are
    sidechains, not the user's sessions.
    """
    log_re = _log_pattern(vault, start.date())
    sessions, covered = [], []
    for path in sorted(Path(projects_dir).glob("**/*.jsonl")):
        if "subagents" in path.parts:
            continue
        info = _read(path, start, end, log_re)
        if info is None or info["is_daily"]:
            continue
        if info["covered"]:
            covered.append(info["id"])
            continue
        sessions.append({key: info[key] for key in ("id", "cwd", "turns", "last_reply")})
    return sessions, covered
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `.venv/bin/pytest tests/test_daily_sessions.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/daily_sessions.py tests/test_daily_sessions.py
git commit -m "feat(daily): compact the day's Claude Code sessions"
```

---

### Task 5: ActivityWatch (`daily_aw.py`)

**Goal:** Read the window, AFK and Chrome web buckets from the local ActivityWatch API and reduce them to at most 20 filtered rows of active time.

**Files:**
- Create: `src/daily_aw.py`
- Test: `tests/test_daily_aw.py`

**Acceptance Criteria:**
- [ ] Only time that overlaps a `not-afk` interval counts.
- [ ] Groups under 2 minutes are dropped; the top `top` (default 20) by time are kept.
- [ ] Web rows show the domain only, never the full URL. Domains in the exclude set, and their subdomains, are dropped. Chrome window rows are dropped when web events exist.
- [ ] No server gives `(None, "unavailable")`; a missing web bucket (404) gives no web rows.

**Verify:** `.venv/bin/pytest tests/test_daily_aw.py -v` → 5 passed

**Steps:**

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_daily_aw.py
import json
import socket
import threading
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo

import pytest

import daily_aw

PARIS = ZoneInfo("Europe/Paris")
START = datetime(2026, 10, 5, tzinfo=PARIS)
END = datetime(2026, 10, 6, tzinfo=PARIS)


def _ev(ts, seconds, **data):
    return {"timestamp": ts, "duration": seconds, "data": data}


AFK = [
    _ev("2026-10-05T08:00:00+00:00", 3600, status="not-afk"),
    _ev("2026-10-05T09:00:00+00:00", 3600, status="afk"),
]


def test_summarize_counts_only_active_time():
    window = [_ev("2026-10-05T08:30:00+00:00", 3600, app="Code", title="daily.py")]
    assert daily_aw.summarize(window, AFK, [], set()) == [
        {"kind": "app", "name": "Code", "title": "daily.py", "minutes": 30}
    ]


def test_summarize_drops_groups_under_two_minutes_and_keeps_top_n():
    window = [
        _ev("2026-10-05T08:00:00+00:00", 90, app="Tiny", title="t"),
        _ev("2026-10-05T08:05:00+00:00", 600, app="A", title="a"),
        _ev("2026-10-05T08:20:00+00:00", 300, app="B", title="b"),
        _ev("2026-10-05T08:30:00+00:00", 180, app="C", title="c"),
    ]
    rows = daily_aw.summarize(window, AFK, [], set(), top=2)
    assert [(r["name"], r["minutes"]) for r in rows] == [("A", 10), ("B", 5)]


def test_summarize_web_shows_domains_only_and_applies_the_exclude_list():
    web = [
        _ev("2026-10-05T08:00:00+00:00", 600, url="https://github.com/me/alpha/pull/3?x=1", title="PR 3"),
        _ev("2026-10-05T08:10:00+00:00", 600, url="https://www.mybank.fr/account", title="Balance"),
    ]
    window = [_ev("2026-10-05T08:00:00+00:00", 1200, app="Google Chrome", title="PR 3")]
    assert daily_aw.summarize(window, AFK, web, {"mybank.fr"}) == [
        {"kind": "web", "name": "github.com", "title": "PR 3", "minutes": 10}
    ]


class _Handler(BaseHTTPRequestHandler):
    routes = {}

    def do_GET(self):
        body = self.routes.get(urllib.parse.urlsplit(self.path).path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def aw_url():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/api/0"
    server.shutdown()
    server.server_close()


def test_gather_activity_reads_the_buckets(aw_url):
    _Handler.routes = {
        "/api/0/buckets/aw-watcher-window_host1/events":
            [_ev("2026-10-05T08:00:00+00:00", 600, app="Code", title="x")],
        "/api/0/buckets/aw-watcher-afk_host1/events": AFK,
    }
    rows, status = daily_aw.gather_activity(aw_url, "host1", START, END, set())
    assert status == "ok"
    assert rows == [{"kind": "app", "name": "Code", "title": "x", "minutes": 10}]


def test_gather_activity_without_a_server_is_unavailable():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    url = f"http://127.0.0.1:{port}/api/0"
    assert daily_aw.gather_activity(url, "h", START, END, set()) == (None, "unavailable")
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `.venv/bin/pytest tests/test_daily_aw.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'daily_aw'`

- [ ] **Step 3: Write the module**

```python
# src/daily_aw.py
"""ActivityWatch time for the daily note: active app, window and web time, filtered."""
import collections
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta

from transcript import parse_ts

BROWSER_APPS = {"Google Chrome"}
MIN_MINUTES = 2
TOP = 20
TITLE_CHARS = 100


def _excluded(domain, exclude):
    return any(domain == d or domain.endswith("." + d) for d in exclude)


def _span(event):
    begin = parse_ts(event["timestamp"])
    return begin, begin + timedelta(seconds=event["duration"])


def _active_seconds(event, active):
    begin, finish = _span(event)
    total = 0.0
    for low, high in active:
        overlap = (min(finish, high) - max(begin, low)).total_seconds()
        if overlap > 0:
            total += overlap
    return total


def summarize(window, afk, web, exclude, min_minutes=MIN_MINUTES, top=TOP):
    """Rows of active time grouped by app plus title, and by domain plus page title.

    Chrome window rows are dropped when web rows exist: the web rows carry the
    same time with a domain, and the exclude list can only filter domains.
    """
    active = [_span(e) for e in afk if e["data"].get("status") == "not-afk"]
    seconds = collections.Counter()
    for event in window:
        app = event["data"].get("app", "")
        if web and app in BROWSER_APPS:
            continue
        title = (event["data"].get("title") or "")[:TITLE_CHARS]
        seconds[("app", app, title)] += _active_seconds(event, active)
    for event in web:
        domain = (urllib.parse.urlsplit(event["data"].get("url", "")).hostname or "").lower()
        if not domain or _excluded(domain, exclude):
            continue
        title = (event["data"].get("title") or "")[:TITLE_CHARS]
        seconds[("web", domain, title)] += _active_seconds(event, active)
    kept = sorted(
        ((total, key) for key, total in seconds.items() if total >= min_minutes * 60),
        key=lambda pair: -pair[0],
    )
    return [
        {"kind": kind, "name": name, "title": title, "minutes": round(total / 60)}
        for total, (kind, name, title) in kept[:top]
    ]


def _fetch(base, bucket, start, end, timeout):
    query = urllib.parse.urlencode({"start": start.isoformat(), "end": end.isoformat(), "limit": -1})
    url = f"{base}/buckets/{urllib.parse.quote(bucket)}/events?{query}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.load(response)
    except (urllib.error.URLError, OSError, ValueError):
        return None


def gather_activity(base, host, start, end, exclude, timeout=2.0):
    """Return (rows, "ok"), or (None, "unavailable") when the server does not answer."""
    window = _fetch(base, f"aw-watcher-window_{host}", start, end, timeout)
    afk = _fetch(base, f"aw-watcher-afk_{host}", start, end, timeout)
    if window is None or afk is None:
        return None, "unavailable"
    web = _fetch(base, f"aw-watcher-web-chrome_{host}", start, end, timeout) or []
    return summarize(window, afk, web, exclude), "ok"
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `.venv/bin/pytest tests/test_daily_aw.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/daily_aw.py tests/test_daily_aw.py
git commit -m "feat(daily): summarize ActivityWatch time with noise and privacy filters"
```

---

### Task 6: Sent mail (`daily_mail.py`)

**Goal:** Read the day's sent mail headers (recipient names, subject) over IMAP for each account, never the body.

**Files:**
- Create: `src/daily_mail.py`
- Test: `tests/test_daily_mail.py`

**Acceptance Criteria:**
- [ ] The sent folder is found by its `\Sent` flag, so a French Gmail label works, and is selected read-only.
- [ ] The search is `SINCE <day> BEFORE <day+1>` in IMAP date format (`05-Oct-2026`).
- [ ] The fetch spec is exactly `(BODY.PEEK[HEADER.FIELDS (DATE TO SUBJECT)])`.
- [ ] Encoded subjects are decoded; a recipient with no display name shows the local part of the address.
- [ ] `gather_mail` sets one status per account (`ok`, `no password`, `error: imap`, `error: network`, `no sent folder`) and never raises.
- [ ] `keychain_password` calls `security find-generic-password -s daily-imap -a <address> -w`.

**Verify:** `.venv/bin/pytest tests/test_daily_mail.py -v` → 6 passed

**Steps:**

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_daily_mail.py
import subprocess
from datetime import date

import daily_mail

HEADERS = (
    b"Date: Mon, 05 Oct 2026 10:00:00 +0200\r\n"
    b"To: Abby Smith <abby@x.com>, bob@y.com\r\n"
    b"Subject: =?utf-8?q?Facture_d=C3=A9cembre?=\r\n\r\n"
)
GMAIL_FOLDERS = [
    b'(\\HasNoChildren) "/" "INBOX"',
    b'(\\HasNoChildren \\Sent) "/" "[Gmail]/Messages envoy&AOk-s"',
]
DAY = date(2026, 10, 5)


class FakeIMAP:
    def __init__(self, folders, ids=b"1"):
        self.folders = folders
        self.ids = ids
        self.calls = []

    def list(self):
        return "OK", self.folders

    def select(self, mailbox, readonly=False):
        self.calls.append(("select", mailbox, readonly))
        return "OK", [b"1"]

    def search(self, charset, *criteria):
        self.calls.append(("search", criteria))
        return "OK", [self.ids]

    def fetch(self, ids, spec):
        self.calls.append(("fetch", ids, spec))
        return "OK", [(b"1 (BODY[HEADER.FIELDS (DATE TO SUBJECT)] {120}", HEADERS), b")"]

    def logout(self):
        self.calls.append(("logout",))


def test_sent_for_day_reads_headers_only():
    conn = FakeIMAP(GMAIL_FOLDERS)
    assert daily_mail.sent_for_day(conn, DAY) == [{"to": "Abby Smith, bob", "subject": "Facture décembre"}]
    assert ("select", '"[Gmail]/Messages envoy&AOk-s"', True) in conn.calls
    assert ("search", ("SINCE", "05-Oct-2026", "BEFORE", "06-Oct-2026")) in conn.calls
    fetch = next(call for call in conn.calls if call[0] == "fetch")
    assert fetch[2] == "(BODY.PEEK[HEADER.FIELDS (DATE TO SUBJECT)])"


def test_sent_for_day_without_a_sent_folder_returns_none():
    assert daily_mail.sent_for_day(FakeIMAP([b'(\\HasNoChildren) "/" "INBOX"']), DAY) is None


def test_sent_for_day_with_no_mail_returns_empty():
    assert daily_mail.sent_for_day(FakeIMAP(GMAIL_FOLDERS, ids=b""), DAY) == []


def test_gather_mail_reports_a_status_per_account():
    rows, status = daily_mail.gather_mail(
        ["a@x.com", "b@x.com"], DAY,
        password_fn=lambda address: "pw" if address == "a@x.com" else None,
        connect=lambda address, password: FakeIMAP(GMAIL_FOLDERS),
    )
    assert status == {"a@x.com": "ok", "b@x.com": "no password"}
    assert rows == [{"account": "a@x.com", "to": "Abby Smith, bob", "subject": "Facture décembre"}]


def test_gather_mail_survives_a_login_error():
    def connect(address, password):
        raise daily_mail.imaplib.IMAP4.error("AUTHENTICATIONFAILED")

    rows, status = daily_mail.gather_mail(["a@x.com"], DAY, password_fn=lambda a: "pw", connect=connect)
    assert rows == []
    assert status == {"a@x.com": "error: imap"}


def test_keychain_password_uses_the_security_cli():
    calls = []

    def runner(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="secret\n", stderr="")

    assert daily_mail.keychain_password("a@x.com", runner=runner) == "secret"
    assert calls == [["security", "find-generic-password", "-s", "daily-imap", "-a", "a@x.com", "-w"]]
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `.venv/bin/pytest tests/test_daily_mail.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'daily_mail'`

- [ ] **Step 3: Write the module**

```python
# src/daily_mail.py
"""Sent mail headers for the daily note, read over IMAP. Bodies are never fetched."""
import email
import email.policy
import email.utils
import imaplib
import subprocess
from datetime import timedelta

FETCH_SPEC = "(BODY.PEEK[HEADER.FIELDS (DATE TO SUBJECT)])"
KEYCHAIN_SERVICE = "daily-imap"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
SUBJECT_CHARS = 150


def keychain_password(address, runner=subprocess.run):
    """The Google app password stored with `security add-generic-password -s daily-imap`."""
    result = runner(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", address, "-w"],
        capture_output=True, text=True,
    )
    secret = result.stdout.strip() if result.returncode == 0 else ""
    return secret or None


def _connect(address, password):
    conn = imaplib.IMAP4_SSL("imap.gmail.com", timeout=15)
    conn.login(address, password)
    return conn


def _sent_folder(conn):
    """Find the sent folder by its \\Sent flag, so a localized label still works."""
    _, lines = conn.list()
    for raw in lines or []:
        line = raw.decode() if isinstance(raw, bytes) else str(raw)
        if "\\Sent" in line:
            return line.rsplit(' "/" ', 1)[-1].strip().strip('"')
    return None


def _imap_date(day):
    return f"{day.day:02d}-{MONTHS[day.month - 1]}-{day.year}"


def sent_for_day(conn, day):
    """Rows of {"to", "subject"} for mail sent on `day`. None if no sent folder."""
    folder = _sent_folder(conn)
    if folder is None:
        return None
    conn.select(f'"{folder}"', readonly=True)
    _, data = conn.search(None, "SINCE", _imap_date(day), "BEFORE", _imap_date(day + timedelta(days=1)))
    ids = (data[0] or b"").split()
    if not ids:
        return []
    _, parts = conn.fetch(",".join(i.decode() for i in ids), FETCH_SPEC)
    rows = []
    for part in parts:
        if not isinstance(part, tuple):
            continue
        message = email.message_from_bytes(part[1], policy=email.policy.default)
        names = [
            name or address.split("@")[0]
            for name, address in email.utils.getaddresses([str(message.get("To", ""))])
        ]
        rows.append({"to": ", ".join(names), "subject": str(message.get("Subject", ""))[:SUBJECT_CHARS]})
    return rows


def gather_mail(accounts, day, password_fn=keychain_password, connect=_connect):
    """Return (rows, status by account). One failing account never stops the others."""
    rows, status = [], {}
    for address in accounts:
        password = password_fn(address)
        if not password:
            status[address] = "no password"
            continue
        try:
            conn = connect(address, password)
            try:
                found = sent_for_day(conn, day)
            finally:
                conn.logout()
        except imaplib.IMAP4.error:
            status[address] = "error: imap"
            continue
        except OSError:
            status[address] = "error: network"
            continue
        if found is None:
            status[address] = "no sent folder"
            continue
        rows.extend({"account": address, **row} for row in found)
        status[address] = "ok"
    return rows, status
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `.venv/bin/pytest tests/test_daily_mail.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/daily_mail.py tests/test_daily_mail.py
git commit -m "feat(daily): read sent mail headers over IMAP"
```

---

### Task 7: Config (`daily_config.py`)

**Goal:** Load the user's settings from a JSON file over safe defaults, so no personal value lives in the code.

**Files:**
- Create: `src/daily_config.py`
- Test: `tests/test_daily_config.py`

**Acceptance Criteria:**
- [ ] A missing file gives exactly `DEFAULTS` (a deep copy).
- [ ] A file's keys override the defaults; keys it does not set keep their default.
- [ ] An unknown key raises `ValueError` that names it.
- [ ] The path defaults to `~/.config/magpie/config.json`, or `$MAGPIE_CONFIG` when set.

**Verify:** `.venv/bin/pytest tests/test_daily_config.py -v` → 3 passed

**Steps:**

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_daily_config.py
import json

import pytest

import daily_config


def test_load_returns_the_defaults_for_a_missing_file(tmp_path):
    assert daily_config.load(tmp_path / "none.json") == daily_config.DEFAULTS


def test_load_merges_the_file_over_the_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"timezone": "Europe/Paris", "calendars": ["a@x.com"]}), encoding="utf-8")
    cfg = daily_config.load(path)
    assert cfg["timezone"] == "Europe/Paris"
    assert cfg["calendars"] == ["a@x.com"]
    assert cfg["vault"] == "~/vault"


def test_load_rejects_an_unknown_key(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"vaul": "x"}), encoding="utf-8")
    with pytest.raises(ValueError, match="vaul"):
        daily_config.load(path)
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `.venv/bin/pytest tests/test_daily_config.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'daily_config'`

- [ ] **Step 3: Write the module**

```python
# src/daily_config.py
"""Settings for /daily. Every key is optional; the file only overrides the defaults."""
import copy
import json
import os
from pathlib import Path

DEFAULT_PATH = Path(
    os.environ.get("MAGPIE_CONFIG", "~/.config/magpie/config.json")
).expanduser()

DEFAULTS = {
    "timezone": None,  # IANA name such as "Europe/Paris"; None means the system's local time
    "vault": "~/vault",
    "journal_dir": "50 Journal/daily",
    "template": "90 Templates/daily.md",
    "repos_root": "~/projects",
    "extra_repos": [],
    "activitywatch_url": "http://localhost:5600/api/0",
    "exclude_domains": [],
    "mail_accounts": [],
    "calendars": [],
}


def load(path=DEFAULT_PATH):
    cfg = copy.deepcopy(DEFAULTS)
    path = Path(path)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        unknown = sorted(set(data) - set(DEFAULTS))
        if unknown:
            raise ValueError(f"unknown config keys: {', '.join(unknown)}")
        cfg.update(data)
    return cfg
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `.venv/bin/pytest tests/test_daily_config.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/daily_config.py tests/test_daily_config.py
git commit -m "feat(daily): load settings from a config file"
```

---

### Task 8: CLI (`daily.py`): gather and write

**Goal:** `daily.py gather` prints the day's payload grouped by card; `daily.py write` replaces the note sections from JSON on stdin.

**Files:**
- Create: `src/daily.py`
- Test: `tests/test_daily.py`

**Acceptance Criteria:**
- [ ] `gather` groups logs, commits and sessions by card through the cards' `repo:` lines; a session inside the vault maps to repo `vault`; a session in a missing folder uses the folder name; groups are sorted by `3 x logs + commits + sessions`, highest first.
- [ ] `gather` output has the keys `date`, `note_path`, `manual`, `groups`, `covered_sessions`, `skipped_repos`, `activity`, `activity_status`, `sent_mail`, `mail_status`, `calendars`.
- [ ] Each option left out on the command line takes its value from the config file (`--config`); an empty `mail_accounts` list gives `mail_status` `{}`.
- [ ] A repo where `git log` fails is listed in `skipped_repos` and the run goes on.
- [ ] `cap_size` drops session turns from the largest group first until the JSON fits; logs and commits are never dropped.
- [ ] `write` prints `{"old": ...}`, writes the new sections, creates a missing note from the template, and on an error returns 1, prints to stderr, and leaves the file as it was.

**Verify:** `.venv/bin/pytest tests/test_daily.py -v` → 6 passed, then `just test` → all passed

**Steps:**

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_daily.py
import io
import json
import os
import socket
import subprocess
import sys

import daily

NOTE = "# 2026-10-05\n\n**Did:** \n\n- inbox zero\n**Blocked:** \n**Next:** \n"
TEMPLATE = "# {{date:YYYY-MM-DD}}\n\n**Did:** \n**Blocked:** \n**Next:** \n"


def _dead_url():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return f"http://127.0.0.1:{port}/api/0"


def _commit(repo, message, when):
    env = {**os.environ, "GIT_AUTHOR_NAME": "Me", "GIT_AUTHOR_EMAIL": "me@x.com",
           "GIT_COMMITTER_NAME": "Me", "GIT_COMMITTER_EMAIL": "me@x.com",
           "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
    subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "commit",
                    "--allow-empty", "--no-verify", "-q", "-m", message],
                   check=True, capture_output=True, env=env)


def _session(path, session_id, cwd, text, ts="2026-10-05T09:00:00Z"):
    record = {"type": "user", "timestamp": ts, "cwd": str(cwd), "message": {"content": text}}
    (path / f"{session_id}.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")


def _setup(tmp_path):
    vault = tmp_path / "vault"
    project = vault / "10 Projects" / "vault-setup"
    (project / "log").mkdir(parents=True)
    (project / "_project.md").write_text(
        "---\nrepo: https://github.com/me/vault\n---\n"
        "**Next action:** finish the spec.\n**Open decisions:** none.\n", encoding="utf-8")
    (project / "log" / "2026-10-05.md").write_text("Wrote the spec.\n", encoding="utf-8")
    area = vault / "20 Areas" / "learning"
    area.mkdir(parents=True)
    (area / "_area.md").write_text("---\nrepo: https://github.com/me/alpha\n---\n# Learning\n", encoding="utf-8")
    (vault / "90 Templates").mkdir()
    (vault / "90 Templates" / "daily.md").write_text(TEMPLATE, encoding="utf-8")
    (vault / "50 Journal" / "daily").mkdir(parents=True)
    (vault / "50 Journal" / "daily" / "2026-10-05.md").write_text(NOTE, encoding="utf-8")

    repos = tmp_path / "repos"
    alpha = repos / "alpha"
    alpha.mkdir(parents=True)
    subprocess.run(["git", "-C", str(alpha), "init", "-q", "-b", "main"], check=True)
    subprocess.run(["git", "-C", str(alpha), "remote", "add", "origin",
                    "https://github.com/me/alpha.git"], check=True)
    _commit(alpha, "feat: parser", "2026-10-05T10:00:00+02:00")

    projects = tmp_path / "projects"
    sessions = projects / "p"
    sessions.mkdir(parents=True)
    _session(sessions, "s1", alpha, "fix the parser")
    _session(sessions, "s2", tmp_path / "gone" / "scratch", "try an idea")
    _session(sessions, "s3", vault, "tidy the inbox")
    return vault, repos, projects


def _gather(capsys, tmp_path, vault, repos, projects):
    code = daily.main([
        "gather", "--config", str(tmp_path / "no-config.json"), "--tz", "Europe/Paris",
        "--date", "2026-10-05", "--vault", str(vault),
        "--projects-dir", str(projects), "--repos-root", str(repos),
        "--extra-repo", str(tmp_path / "no-such-repo"), "--author", "me@x.com",
        "--aw-url", _dead_url(),
    ])
    assert code == 0
    return json.loads(capsys.readouterr().out)


def test_gather_groups_logs_commits_and_sessions_by_card(tmp_path, capsys):
    vault, repos, projects = _setup(tmp_path)
    out = _gather(capsys, tmp_path, vault, repos, projects)
    assert out["date"] == "2026-10-05"
    assert out["note_path"] == str(vault / "50 Journal" / "daily" / "2026-10-05.md")
    assert out["manual"] == {"did": "- inbox zero", "blocked": "", "next": ""}
    assert [g["name"] for g in out["groups"]] == ["vault-setup", "learning", "scratch"]
    groups = {g["name"]: g for g in out["groups"]}
    assert groups["vault-setup"]["logs"] == ["Wrote the spec.\n"]
    assert groups["vault-setup"]["card_next_action"] == "finish the spec."
    assert [s["id"] for s in groups["vault-setup"]["sessions"]] == ["s3"]
    assert groups["learning"]["link"] == "[[20 Areas/learning/_area|learning]]"
    assert groups["learning"]["commits"] == [{"repo": "alpha", "subject": "feat: parser"}]
    assert [s["id"] for s in groups["learning"]["sessions"]] == ["s1"]
    assert groups["scratch"]["link"] is None
    assert out["covered_sessions"] == []
    assert out["skipped_repos"] == []
    assert out["activity"] is None
    assert out["activity_status"] == "unavailable"
    assert out["sent_mail"] == []
    assert out["mail_status"] == {}
    assert out["calendars"] == []


def test_gather_skips_a_broken_repo(tmp_path, capsys):
    vault, repos, projects = _setup(tmp_path)
    (repos / "broken").mkdir()
    (repos / "broken" / ".git").write_text("garbage", encoding="utf-8")
    out = _gather(capsys, tmp_path, vault, repos, projects)
    assert out["skipped_repos"] == ["broken"]


def test_cap_size_drops_session_turns_from_the_largest_group_first():
    payload = {"groups": [
        {"name": "a", "logs": ["L" * 50], "commits": [], "sessions": [{"turns": ["x" * 100] * 5}]},
        {"name": "b", "logs": [], "commits": [], "sessions": [{"turns": ["y" * 10]}]},
    ]}
    limit = len(json.dumps(payload, ensure_ascii=False)) - 150
    daily.cap_size(payload, limit=limit)
    assert len(payload["groups"][0]["sessions"][0]["turns"]) == 3
    assert payload["groups"][1]["sessions"][0]["turns"] == ["y" * 10]
    assert payload["groups"][0]["logs"] == ["L" * 50]


def test_write_replaces_the_sections_and_prints_the_old_ones(tmp_path, capsys, monkeypatch):
    vault, _, _ = _setup(tmp_path)
    bullets = {
        "did": ["[[10 Projects/vault-setup/_project|vault-setup]]: wrote the spec", "inbox zero"],
        "blocked": [],
        "next": ["finish the spec"],
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(bullets)))
    assert daily.main(["write", "--config", str(tmp_path / "none.json"), "--date", "2026-10-05",
                       "--vault", str(vault)]) == 0
    assert json.loads(capsys.readouterr().out) == {"old": {"did": "- inbox zero", "blocked": "", "next": ""}}
    text = (vault / "50 Journal" / "daily" / "2026-10-05.md").read_text(encoding="utf-8")
    assert text == (
        "# 2026-10-05\n\n**Did:**\n\n"
        "- [[10 Projects/vault-setup/_project|vault-setup]]: wrote the spec\n- inbox zero\n\n"
        "**Blocked:**\n\n**Next:**\n\n- finish the spec\n"
    )


def test_write_creates_a_missing_note_from_the_template(tmp_path, capsys, monkeypatch):
    vault, _, _ = _setup(tmp_path)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"did": ["a"], "blocked": [], "next": []})))
    assert daily.main(["write", "--config", str(tmp_path / "none.json"), "--date", "2026-10-06",
                       "--vault", str(vault)]) == 0
    text = (vault / "50 Journal" / "daily" / "2026-10-06.md").read_text(encoding="utf-8")
    assert text == "# 2026-10-06\n\n**Did:**\n\n- a\n\n**Blocked:**\n\n**Next:**\n"


def test_write_refuses_an_empty_did_and_leaves_the_file(tmp_path, capsys, monkeypatch):
    vault, _, _ = _setup(tmp_path)
    path = vault / "50 Journal" / "daily" / "2026-10-05.md"
    before = path.read_text(encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"did": [], "blocked": ["x"], "next": []})))
    assert daily.main(["write", "--config", str(tmp_path / "none.json"), "--date", "2026-10-05",
                       "--vault", str(vault)]) == 1
    assert "did section is empty" in capsys.readouterr().err
    assert path.read_text(encoding="utf-8") == before
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `.venv/bin/pytest tests/test_daily.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'daily'`

- [ ] **Step 3: Write the module**

```python
# src/daily.py
"""/daily: gather the day's traceable work, and write the daily note's sections."""
import argparse
import json
import socket
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import daily_aw
import daily_config
import daily_git
import daily_mail
import daily_note
import daily_sessions
import daily_vault

SIZE_LIMIT = 40000


def _zone(tz):
    """The IANA zone, or the system's local zone when the config gives none."""
    return ZoneInfo(tz) if tz else datetime.now().astimezone().tzinfo


def _day_bounds(day, tz):
    start = datetime(day.year, day.month, day.day, tzinfo=_zone(tz))
    return start, start + timedelta(days=1)


def _empty_group(name, card):
    return {
        "name": name,
        "link": card["link"] if card else None,
        "card_next_action": card["next_action"] if card else None,
        "card_open_decisions": card["open_decisions"] if card else None,
        "logs": [],
        "commits": [],
        "sessions": [],
    }


def _session_repo(cwd, vault):
    """The repo a session worked in. Superset worktrees resolve through git itself."""
    if not cwd:
        return "unknown"
    path, vault = Path(cwd), Path(vault)
    if path == vault or vault in path.parents:
        return "vault"
    return daily_git.origin_name(path) or path.name


def build_groups(cards, logs, commits, sessions, vault):
    """Group the day's work by card. Work with no card keeps its repo or folder name."""
    by_name = {card["name"]: card for card in cards}
    by_repo = {repo: card for card in cards for repo in card["repos"]}
    groups = {}

    def group_for(name, card=None):
        card = card or by_repo.get(name)
        key = card["name"] if card else name
        if key not in groups:
            groups[key] = _empty_group(key, card)
        return groups[key]

    for card_name, texts in logs.items():
        group_for(card_name, by_name[card_name])["logs"].extend(texts)
    for repo, subjects in commits:
        group_for(repo)["commits"].extend({"repo": repo, "subject": s} for s in subjects)
    for session in sessions:
        group_for(_session_repo(session["cwd"], vault))["sessions"].append(session)

    def weight(group):
        return 3 * len(group["logs"]) + len(group["commits"]) + len(group["sessions"])

    return sorted(groups.values(), key=weight, reverse=True)


def cap_size(payload, limit=SIZE_LIMIT):
    """Drop session turns from the largest group until the JSON fits. Logs and commits stay."""
    while len(json.dumps(payload, ensure_ascii=False)) > limit:
        candidates = [g for g in payload["groups"] if any(s["turns"] for s in g["sessions"])]
        if not candidates:
            break
        largest = max(candidates, key=lambda g: len(json.dumps(g["sessions"], ensure_ascii=False)))
        session = max(largest["sessions"], key=lambda s: len(s["turns"]))
        session["turns"].pop()
    return payload


def gather(args):
    day = args.date
    start, end = _day_bounds(day, args.tz)
    vault = Path(args.vault)
    cards = daily_vault.load_cards(vault)
    logs = daily_vault.logs_for_day(cards, day)

    author = args.author or daily_git.author_email()
    commits, skipped = [], []
    for repo in daily_git.find_repos(args.repos_root, args.extra_repo):
        subjects = daily_git.commits_for_day(repo, start, end, author) if author else []
        if subjects is None:
            skipped.append(repo.name)
        elif subjects:
            commits.append((daily_git.origin_name(repo) or repo.name, subjects))

    sessions, covered = daily_sessions.sessions_for_day(args.projects_dir, start, end, vault)
    activity, activity_status = daily_aw.gather_activity(
        args.aw_url, args.host, start, end, args.exclude
    )
    mail, mail_status = daily_mail.gather_mail(args.mail_account, day)

    path = daily_note.note_path(vault, day, args.journal_dir)
    manual = {"did": "", "blocked": "", "next": ""}
    if path.exists():
        try:
            manual = daily_note.read_sections(path.read_text(encoding="utf-8"))
        except ValueError:
            pass

    payload = {
        "date": day.isoformat(),
        "note_path": str(path),
        "manual": manual,
        "groups": build_groups(cards, logs, commits, sessions, vault),
        "covered_sessions": covered,
        "skipped_repos": skipped,
        "activity": activity,
        "activity_status": activity_status,
        "sent_mail": mail,
        "mail_status": mail_status,
        "calendars": args.calendars,
    }
    return cap_size(payload)


def write(args):
    try:
        sections = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"error: bad JSON on stdin: {exc}", file=sys.stderr)
        return 1
    path = daily_note.note_path(args.vault, args.date, args.journal_dir)
    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        text = daily_note.from_template(args.vault, args.date, args.template)
    try:
        old = daily_note.read_sections(text)
        new = daily_note.replace_sections(text, sections)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"old": old}, ensure_ascii=False, indent=2))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new, encoding="utf-8")
    return 0


def parse_args(argv):
    """Options left out take their value from the config file (see daily_config)."""
    parser = argparse.ArgumentParser(description="Pre-fill the Obsidian daily note.")
    sub = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", type=Path, default=daily_config.DEFAULT_PATH)
    common.add_argument("--date", type=date.fromisoformat, default=None, help="YYYY-MM-DD, default today")
    common.add_argument("--tz", default=None)
    common.add_argument("--vault", type=Path, default=None)

    g = sub.add_parser("gather", parents=[common], help="print the day's facts as JSON")
    g.add_argument("--projects-dir", type=Path, default=Path.home() / ".claude" / "projects")
    g.add_argument("--repos-root", type=Path, default=None)
    g.add_argument("--extra-repo", type=Path, action="append", default=None)
    g.add_argument("--author", default=None, help="default: git config --global user.email")
    g.add_argument("--aw-url", default=None)
    g.add_argument("--host", default=socket.gethostname())
    g.add_argument("--mail-account", action="append", default=None)

    sub.add_parser("write", parents=[common], help="replace the note sections from JSON on stdin")
    return resolve(parser.parse_args(argv))


def resolve(args):
    """Fill every option that was left out from the config file."""
    cfg = daily_config.load(args.config)
    args.tz = args.tz or cfg["timezone"]
    args.vault = Path(args.vault or cfg["vault"]).expanduser()
    args.journal_dir = cfg["journal_dir"]
    args.template = cfg["template"]
    if args.date is None:
        args.date = datetime.now(_zone(args.tz)).date()
    if args.command == "gather":
        args.repos_root = Path(args.repos_root or cfg["repos_root"]).expanduser()
        if args.extra_repo is None:
            args.extra_repo = [Path(p).expanduser() for p in cfg["extra_repos"]]
        args.aw_url = args.aw_url or cfg["activitywatch_url"]
        args.exclude = {domain.lower() for domain in cfg["exclude_domains"]}
        args.mail_account = args.mail_account or cfg["mail_accounts"]
        args.calendars = cfg["calendars"]
    return args


def main(argv=None):
    args = parse_args(argv)
    if args.command == "gather":
        print(json.dumps(gather(args), ensure_ascii=False, indent=2))
        return 0
    return write(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `.venv/bin/pytest tests/test_daily.py -v`
Expected: 6 passed

Run: `just test`
Expected: every test passes, old and new.

- [ ] **Step 5: Commit**

```bash
git add src/daily.py tests/test_daily.py
git commit -m "feat(daily): gather and write commands"
```

---

### Task 9: Skill, install and docs

**Goal:** Ship `skills/daily/SKILL.md`, add `just install`, write the public README, and allow the write in the vault rules.

**Files:**
- Create: `skills/daily/SKILL.md`
- Create (by `just install`): `skills/daily/*.py` (copies of `src/*.py`)
- Modify: `justfile` (add recipe `install`)
- Create: `README.md`
- Modify (outside the repo, no git): `~/vault/CLAUDE.md` (Writing rules)

**Acceptance Criteria:**
- [ ] `just install` copies the nine modules of `src/` into `skills/daily/` and symlinks `~/.claude/skills/daily`.
- [ ] `README.md` explains what the skill does, the sources, the install, the config keys and the privacy rules, with no personal value.
- [ ] `python3 ~/.claude/skills/daily/daily.py gather --help` prints the usage.
- [ ] `SKILL.md` contains no em dash: `grep -c "$(printf '\342\200\224')" skills/daily/SKILL.md` prints `0`.
- [ ] `~/vault/CLAUDE.md` has the line that lets `/daily` write the three sections.

**Verify:** `just install && python3 ~/.claude/skills/daily/daily.py gather --help | head -1` → `usage: daily.py gather [-h] ...`

**Steps:**

- [ ] **Step 1: Write the skill**

````markdown
---
name: daily
description: Use when the user runs /daily, or asks to pre-fill, draft or fill the daily note or journal for today or a given day. Gathers the day's vault logs, git commits, Claude Code sessions, ActivityWatch time, calendar events and sent mail, then writes a Did / Blocked / Next draft into the Obsidian daily note.
---

# Daily

Draft the three sections of the user's Obsidian daily note from what is traceable. The
user edits the draft every evening. **Did:** is a record of facts. **Blocked:** and
**Next:** are a starting point.

## Rules

- No em dashes in any bullet. Use commas, colons, periods or parentheses.
- Never invent a fact. Every bullet comes from the gathered data or from the user's own
  bullets.
- Change the note only through `daily.py write`. Never edit the note by hand.
- Never copy a full URL, a mail body or a long transcript quote into the note.
- Bullets are in English, plain past tense for **Did:**, one line each.

## Step 1: Gather

The day is the argument (`/daily 2026-10-04`) or, without one, today.

1. Run:

   ```bash
   python3 ~/.claude/skills/daily/daily.py gather --date <YYYY-MM-DD>
   ```

2. Read the calendar with the Google Calendar `list_events` tool, once per ID in the
   payload's `calendars` list (from the user's config; skip this step if it is empty):
   `startTime` `<day>T00:00:00`, `endTime` `<next day>T00:00:00`, and `timeZone` the
   config time zone. Run `gather` first if you need the list; it is fast.
   Keep an event only if all are true:
   - `start.dateTime` exists (not an all-day event);
   - `eventType` is `DEFAULT`;
   - the user is the organizer, or the attendee with `"self": true` has
     `responseStatus` `accepted`, or there is no attendee list.

If `activity_status` is not `ok`, a `mail_status` value is not `ok`, or
`skipped_repos` is not empty, tell the user in one line which source is missing.

## Step 2: Draft

**Did:** one bullet per group in `groups`, in the given order:

- Start with the group's `link` and a colon, or the plain `name` when `link` is null.
  Example: `[[10 Projects/vault-setup/_project|vault-setup]]: wrote the /daily spec and plan`.
- Use `logs` first (they are the best summary), then `commits`, then `sessions`
  (`turns` say what the user asked, `last_reply` what was done).
- A session in the vault (`cwd` is the vault) can be about another project. If its
  turns clearly name another group's project, fold it into that group.
- Fold `activity` rows into a group when the title or domain names its project
  (a repo name in a VS Code title, a `github.com` page about the repo). An activity row
  of 30 minutes or more that fits no group can be its own bullet, for example
  `Read the ActivityWatch docs (docs.activitywatch.net, 40 min)`.
- Calendar events: fold into a group when the title names its project; otherwise one
  bullet per event, with its time: `10:00 call with Abby`.
- Sent mail: fold into a group when the subject names its project. Otherwise group
  the mails in one bullet: `Sent 3 mails: invoice to Abby, ...`. Skip mail that is
  clearly automatic.

**Blocked:** at most 3 bullets, only with evidence: a log, a last reply or a mail that
names a failure, a wait on someone, or a card's `card_open_decisions` that is not
`none`. No evidence, no bullet.

**Next:** at most 3 bullets, from the `card_next_action` of the top groups and from
the last replies of the day. Prefer the group with the most work.

**Merge the user's bullets (`manual`), in all three sections.** Every fact in a manual
bullet must survive. A manual bullet about a project is folded into that project's
bullet. A manual bullet with no project stays as its own bullet, in the user's words.

## Step 3: Write

```bash
python3 ~/.claude/skills/daily/daily.py write --date <YYYY-MM-DD> <<'EOF'
{"did": ["..."], "blocked": ["..."], "next": ["..."]}
EOF
```

Each list holds bullet strings without the leading `- `. `did` must not be empty.
The command prints the old sections. If it fails, show the error and stop.

## Step 4: Report

Show the new note sections as they are now in the file, then one line: what changed
compared with the old sections (for example "3 bullets added, your 2 bullets merged").
Nothing else.
````

- [ ] **Step 2: Add `just install`**

Append to `justfile`:

```just
# Copy the tested modules into the skill dir and symlink the skill globally
install:
    cp src/*.py skills/daily/
    mkdir -p ~/.claude/skills
    ln -sfn "$(pwd)/skills/daily" ~/.claude/skills/daily
    @echo "Installed. Run /daily in any Claude Code session."
```

- [ ] **Step 3: Write `README.md`**

```markdown
# magpie

A magpie collects shiny bits from everywhere and keeps them in one nest. This
Claude Code skill does the same with your day. Run `/daily` in the evening, and it
drafts your Obsidian daily note from what you actually did: it fills **Did:**, **Blocked:** and **Next:**, and you edit the draft.

## Sources

| Source | How it is read |
|---|---|
| Vault project logs (`10 Projects/*/log/<date>.md`, `20 Areas/*/log/<date>.md`) | local files |
| Git commits (your author email, all branches) | `git log` on local clones |
| Claude Code sessions | `~/.claude/projects/*.jsonl`, read-only, your messages and the last reply only |
| ActivityWatch (apps, windows, Chrome tabs) | local REST API, active time only |
| Google Calendar | the Google Calendar connector in Claude |
| Sent mail (headers only) | IMAP, app password from the macOS Keychain |

Every source is optional. A missing one is reported in one line and skipped.

## Install

    git clone <this repo> && cd magpie
    python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
    just test && just install

## Config

`~/.config/magpie/config.json` (or `$MAGPIE_CONFIG`). Every key is
optional:

| Key | Default | Meaning |
|---|---|---|
| `timezone` | system local | IANA name of your day, such as `Europe/Paris` |
| `vault` | `~/vault` | Obsidian vault |
| `journal_dir` | `50 Journal/daily` | daily notes folder, in the vault |
| `template` | `90 Templates/daily.md` | template for a missing note |
| `repos_root` | `~/projects` | every git repo directly under it is read |
| `extra_repos` | `[]` | more repos |
| `activitywatch_url` | `http://localhost:5600/api/0` | ActivityWatch API |
| `exclude_domains` | `[]` | domains never reported (and their subdomains) |
| `mail_accounts` | `[]` | Gmail addresses whose sent mail is read |
| `calendars` | `[]` | Google Calendar IDs |

For each mail account, create a Google app password and store it:

    security add-generic-password -s daily-imap -a you@example.com -w

## Privacy

Everything runs on your machine. Mail bodies are never downloaded. Web activity is
reported as domains, never full URLs. Session transcripts are read, never changed.

## License

MIT
```

- [ ] **Step 4: Allow the write in the vault rules**

In `~/vault/CLAUDE.md`, under `## Writing rules`, add this line after the first bullet
(do not run git in the vault):

```markdown
- The `/daily` skill may write the **Did:**, **Blocked:** and **Next:** sections of a
  note in `50 Journal/daily/`.
```

- [ ] **Step 5: Install and check**

Run: `just install && python3 ~/.claude/skills/daily/daily.py gather --help | head -1`
Expected: `usage: daily.py gather [-h] ...`

Run: `grep -c "$(printf '\342\200\224')" skills/daily/SKILL.md`
Expected: `0`

Run: `just test`
Expected: every test passes.

- [ ] **Step 6: Commit**

```bash
git add skills/daily justfile README.md
git commit -m "feat(daily): add the /daily skill, install recipe and README"
```

---

### Task 10: Live run on the real day

**Goal:** Run `/daily` for 2026-10-05 on the real vault, repos, sessions, ActivityWatch, calendars and mailboxes, and confirm the success criteria of the spec.

**Files:**
- Create (outside the repo): `~/.config/magpie/config.json`
- Modify (outside the repo): `~/vault/50 Journal/daily/2026-10-05.md` (through `daily.py write` only)

**Acceptance Criteria:**
- [ ] `gather --date 2026-10-05` exits 0; `activity_status` is `ok`; `mail_status` is `ok` for both accounts; `calendars` lists both IDs.
- [ ] The written **Did:** has one bullet per project worked on that day, and the three manual bullets of that note survive the merge ("set up the GitHub second brain", "inbox zero", "website refactoring").
- [ ] **Next:** has at least one bullet taken from the vault-setup card's next action.
- [ ] The title line of the note is unchanged.

**Verify:** `python3 ~/.claude/skills/daily/daily.py gather --date 2026-10-05 | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['activity_status'], d['mail_status'], [g['name'] for g in d['groups']])"` → `ok {'<account 1>': 'ok', '<account 2>': 'ok'} [...]`

**Steps:**

- [ ] **Step 0: Write the user's config (outside the repo, never committed)**

The user's own values are recorded in their vault card and in this session; write them
to `~/.config/magpie/config.json`:

```json
{
  "timezone": "Europe/Paris",
  "vault": "~/vault",
  "repos_root": "~/projects/personal",
  "extra_repos": ["~/.claude"],
  "mail_accounts": ["<the two Gmail addresses>"],
  "calendars": ["<the two calendar IDs>"],
  "exclude_domains": []
}
```

The coordinator fills in the two addresses and the two calendar IDs (they are the
same two addresses) from the conversation. They never go into the repo.

- [ ] **Step 1: The user creates the two app passwords (manual, the user does this)**

For each address, open https://myaccount.google.com/apppasswords while signed in as
that address, and create an app password named `daily`. App passwords need 2-Step
Verification on the account. If the page says app passwords are not available for
the work address, turn on 2-Step Verification for it first (it is a Workspace
account, so the admin console may also need to allow 2-Step Verification).
Then store it, one command per address (the command prompts for the password, so it
never appears in the shell history):

```bash
security add-generic-password -s daily-imap -a <work address> -w
security add-generic-password -s daily-imap -a <personal Gmail address> -w
```

IMAP must be on in each Gmail account (Settings, Forwarding and POP/IMAP).

- [ ] **Step 2: Gather and check the payload**

Run the **Verify** command. Expected: `ok`, both mail accounts `ok`, and the groups
include `vault-setup` and `learning-to-code`. If a status is not `ok`, fix the cause
(ActivityWatch not running, a missing Keychain entry) and run it again.

- [ ] **Step 3: Run the skill**

In a Claude Code session, run `/daily 2026-10-05`. Then read the note:

Run: `cat "$HOME/vault/50 Journal/daily/2026-10-05.md"`
Expected: line 1 is `# 2026-10-05`; the three manual facts are present; **Next:** has
a bullet from the vault-setup next action; each list is followed by a blank line.

- [ ] **Step 4: Record the result**

Write two lines in `~/vault/20 Areas/learning-to-code/log/2026-10-05.md` (create it if
missing; no git in the vault): what `/daily` produced and what the user changed in the
draft. This is the first evidence on whether the draft is useful.
