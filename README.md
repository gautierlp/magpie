# magpie

A magpie collects shiny bits from everywhere and keeps them in one nest. This
Claude Code skill does the same with your day. Run `/daily` in the evening, and it
drafts your Obsidian daily note from what you actually did: it fills **Did:**,
**Blocked:** and **Next:**, and you edit the draft.

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
