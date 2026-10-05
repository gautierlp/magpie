# src/daily.py
"""/magpie: gather the day's traceable work, and write the daily note's sections."""
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
    name = daily_git.origin_name(path)
    if name:
        return name
    parts = path.parts
    for i, part in enumerate(parts[:-2]):
        if part == ".superset" and parts[i + 1] == "worktrees":
            return parts[i + 2]
    return path.name


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
    def printed(obj):
        return json.dumps(obj, ensure_ascii=False, indent=2)

    while len(printed(payload)) > limit:
        candidates = [g for g in payload["groups"] if any(s["turns"] for s in g["sessions"])]
        if not candidates:
            break
        largest = max(candidates, key=lambda g: len(printed(g["sessions"])))
        session = max(largest["sessions"], key=lambda s: len(s["turns"]))
        session["turns"].pop()
    return payload


def gather(args):
    day = args.date
    start, end = _day_bounds(day, args.tz)
    vault = Path(args.vault)
    errors = {}

    def guarded(source, fallback, call):
        """Run one source. A failure is recorded and the fallback used, never raised."""
        try:
            return call()
        except Exception as exc:
            errors[source] = f"{type(exc).__name__}: {exc}"
            return fallback

    def read_vault():
        cards = daily_vault.load_cards(vault)
        return cards, daily_vault.logs_for_day(cards, day)

    def read_git():
        author = args.author or daily_git.author_email()
        commits, skipped = [], []
        for repo in daily_git.find_repos(args.repos_root, args.extra_repo):
            subjects = daily_git.commits_for_day(repo, start, end, author) if author else []
            if subjects is None:
                skipped.append(repo.name)
            elif subjects:
                commits.append((daily_git.origin_name(repo) or repo.name, subjects))
        return commits, skipped

    cards, logs = guarded("vault", ([], {}), read_vault)
    commits, skipped = guarded("git", ([], []), read_git)
    sessions, covered = guarded(
        "sessions", ([], []),
        lambda: daily_sessions.sessions_for_day(args.projects_dir, start, end, vault))
    activity, activity_status = guarded(
        "activity", (None, "error"),
        lambda: daily_aw.gather_activity(args.aw_url, args.host, start, end, args.exclude))
    mail, mail_status = guarded(
        "mail", ([], {}), lambda: daily_mail.gather_mail(args.mail_account, day))

    path = daily_note.note_path(vault, day, args.journal_dir)
    manual = {"did": "", "blocked": "", "next": ""}
    if path.exists():
        try:
            manual = daily_note.read_sections(path.read_text(encoding="utf-8"))
        except ValueError:
            pass

    payload = {
        "date": day.isoformat(),
        "timezone": args.tz,
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
        "errors": errors,
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
