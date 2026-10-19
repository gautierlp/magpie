---
name: magpie
description: Use when the user runs /magpie or /magpie week, or asks to pre-fill, draft or fill the daily note, the journal, or the weekly note for a day or a week. Gathers the day's vault logs, git commits, Claude Code sessions, ActivityWatch time, calendar events and sent mail, then writes a Did / Blocked / Next draft into the Obsidian daily note; the weekly run sums the week's daily notes into Moved / Still blocked / Focus.
---

# magpie

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

The day is the argument (`/magpie 2026-10-04`) or, without one, today.

1. Run:

   ```bash
   python3 ~/.claude/skills/magpie/daily.py gather --date <YYYY-MM-DD>
   ```

2. Read the calendar with the Google Calendar `list_events` tool, once per ID in the
   payload's `calendars` list (from the user's config; skip this step if it is empty):
   `startTime` `<day>T00:00:00`, `endTime` `<next day>T00:00:00`, and `timeZone` the
   payload's `timezone` (leave `timeZone` out when it is null).
   Keep an event only if all are true:
   - `start.dateTime` exists (not an all-day event);
   - `eventType` is `DEFAULT`;
   - the user is the organizer, or the attendee with `"self": true` has
     `responseStatus` `accepted`, or there is no attendee list.

If `activity_status` is not `ok`, a `mail_status` value is not `ok`, or
`skipped_repos` is not empty, tell the user in one line which source is missing.
If `errors` is not empty, name each failed source in the same line.

## Step 2: Draft

**Did:** one bullet per group in `groups`, in the given order:

- Start with the group's `link` and a colon, or the plain `name` when `link` is null.
  Example: `[[10 Projects/vault-setup/_project|vault-setup]]: wrote the /magpie spec and plan`.
- Use `logs` first (they are the best summary), then `commits`, then `sessions`
  (`turns` say what the user asked, `last_reply` what was done).
- A session in the vault (`cwd` is the vault) can be about another project. If its
  turns clearly name another group's project, fold it into that group.
- Fold `activity` rows into a group when the title or domain names its project
  (a repo name in a VS Code title, a `github.com` page about the repo). An activity row
  of 30 minutes or more that fits no group can be its own bullet, for example
  `Read the ActivityWatch docs (docs.activitywatch.net, 40 min)`.
  If `activity` is null, skip it.
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

Write **Next** bullets as plain text with links, never as checkboxes (`- [ ]`). A task
lives as a checkbox in the note it is about; the daily note only points to it.

**Merge the user's bullets (`manual`), in all three sections.** Every fact in a manual
bullet must survive. A manual bullet about a project is folded into that project's
bullet. A manual bullet with no project stays as its own bullet, in the user's words.
The `manual` text can hold bullets from an earlier `/magpie` run: merge them, never
duplicate them.

## Step 3: Write

```bash
python3 ~/.claude/skills/magpie/daily.py write --date <YYYY-MM-DD> <<'EOF'
{"did": ["..."], "blocked": ["..."], "next": ["..."]}
EOF
```

Each list holds bullet strings without the leading `- `. `did` must not be empty.
The command prints the old sections. If it fails, show the error and stop.

## Step 4: Report

Show the new note sections as they are now in the file, then one line: what changed
compared with the old sections (for example "3 bullets added, your 2 bullets merged").
Nothing else.

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
python3 ~/.claude/skills/magpie/daily.py write --week --date <start> <<'EOF'
{"moved": ["..."], "blocked": ["..."], "focus": ["..."]}
EOF
```

Pass the `start` date of the week payload, so that the write goes to the same week as
Step W1.

`moved` must not be empty. If the command fails, show the error and stop. Then show the
weekly note as it is in the file, and one line: which days were filled, which had no
activity, and what changed compared with the old sections.
