"""Settings for /magpie. Every key is optional; the file only overrides the defaults."""
import copy
import json
import os
from pathlib import Path

DEFAULT_PATH = Path(
    os.environ.get("MAGPIE_CONFIG", "~/.config/magpie/config.json")
).expanduser()

DEFAULTS = {
    "timezone": None,  # IANA name such as "Europe/Paris"; None means the system's local time
    "vault": "~/vault",
    "journal_dir": "50 Journal/daily",
    "template": "90 Templates/daily.md",
    "repos_root": "~/projects",
    "extra_repos": [],
    "activitywatch_url": "http://localhost:5600/api/0",
    "activitywatch_host": None,  # machine name in the bucket IDs; None means this machine
    "exclude_domains": [],
    "mail_accounts": [],
    "calendars": [],
}


def load(path=DEFAULT_PATH):
    cfg = copy.deepcopy(DEFAULTS)
    path = Path(path)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        unknown = sorted(set(data) - set(DEFAULTS))
        if unknown:
            raise ValueError(f"unknown config keys: {', '.join(unknown)}")
        cfg.update(data)
    return cfg
