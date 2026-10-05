"""ActivityWatch time for the daily note: active app, window and web time, filtered."""
import collections
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta

from transcript import parse_ts

BROWSER_APPS = {"Google Chrome"}
MIN_MINUTES = 2
TOP = 20
TITLE_CHARS = 100


def _excluded(domain, exclude):
    return any(domain == d or domain.endswith("." + d) for d in exclude)


def _span(event):
    begin = parse_ts(event["timestamp"])
    return begin, begin + timedelta(seconds=event["duration"])


def _active_seconds(event, active):
    begin, finish = _span(event)
    total = 0.0
    for low, high in active:
        overlap = (min(finish, high) - max(begin, low)).total_seconds()
        if overlap > 0:
            total += overlap
    return total


def summarize(window, afk, web, exclude, min_minutes=MIN_MINUTES, top=TOP):
    """Rows of active time grouped by app plus title, and by domain plus page title.

    Chrome window rows are dropped when web rows exist: the web rows carry the
    same time with a domain, and the exclude list can only filter domains.
    """
    active = [_span(e) for e in afk if e["data"].get("status") == "not-afk"]
    seconds = collections.Counter()
    for event in window:
        app = event["data"].get("app", "")
        if web and app in BROWSER_APPS:
            continue
        title = (event["data"].get("title") or "")[:TITLE_CHARS]
        seconds[("app", app, title)] += _active_seconds(event, active)
    for event in web:
        domain = (urllib.parse.urlsplit(event["data"].get("url", "")).hostname or "").lower()
        if not domain or _excluded(domain, exclude):
            continue
        title = (event["data"].get("title") or "")[:TITLE_CHARS]
        seconds[("web", domain, title)] += _active_seconds(event, active)
    kept = sorted(
        ((total, key) for key, total in seconds.items() if total >= min_minutes * 60),
        key=lambda pair: -pair[0],
    )
    return [
        {"kind": kind, "name": name, "title": title, "minutes": round(total / 60)}
        for total, (kind, name, title) in kept[:top]
    ]


def _fetch(base, bucket, start, end, timeout):
    query = urllib.parse.urlencode({"start": start.isoformat(), "end": end.isoformat(), "limit": -1})
    url = f"{base}/buckets/{urllib.parse.quote(bucket)}/events?{query}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.load(response)
    except (urllib.error.URLError, OSError, ValueError):
        return None


def gather_activity(base, host, start, end, exclude, timeout=2.0):
    """Return (rows, "ok"), or (None, "unavailable") when the server does not answer."""
    window = _fetch(base, f"aw-watcher-window_{host}", start, end, timeout)
    afk = _fetch(base, f"aw-watcher-afk_{host}", start, end, timeout)
    if window is None or afk is None:
        return None, "unavailable"
    web = _fetch(base, f"aw-watcher-web-chrome_{host}", start, end, timeout) or []
    return summarize(window, afk, web, exclude), "ok"
