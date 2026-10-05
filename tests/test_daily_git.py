import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

import daily_git

PARIS = ZoneInfo("Europe/Paris")
START = datetime(2026, 10, 5, tzinfo=PARIS)
END = datetime(2026, 10, 6, tzinfo=PARIS)


def _git(repo, *args, env=None):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


def _repo(path, origin="https://github.com/me/alpha.git"):
    path.mkdir()
    _git(path, "init", "-q", "-b", "main")
    if origin:
        _git(path, "remote", "add", "origin", origin)
    return path


def _commit(repo, message, when, email="me@x.com"):
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Me",
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": "Me",
        "GIT_COMMITTER_EMAIL": email,
        "GIT_AUTHOR_DATE": when,
        "GIT_COMMITTER_DATE": when,
    }
    _git(repo, "-c", "commit.gpgsign=false", "commit", "--allow-empty", "--no-verify",
         "-q", "-m", message, env=env)


def test_repo_name_handles_https_ssh_and_git_suffix():
    assert daily_git.repo_name("https://github.com/me/alpha.git\n") == "alpha"
    assert daily_git.repo_name("git@github.com:me/beta.git") == "beta"
    assert daily_git.repo_name("https://github.com/me/gamma/") == "gamma"


def test_find_repos_lists_git_folders_then_extras(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    alpha = _repo(root / "alpha")
    (root / "notes").mkdir()
    dot = _repo(tmp_path / "dot", origin=None)
    assert daily_git.find_repos(root, [dot, tmp_path / "missing"]) == [alpha, dot]


def test_commits_for_day_filters_the_day_and_the_author(tmp_path):
    repo = _repo(tmp_path / "alpha")
    _commit(repo, "before", "2026-10-04T23:30:00+02:00")
    _commit(repo, "on the day", "2026-10-05T10:00:00+02:00")
    _commit(repo, "late on the day", "2026-10-05T23:30:00+02:00")
    _commit(repo, "someone else", "2026-10-05T11:00:00+02:00", email="other@x.com")
    _commit(repo, "after", "2026-10-06T00:30:00+02:00")
    assert daily_git.commits_for_day(repo, START, END, "me@x.com") == [
        "late on the day",
        "on the day",
    ]


def test_commits_for_day_returns_none_when_git_fails(tmp_path):
    assert daily_git.commits_for_day(tmp_path / "nope", START, END, "me@x.com") is None


def test_origin_name(tmp_path):
    assert daily_git.origin_name(_repo(tmp_path / "alpha")) == "alpha"
    assert daily_git.origin_name(_repo(tmp_path / "bare", origin=None)) is None
