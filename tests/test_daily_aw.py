import json
import socket
import threading
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo

import pytest

import daily_aw

PARIS = ZoneInfo("Europe/Paris")
START = datetime(2026, 10, 5, tzinfo=PARIS)
END = datetime(2026, 10, 6, tzinfo=PARIS)


def _ev(ts, seconds, **data):
    return {"timestamp": ts, "duration": seconds, "data": data}


AFK = [
    _ev("2026-10-05T08:00:00+00:00", 3600, status="not-afk"),
    _ev("2026-10-05T09:00:00+00:00", 3600, status="afk"),
]


def test_summarize_counts_only_active_time():
    window = [_ev("2026-10-05T08:30:00+00:00", 3600, app="Code", title="daily.py")]
    assert daily_aw.summarize(window, AFK, [], set()) == [
        {"kind": "app", "name": "Code", "title": "daily.py", "minutes": 30}
    ]


def test_summarize_drops_groups_under_two_minutes_and_keeps_top_n():
    window = [
        _ev("2026-10-05T08:00:00+00:00", 90, app="Tiny", title="t"),
        _ev("2026-10-05T08:05:00+00:00", 600, app="A", title="a"),
        _ev("2026-10-05T08:20:00+00:00", 300, app="B", title="b"),
        _ev("2026-10-05T08:30:00+00:00", 180, app="C", title="c"),
    ]
    rows = daily_aw.summarize(window, AFK, [], set(), top=2)
    assert [(r["name"], r["minutes"]) for r in rows] == [("A", 10), ("B", 5)]


def test_summarize_web_shows_domains_only_and_applies_the_exclude_list():
    web = [
        _ev("2026-10-05T08:00:00+00:00", 600, url="https://github.com/me/alpha/pull/3?x=1", title="PR 3"),
        _ev("2026-10-05T08:10:00+00:00", 600, url="https://www.mybank.fr/account", title="Balance"),
    ]
    window = [_ev("2026-10-05T08:00:00+00:00", 1200, app="Google Chrome", title="PR 3")]
    assert daily_aw.summarize(window, AFK, web, {"mybank.fr"}) == [
        {"kind": "web", "name": "github.com", "title": "PR 3", "minutes": 10}
    ]


def test_summarize_skips_incognito_web_events():
    web = [
        _ev("2026-10-05T08:00:00+00:00", 600, url="https://secret.example/x", title="s", incognito=True),
        _ev("2026-10-05T08:10:00+00:00", 600, url="https://github.com/a", title="PR", incognito=False),
    ]
    rows = daily_aw.summarize([], AFK, web, set())
    assert [r["name"] for r in rows] == ["github.com"]


def test_summarize_drops_browser_window_rows_even_without_web_rows():
    window = [
        _ev("2026-10-05T08:00:00+00:00", 600, app="Google Chrome", title="Bank"),
        _ev("2026-10-05T08:10:00+00:00", 600, app="Safari", title="Private page"),
        _ev("2026-10-05T08:20:00+00:00", 600, app="Code", title="daily.py"),
    ]
    rows = daily_aw.summarize(window, AFK, [], set())
    assert [r["name"] for r in rows] == ["Code"]


def test_summarize_ignores_an_event_with_an_unparseable_timestamp():
    window = [
        _ev(None, 600, app="Code", title="bad"),
        _ev("2026-10-05T08:00:00+00:00", 600, app="Code", title="good"),
    ]
    rows = daily_aw.summarize(window, AFK, [], set())
    assert rows == [{"kind": "app", "name": "Code", "title": "good", "minutes": 10}]


class _Handler(BaseHTTPRequestHandler):
    routes = {}

    def do_GET(self):
        body = self.routes.get(urllib.parse.urlsplit(self.path).path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def aw_url():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/api/0"
    server.shutdown()
    server.server_close()


def test_gather_activity_reads_the_buckets(aw_url):
    _Handler.routes = {
        "/api/0/buckets/aw-watcher-window_host1/events":
            [_ev("2026-10-05T08:00:00+00:00", 600, app="Code", title="x")],
        "/api/0/buckets/aw-watcher-afk_host1/events": AFK,
    }
    rows, status = daily_aw.gather_activity(aw_url, "host1", START, END, set())
    assert status == "ok"
    assert rows == [{"kind": "app", "name": "Code", "title": "x", "minutes": 10}]


def test_gather_activity_without_a_server_is_unavailable():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    url = f"http://127.0.0.1:{port}/api/0"
    assert daily_aw.gather_activity(url, "h", START, END, set()) == (None, "unavailable")
