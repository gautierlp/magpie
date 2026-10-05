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
