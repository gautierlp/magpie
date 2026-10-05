"""Sent mail headers for the daily note, read over IMAP. Bodies are never fetched."""
import email
import email.policy
import email.utils
import imaplib
import subprocess
from datetime import timedelta

FETCH_SPEC = "(BODY.PEEK[HEADER.FIELDS (DATE TO SUBJECT)])"
KEYCHAIN_SERVICE = "daily-imap"
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
SUBJECT_CHARS = 150


def keychain_password(address, runner=subprocess.run):
    """The Google app password stored with `security add-generic-password -s daily-imap`."""
    result = runner(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", address, "-w"],
        capture_output=True, text=True,
    )
    secret = result.stdout.strip() if result.returncode == 0 else ""
    return secret or None


def _connect(address, password):
    conn = imaplib.IMAP4_SSL("imap.gmail.com", timeout=15)
    conn.login(address, password)
    return conn


def _sent_folder(conn):
    """Find the sent folder by its \\Sent flag, so a localized label still works."""
    _, lines = conn.list()
    for raw in lines or []:
        line = raw.decode() if isinstance(raw, bytes) else str(raw)
        if "\\Sent" in line:
            return line.rsplit(' "/" ', 1)[-1].strip().strip('"')
    return None


def _imap_date(day):
    return f"{day.day:02d}-{MONTHS[day.month - 1]}-{day.year}"


def sent_for_day(conn, day):
    """Rows of {"to", "subject"} for mail sent on `day`. None if no sent folder."""
    folder = _sent_folder(conn)
    if folder is None:
        return None
    conn.select(f'"{folder}"', readonly=True)
    _, data = conn.search(None, "SINCE", _imap_date(day), "BEFORE", _imap_date(day + timedelta(days=1)))
    ids = (data[0] or b"").split()
    if not ids:
        return []
    _, parts = conn.fetch(",".join(i.decode() for i in ids), FETCH_SPEC)
    rows = []
    for part in parts:
        if not isinstance(part, tuple):
            continue
        message = email.message_from_bytes(part[1], policy=email.policy.default)
        names = [
            name or address.split("@")[0]
            for name, address in email.utils.getaddresses([str(message.get("To", ""))])
        ]
        rows.append({"to": ", ".join(names), "subject": str(message.get("Subject", ""))[:SUBJECT_CHARS]})
    return rows


def gather_mail(accounts, day, password_fn=keychain_password, connect=_connect):
    """Return (rows, status by account). One failing account never stops the others."""
    rows, status = [], {}
    for address in accounts:
        password = password_fn(address)
        if not password:
            status[address] = "no password"
            continue
        try:
            conn = connect(address, password)
            try:
                found = sent_for_day(conn, day)
            finally:
                conn.logout()
        except imaplib.IMAP4.error:
            status[address] = "error: imap"
            continue
        except OSError:
            status[address] = "error: network"
            continue
        if found is None:
            status[address] = "no sent folder"
            continue
        rows.extend({"account": address, **row} for row in found)
        status[address] = "ok"
    return rows, status
