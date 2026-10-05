# CLAUDE.md

magpie: a Claude Code skill, `/daily`, that drafts the Did / Blocked / Next sections of
an Obsidian daily note from the day's traceable work. Spec:
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
