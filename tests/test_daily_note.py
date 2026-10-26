from datetime import date

import pytest

import daily_note

TEMPLATE = "# {{date:YYYY-MM-DD}}\n\n**Did:** \n**Blocked:** \n**Next:** \n"
NOTE = "# 2026-10-05\n\n**Did:** \n\n- set up the vault\n- inbox zero\n**Blocked:** \n**Next:** \n"


def test_read_sections_strips_each_section():
    assert daily_note.read_sections(NOTE) == {
        "did": "- set up the vault\n- inbox zero",
        "blocked": "",
        "next": "",
    }


def test_read_sections_refuses_a_missing_marker():
    with pytest.raises(ValueError, match="Next"):
        daily_note.read_sections("# x\n\n**Did:** \n**Blocked:** \n")


def test_replace_sections_renders_all_three_and_keeps_the_title():
    out = daily_note.replace_sections(NOTE, {"did": ["a", "b"], "blocked": [], "next": ["x"]})
    assert out == "# 2026-10-05\n\n**Did:**\n\n- a\n- b\n\n**Blocked:**\n\n**Next:**\n\n- x\n"


def test_replace_sections_strips_a_leading_dash():
    out = daily_note.replace_sections(NOTE, {"did": ["- a"], "blocked": [], "next": []})
    assert "\n- a\n" in out
    assert "- - a" not in out


def test_replace_sections_refuses_an_empty_did():
    with pytest.raises(ValueError, match="did section is empty"):
        daily_note.replace_sections(NOTE, {"did": [], "blocked": ["x"], "next": []})


def test_from_template_fills_the_date(tmp_path):
    (tmp_path / "90 Templates").mkdir()
    (tmp_path / "90 Templates" / "daily.md").write_text(TEMPLATE, encoding="utf-8")
    assert daily_note.from_template(tmp_path, date(2026, 10, 5)).startswith("# 2026-10-05\n")


def test_note_path(tmp_path):
    expected = tmp_path / "50 Journal" / "daily" / "2026-10-05.md"
    assert daily_note.note_path(tmp_path, date(2026, 10, 5)) == expected


WEEK_NOTE = (
    "# 2026-W42 (2026-10-12 to 2026-10-18)\n\n"
    "**Moved:**\n\n- site: form split\n\n**Still blocked:**\n\n**Focus:**\n\n- fix the blockers\n"
)


def test_read_sections_with_the_weekly_markers():
    assert daily_note.read_sections(WEEK_NOTE, daily_note.WEEKLY) == {
        "moved": "- site: form split",
        "blocked": "",
        "focus": "- fix the blockers",
    }


def test_replace_sections_with_the_weekly_markers_keeps_the_title():
    out = daily_note.replace_sections(
        WEEK_NOTE, {"moved": ["a"], "blocked": ["b"], "focus": []}, daily_note.WEEKLY)
    assert out == (
        "# 2026-W42 (2026-10-12 to 2026-10-18)\n\n"
        "**Moved:**\n\n- a\n\n**Still blocked:**\n\n- b\n\n**Focus:**\n"
    )


def test_replace_sections_refuses_an_empty_moved():
    with pytest.raises(ValueError, match="moved section is empty"):
        daily_note.replace_sections(
            WEEK_NOTE, {"moved": [], "blocked": [], "focus": ["x"]}, daily_note.WEEKLY)


def test_the_daily_markers_are_not_found_in_a_weekly_note():
    with pytest.raises(ValueError, match="Did"):
        daily_note.read_sections(WEEK_NOTE)


TAILED = NOTE + "\n## Notes\n\nkeep this paragraph\n"


def test_read_sections_stops_next_at_the_next_heading():
    assert daily_note.read_sections(TAILED)["next"] == ""


def test_replace_sections_keeps_the_text_below_next():
    out = daily_note.replace_sections(TAILED, {"did": ["a"], "blocked": [], "next": ["x"]})
    assert out == "# 2026-10-05\n\n**Did:**\n\n- a\n\n**Blocked:**\n\n**Next:**\n\n- x\n\n## Notes\n\nkeep this paragraph\n"
