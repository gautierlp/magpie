---
name: magpie
description: Use when the user runs /magpie, or asks to pre-fill, draft or fill the daily note or journal for today or a given day. Gathers the day's vault logs, git commits, Claude Code sessions, ActivityWatch time, calendar events and sent mail, then writes a Did / Blocked / Next draft into the Obsidian daily note.
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
