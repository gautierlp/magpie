import subprocess
from datetime import date

import daily_mail

HEADERS = (
    b"Date: Mon, 05 Oct 2026 10:00:00 +0200\r\n"
    b"To: Abby Smith <abby@x.com>, bob@y.com\r\n"
    b"Subject: =?utf-8?q?Facture_d=C3=A9cembre?=\r\n\r\n"
)
GMAIL_FOLDERS = [
    b'(\\HasNoChildren) "/" "INBOX"',
    b'(\\HasNoChildren \\Sent) "/" "[Gmail]/Messages envoy&AOk-s"',
]
DAY = date(2026, 10, 5)


class FakeIMAP:
    def __init__(self, folders, ids=b"1"):
        self.folders = folders
        self.ids = ids
        self.calls = []

    def list(self):
        return "OK", self.folders

    def select(self, mailbox, readonly=False):
        self.calls.append(("select", mailbox, readonly))
        return "OK", [b"1"]

    def search(self, charset, *criteria):
        self.calls.append(("search", criteria))
        return "OK", [self.ids]

    def fetch(self, ids, spec):
        self.calls.append(("fetch", ids, spec))
        return "OK", [(b"1 (BODY[HEADER.FIELDS (DATE TO SUBJECT)] {120}", HEADERS), b")"]

    def logout(self):
        self.calls.append(("logout",))


def test_sent_for_day_reads_headers_only():
    conn = FakeIMAP(GMAIL_FOLDERS)
    assert daily_mail.sent_for_day(conn, DAY) == [{"to": "Abby Smith, bob", "subject": "Facture décembre"}]
    assert ("select", '"[Gmail]/Messages envoy&AOk-s"', True) in conn.calls
    assert ("search", ("SINCE", "05-Oct-2026", "BEFORE", "06-Oct-2026")) in conn.calls
    fetch = next(call for call in conn.calls if call[0] == "fetch")
    assert fetch[2] == "(BODY.PEEK[HEADER.FIELDS (DATE TO SUBJECT)])"


def test_sent_for_day_without_a_sent_folder_returns_none():
    assert daily_mail.sent_for_day(FakeIMAP([b'(\\HasNoChildren) "/" "INBOX"']), DAY) is None


def test_sent_for_day_with_no_mail_returns_empty():
    assert daily_mail.sent_for_day(FakeIMAP(GMAIL_FOLDERS, ids=b""), DAY) == []


def test_gather_mail_reports_a_status_per_account():
    rows, status = daily_mail.gather_mail(
        ["a@x.com", "b@x.com"], DAY,
        password_fn=lambda address: "pw" if address == "a@x.com" else None,
        connect=lambda address, password: FakeIMAP(GMAIL_FOLDERS),
    )
    assert status == {"a@x.com": "ok", "b@x.com": "no password"}
    assert rows == [{"account": "a@x.com", "to": "Abby Smith, bob", "subject": "Facture décembre"}]


def test_gather_mail_survives_a_login_error():
    def connect(address, password):
        raise daily_mail.imaplib.IMAP4.error("AUTHENTICATIONFAILED")

    rows, status = daily_mail.gather_mail(["a@x.com"], DAY, password_fn=lambda a: "pw", connect=connect)
    assert rows == []
    assert status == {"a@x.com": "error: imap"}


def test_keychain_password_uses_the_security_cli():
    calls = []

    def runner(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="secret\n", stderr="")

    assert daily_mail.keychain_password("a@x.com", runner=runner) == "secret"
    assert calls == [["security", "find-generic-password", "-s", "daily-imap", "-a", "a@x.com", "-w"]]


def test_keychain_password_returns_none_when_security_is_missing():
    def runner(cmd, **kwargs):
        raise FileNotFoundError("security binary not found")

    assert daily_mail.keychain_password("a@x.com", runner=runner) is None
