# Weekly journal note (`/magpie week`): design

Date: 2026-10-19. Status: approved in brainstorm 2026-10-19, awaiting spec review.

## Goal

Write a weekly note that does two jobs: a short look back per project, and up to three
focus items for the next week. The daily notes already hold the facts, so the skill
drafts the weekly note from them and from nothing else. It fills gaps first. A day of
the week with no daily note gets the usual daily run before the weekly draft.

Target file: `~/vault/50 Journal/weekly/YYYY-Www.md` (ISO week, the format Obsidian's
periodic notes use), for example `2026-W42.md`:

```
# 2026-W42 (2026-10-12 to 2026-10-18)

**Moved:**
- [[10 Projects/site/_project|site]]: booking form split per language, traffic read
**Still blocked:**
- [[10 Projects/house/_project|house]]: funding route open
**Focus:**
- [[10 Projects/site/_project|site]]: fix the launch blockers
```

## Non-goals (v1)

- No monthly note. A month summary can read four weekly notes later, if it is ever
  wanted.
- No schedule. The user runs `/magpie week` by hand, like the daily run.
- No template file in the vault. The code writes the title line and the three markers.
- No checkboxes in **Focus:**. A task lives as a checkbox in the note it is about; the
  weekly note links to it, so `/todo` never counts a task twice.
- No new data sources. The weekly draft reads daily notes and project cards only.

## Which week

`/magpie week` with no date takes the ISO week (Monday to Sunday) that contains
yesterday, in the configured timezone. On Sunday evening that is the current week. On
Monday morning it is the week that just ended. `/magpie week 2026-10-14` takes
the week that contains that date.

## Config

One new optional key, `weekly_dir`, default `50 Journal/weekly`. Unknown keys stay an
error.

## `daily.py week --date YYYY-MM-DD`

Prints one JSON object:

```json
{
  "week": "2026-W42",
  "start": "2026-10-12",
  "end": "2026-10-18",
  "note_path": ".../50 Journal/weekly/2026-W42.md",
  "manual": {"moved": "", "blocked": "", "focus": ""},
  "days": [
    {"date": "2026-10-12", "status": "ok", "did": "...", "blocked": "...", "next": "..."},
    {"date": "2026-10-15", "status": "missing"},
    {"date": "2026-10-19", "status": "future"}
  ],
  "cards": [
    {"name": "site", "link": "[[...]]", "next_action": "...", "open_decisions": "..."}
  ],
  "errors": {}
}
```

- `status` is `ok` (note read), `missing` (no file, or a file with three empty
  sections), `unreadable` (markers missing; the reason goes in `errors`), or `future`
  (after today). Today counts as a past day, so a Sunday evening run includes Sunday.
- `cards` holds only the cards whose link or name appears in one of the week's daily
  notes. The skill uses their next action and open decisions for **Focus:** and
  **Still blocked:**.
- `manual` holds the text already under each marker of the weekly note, when the file
  exists.
- The command never fails on one bad day; it records the error and goes on.

## `daily.py write --week --date YYYY-MM-DD`

Reads `{"moved": [...], "blocked": [...], "focus": [...]}` on stdin and writes the
weekly note. Same contract as the daily `write`: it prints the old sections, refuses an
empty `moved`, and only touches the text from the first marker on. When the file does
not exist, it starts from the title line `# YYYY-Www (start to end)`.

`daily_note.py` takes the marker set as a parameter (daily: Did / Blocked / Next,
weekly: Moved / Still blocked / Focus), so both notes share the same read, render and
replace code.

## The skill (`skills/magpie/SKILL.md`)

A new section, "Weekly run", triggered by `/magpie week [date]`:

1. Run `daily.py week`. Report `errors` in one line.
2. For each day with `status` `missing`, run the daily flow (gather, draft, write) for
   that date. A day whose gather has no groups, no activity row of 30 minutes or more,
   no calendar event and no sent mail gets no note: say so in the report and move on.
   Then run `daily.py week` again.
3. Draft the three sections:
   - **Moved:** one bullet per project or area, from the **Did:** bullets of the week.
     State results, not steps. Work with no project keeps one short bullet.
   - **Still blocked:** at most 3, from the week's **Blocked:** bullets that no later
     daily note or card shows as resolved, plus open decisions from `cards` when they
     hold up work.
   - **Focus:** at most 3, plain text with links, from the cards' next actions and the
     last **Next:** bullets. Prefer the project with the most work in the week.
   - Merge `manual` as the daily run does: every fact in the user's bullets survives,
     nothing is duplicated.
4. Run `daily.py write --week`, then show the note and one line: which days were
   filled, which had no activity, and what changed.

## Errors

- A daily note without markers: `unreadable`, never rewritten by the weekly run.
- A daily run that fails during gap filling: report it, keep going with the other days,
  and draft the weekly note from what exists.
- Bad JSON on stdin or an empty `moved`: `write` prints `error:` and exits 1, file
  untouched.

## Tests

TDD, in the existing test files:

- `test_daily.py`: week bounds (a Wednesday, a Sunday, a Monday, a year boundary such
  as 2026-12-31 in 2026-W53); the default week from "yesterday"; day status
  `ok`, `missing`, `unreadable`, `future`; card filtering by link and by name;
  `write --week` on a new file and on a file with user bullets.
- `test_daily_note.py`: read and replace with the weekly marker set; the daily marker
  set unchanged.
- `test_daily_config.py`: `weekly_dir` default and override.

Acceptance by hand: run `/magpie week 2026-10-14` on the real vault and check the
2026-W42 note.

## Success criteria

- `/magpie week` on Sunday evening produces a weekly note in under five minutes of
  review, with every missing day filled or named as empty.
- No daily note loses a user bullet, and no checkbox appears in a weekly note.
