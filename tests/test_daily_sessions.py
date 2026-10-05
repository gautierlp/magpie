import json
import tempfile
from pathlib import Path
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
              "<command-message>magpie</command-message>\n<command-name>/magpie</command-name>"),
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


def test_a_session_in_the_system_temp_folder_is_dropped(tmp_path):
    temp_cwd = str(Path(tempfile.gettempdir()) / "superset-bg" / "run")
    _write(tmp_path / "p" / "bg.jsonl", [_user("2026-10-05T09:00:00Z", "background", cwd=temp_cwd)])
    _write(tmp_path / "p" / "ok.jsonl", [_user("2026-10-05T09:00:00Z", "real", cwd="/w/alpha")])
    sessions, _ = daily_sessions.sessions_for_day(tmp_path, START, END, VAULT)
    assert [s["id"] for s in sessions] == ["ok"]
