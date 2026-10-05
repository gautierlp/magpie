"""Local git facts for the daily note: repos, origin names, and the day's commits."""
import subprocess
from pathlib import Path


def run_git(repo, *args):
    """Run git in `repo`. Return stdout, or None when git fails or is missing."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=20
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def repo_name(url):
    """'https://github.com/me/alpha.git' and 'git@github.com:me/alpha' both give 'alpha'."""
    tail = url.strip().rstrip("/").split("/")[-1].split(":")[-1]
    return tail.removesuffix(".git")


def origin_name(path):
    out = run_git(path, "remote", "get-url", "origin")
    return repo_name(out) if out and out.strip() else None


def find_repos(root, extra=()):
    root = Path(root)
    repos = [p for p in sorted(root.iterdir()) if (p / ".git").exists()] if root.is_dir() else []
    return repos + [Path(e) for e in extra if (Path(e) / ".git").exists()]


def author_email():
    out = run_git(Path.home(), "config", "--global", "user.email")
    return out.strip() if out and out.strip() else None


def commits_for_day(repo, start, end, author):
    """Subjects of `author`'s commits in [start, end), newest first. None if git fails.

    `--all` covers branches made in Superset workspaces, because a worktree shares
    the main clone's refs. The stash is excluded: its commits are not work.
    """
    out = run_git(
        repo, "log", "--exclude=refs/stash", "--all",
        f"--since={start.isoformat()}", f"--until={end.isoformat()}",
        f"--author={author}", "--format=%s",
    )
    if out is None:
        return None
    return list(dict.fromkeys(line for line in out.splitlines() if line.strip()))
