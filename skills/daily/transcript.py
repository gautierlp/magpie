import json
from datetime import datetime

# Markers of harness- or skill-injected user text (copied from session_reviewer's signals.py).
_INJECTION_MARKERS = [
    "Base directory for this skill:",
    "<task-notification>",
    "<command-name>",
    "<command-message>",
    "<local-command-stdout>",
    "Caveat: The messages below",
    "[Request interrupted by user",
]


def parse_ts(value):
    """Parse an ISO8601 timestamp (trailing 'Z' allowed) to an aware datetime, or None."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def is_injected(text):
    """True if this user text was injected by the harness or a skill, not typed."""
    return any(marker in text for marker in _INJECTION_MARKERS)


def iter_records(path):
    """Yield parsed JSON records from a .jsonl file.

    Skips blank lines and lines that are not valid JSON, so a single
    corrupt line never aborts a whole session parse.
    """
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _content(record):
    return record.get("message", {}).get("content")


def is_human_turn(record):
    """True if this user record is human-typed text, not a tool result."""
    if record.get("type") != "user":
        return False
    content = _content(record)
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        return any(
            isinstance(b, dict) and b.get("type") == "text" for b in content
        )
    return False


def human_text(record):
    """Return the human's text from a user record, or '' if there is none."""
    content = _content(record)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ]
        return "\n".join(parts)
    return ""


def assistant_blocks(record):
    """Return the content block list for an assistant record, else []."""
    if record.get("type") != "assistant":
        return []
    content = _content(record)
    return content if isinstance(content, list) else []


def tool_results(record):
    """Yield tool_result blocks from a user record."""
    if record.get("type") != "user":
        return
    content = _content(record)
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                yield block


def result_text(block):
    """Flatten a tool_result block's content (str or list) to a string."""
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict)
        )
    return ""
