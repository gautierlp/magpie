# Daily journal pre-fill (`/daily`): design

Date: 2026-10-05. Status: approved in brainstorm 2026-10-05, awaiting spec review.

## Goal

Pre-fill the three sections of the Obsidian daily note (**Did:**, **Blocked:**,
**Next:**) from what is traceable, so the evening note takes one minute of review
instead of recall. **Did:** is a record of facts. **Blocked:** and **Next:** are a
draft to get the user started: the user edits them every time, so a weak guess costs
one deletion.

Target file: `~/vault/50 Journal/daily/YYYY-MM-DD.md`, made from
`~/vault/90 Templates/daily.md`:

```
# {{date:YYYY-MM-DD}}

**Did:** 
**Blocked:** 
**Next:** 
```

## Non-goals (v1)

- No email bodies and no received mail. No direct read of Chrome's `History` SQLite file: browser activity comes
  from ActivityWatch (source 4), which records dwell time, not every page opened.
  Research on 2026-10-05 found no daily tool that reads the raw history file; the ones
  that use browser data take it from ActivityWatch.
- No Screenpipe: its reported CPU, RAM and battery cost is too high for the gain.
- No schedule. The user runs `/daily` by hand in the evening.
- No edits outside the three sections (the title line stays as it is).
- No network calls from the script, except `localhost` and Gmail IMAP. Commits come from local clones.

## Where it lives

In its own repo (`~/projects/personal/magpie`), separate from
`session_reviewer`, so each one can be open-sourced alone: session_reviewer improves
the Claude Code setup, this one is a daily update assistant. Decided 2026-10-05.

- `src/transcript.py`: the Claude Code transcript parser, copied from session_reviewer
  with `parse_ts` and `is_injected`. A copy, not a dependency, because the repos ship
  separately.
- `src/daily.py`: the deterministic half. Two subcommands, `gather` and `write`.
- `skills/daily/SKILL.md`: the reasoning half. Runs `gather`, writes the bullets, runs
  `write`.
- `just install` copies `src/*.py` into `skills/daily/` and symlinks that folder to
  `~/.claude/skills/daily`.

Stdlib only.

## Config

The repo is public, so no personal value is in the code. Settings come from
`~/.config/magpie/config.json` (or `$MAGPIE_CONFIG`). Every key is
optional: `timezone` (default: system local), `vault` (`~/vault`), `journal_dir`
(`50 Journal/daily`), `template` (`90 Templates/daily.md`), `repos_root`
(`~/projects`), `extra_repos` (`[]`), `activitywatch_url`
(`http://localhost:5600/api/0`), `exclude_domains` (`[]`), `mail_accounts` (`[]`),
`calendars` (`[]`). An unknown key is an error. A command-line option overrides its key.

## `daily.py gather --date YYYY-MM-DD`

Prints one JSON object to stdout. `--date` defaults to today in local time. The day is
the local calendar day in the configured time zone: transcript timestamps are UTC
and are converted before the day filter. Every path, URL and list comes from the config, and a command-line option overrides it (tests pass them all).

### Sources, in priority order

1. **Vault logs.** Every `10 Projects/*/log/<date>.md` and `20 Areas/*/log/<date>.md`.
   Full text, each tagged with its card (the folder's `_project.md` or `_area.md`).
   For each card that has work on the day, `gather` also copies its `**Next action:**`
   and `**Open decisions:**` lines: they are the main input for **Next:** and
   **Blocked:**.
2. **Commits.** For each git repo directly under `--repos-root`, plus each
   `--extra-repo`: `git log --all --since <day start> --until <day end>
   --author <global user.email>`, subject lines only. `--all` covers branches made in
   Superset workspaces, because a worktree shares the main clone's git data. A folder
   that is not a git repo is skipped. The vault has no `.git` on the Mac, so it never
   shows up.
3. **Sessions.** Each transcript under `--projects-dir` with at least one record on
   that day, excluding subagent transcripts (reuse the digest filter). Per session:
   the working directory, the human turns of that day (injected and harness text
   dropped with `transcript.is_injected`, each turn cut to 300 chars, at most 8 turns), and
   the last assistant text block of the day cut to 500 chars.
   - **Covered sessions are dropped.** A session that wrote or edited a vault log file
     for that date (a `Write` or `Edit` tool call whose `file_path` matches
     `<vault>/(10 Projects|20 Areas)/<name>/log/<date>.md`) is already described by
     source 1. It is listed by id only, under `covered_sessions`.
   - **`/daily` runs are dropped.** A session whose human turns invoke `/daily` is the
     tool itself, not work.
4. **ActivityWatch.** Local REST API at `http://localhost:5600/api/0`, buckets
   `aw-watcher-window_<host>`, `aw-watcher-afk_<host>` and
   `aw-watcher-web-chrome_<host>` (`<host>` is `socket.gethostname()`). Noise filters:
   - Keep only time when the AFK bucket says `not-afk` (intersect the intervals).
   - Group window events by app plus title, and web events by domain plus page title.
     Sum the durations. Drop any group under 2 minutes. Keep the top 20 by time.
   - Drop every domain in the config `exclude_domains` list, and its subdomains. This is the privacy filter for banking, health
     and similar sites.
   - Cut titles to 100 chars. Never output full URLs, only domains.
   - If the server does not answer within 2 seconds, set `activitywatch: null` and go
     on.
   ActivityWatch data is not mapped to cards by the script. It goes in a separate
   `activity` list, and the skill folds it into the right project when a title or
   domain names one (for example a GitHub URL or a VS Code window with the repo name).
5. **Calendar.** Read by the skill, not the script, through the Google Calendar MCP
   connector (`list_events` for the local day). Keep events of type `DEFAULT` (this drops focus
   time, out of office and working location) that the user accepted or organizes.
   Skip all-day events and declined events. Each kept event is a **Did:** fact. The
   connector is signed in as the work address; the the personal Gmail address
   calendar is shared to that account (done 2026-10-05). The share does not add it to
   `list_calendars`, so the skill calls `list_events` with the two calendar IDs by name:
   the work address and the personal Gmail address. Verified 2026-10-05: the
   connector reads the Gmail calendar with `accessRole: reader`.
6. **Sent mail.** Both accounts (the work address, the personal Gmail address),
   read by the script over IMAP (`imaplib`, stdlib) from the Gmail folder
   `[Gmail]/Sent Mail` (the folder name is found with the `\Sent` flag, so a French
   UI label still works). Headers only: date, recipient names, subject. The body is
   never fetched (`BODY.PEEK[HEADER.FIELDS (DATE TO SUBJECT)]`). Auth: a Google app
   password per account, read from the macOS Keychain with
   `security find-generic-password -s daily-imap -a <address> -w`. A missing password
   or a failed login sets `mail_status` for that account and the run goes on. Sent
   mail is what the user did; received mail is mostly noise, so it is out.

### Mapping work to a card

Each card's frontmatter has a `repo:` line with one or more GitHub URLs, comma
separated. `gather` builds a map from repo name (last URL segment, without `.git`) to
card. It maps a commit or session to a repo like this:

- A commit: the repo it was found in, by its `origin` remote URL.
- A session: `git -C <working directory> remote get-url origin`. This also works in a
  Superset workspace, because a worktree shares the main clone's config (the folder
  names under `~/.superset/worktrees/` are often UUIDs, so they are not used). A
  working directory inside the vault maps to the `vault` card. If the folder no longer
  exists or has no `origin`, use the folder's last path segment as the name.

Then repo to card through the map. Work with no card keeps the repo or folder name.
Output groups everything by card:

```json
{
  "date": "2026-10-05",
  "note_path": "~/vault/50 Journal/daily/2026-10-05.md",
  "manual": {"did": "- set up the GitHub second brain\n- ...", "blocked": "", "next": ""},
  "groups": [
    {
      "name": "vault-setup",
      "link": "[[10 Projects/vault-setup/_project|vault-setup]]",
      "card_next_action": "rewrite pass on the finance notes ...",
      "card_open_decisions": "none.",
      "logs": ["..."],
      "commits": [{"repo": "vault", "subject": "..."}],
      "sessions": [{"id": "...", "cwd": "...", "turns": ["..."], "last_reply": "..."}]
    }
  ],
  "covered_sessions": ["..."],
  "activity": [{"kind": "app", "name": "Code", "title": "daily.py: session_reviewer", "minutes": 42}],
  "activity_status": "ok",
  "sent_mail": [{"account": "<work address>", "to": "Abby", "subject": "..."}],
  "mail_status": {"<work address>": "ok", "<personal Gmail address>": "no password"}
}
```

`link`, `card_next_action` and `card_open_decisions` are `null` for work with no card.
`manual` holds the current text of each section, or empty strings if the note does not
exist.

**Size cap:** if the JSON passes 40,000 characters, drop session turns from the
largest group first, until it fits. Logs and commits are never dropped.

## The skill (`skills/daily/SKILL.md`)

1. Run `gather` for the day (argument: optional date). In parallel, read the day's
   calendar events (source 5). If `activity_status` is not `ok`, say in one line that
   ActivityWatch data is missing.
2. **Did:** one bullet per group, plain past tense, one line, starting with the `link`
   (or the plain name). Order: most work first.
3. **Blocked:** at most 3 bullets, only from evidence: a log or a last reply that names
   a failure, a wait on someone, or an open decision on a card. No evidence, no bullet.
4. **Next:** at most 3 bullets, from the cards' next action and the last replies of the
   day. Prefer the project with the most work that day.
5. **Merge the manual bullets, in all three sections.** Every fact in `manual` must
   survive. A manual bullet about a project is folded into that project's bullet. A
   manual bullet with no project (for example "inbox zero on email") stays as its own
   bullet.
6. Pipe the bullets to `write`. Show the user the old and new sections.
7. No em dashes in any bullet.

## `daily.py write --date YYYY-MM-DD`

Reads a JSON object from stdin, `{"did": [...], "blocked": [...], "next": [...]}`, each
a list of bullet strings without the `- `, and replaces the three sections of the note.
A section runs from its marker line (`**Did:**`, `**Blocked:**`, `**Next:**`) to the
next marker, and the last one to the end of the file.

- If the note does not exist, create it from the template, with `{{date:YYYY-MM-DD}}`
  replaced.
- Output shape, with a blank line after each list so Obsidian does not fold the next
  marker into the last list item (the current note has this rendering bug):

  ```
  **Did:**

  - bullet
  - bullet

  **Blocked:**

  - bullet

  **Next:**

  - bullet
  ```

- An empty `blocked` or `next` list writes the marker line alone.
- If a marker is missing, or `did` is empty, write nothing and exit with an error.
- Print the old sections to stdout before the write, so the skill can show them.
- Nothing above `**Did:**` changes, byte for byte.

## Vault rule change

`~/vault/CLAUDE.md`, Writing rules: add "The `/daily` skill may write the **Did:**,
**Blocked:** and **Next:** sections of a note in `50 Journal/daily/`." Without it, the vault rules forbid the write.

## Errors

- No source has anything for the day: `gather` returns empty groups; the skill says so
  and writes nothing.
- A broken transcript line is skipped (existing parser behavior).
- A failing `git log` in one repo skips that repo and adds its name to a `skipped_repos`
  list in the output. It never aborts the run.

## Tests

One test file per module, as the repo already does (`tests/test_daily_note.py`,
`test_daily_git.py`, `test_daily_vault.py`, `test_daily_sessions.py`,
`test_daily_aw.py`, `test_daily_mail.py`, `test_daily.py`). TDD. Fixtures are built in
`tmp_path` by small helpers in each test file:

- A fake vault (two cards with `repo:` lines, one log file, a daily note with manual
  bullets, the template).
- A git repo built in `tmp_path` with commits on and off the day, and by another author.
- ActivityWatch: a fake HTTP server in the test (stdlib `http.server`) with window,
  AFK and web buckets; checks the AFK intersection, the 2-minute floor, the top 20,
  the exclude file, domain-only output, and the timeout when no server answers.
- Sent mail: a fake IMAP object injected into the reader; checks header-only fetch
  (no body request), the day filter, and that a missing Keychain entry sets
  `mail_status` without aborting.
- Transcripts: one plain session, one that writes a vault log (covered), one `/daily`
  run, one subagent, one that crosses midnight UTC to Paris.
- `gather`: copies the next action and open decisions of a card with work that day.
- `write`: replaces the three sections; writes a marker alone for an empty list;
  creates a missing note from the template; refuses without a marker or without `did`
  bullets; leaves the title line byte for byte.

## Success criteria

- `just test` passes.
- `/daily` on 2026-10-05 produces one **Did:** bullet per project worked on that day,
  the three manual bullets of that note survive the merge, and **Next:** has at least
  one bullet taken from the vault-setup card.
