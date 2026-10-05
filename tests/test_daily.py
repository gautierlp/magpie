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
