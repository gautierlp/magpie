from datetime import date

import daily_week

DAY = "# {d}\n\n**Did:**\n\n- {did}\n\n**Blocked:**\n\n**Next:**\n"


def _daily(vault, iso, text):
    folder = vault / "50 Journal" / "daily"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{iso}.md").write_text(text, encoding="utf-8")


def test_week_bounds_runs_monday_to_sunday():
    assert daily_week.week_bounds(date(2026, 10, 14)) == (date(2026, 10, 12), date(2026, 10, 18))
    assert daily_week.week_bounds(date(2026, 10, 12)) == (date(2026, 10, 12), date(2026, 10, 18))
    assert daily_week.week_bounds(date(2026, 10, 18)) == (date(2026, 10, 12), date(2026, 10, 18))


def test_week_id_uses_the_iso_year_and_week():
    assert daily_week.week_id(date(2026, 10, 14)) == "2026-W42"
    assert daily_week.week_id(date(2026, 12, 31)) == "2026-W53"
    assert daily_week.week_id(date(2027, 1, 4)) == "2027-W01"


def test_note_path_and_blank(tmp_path):
    day = date(2026, 10, 14)
    assert daily_week.note_path(tmp_path, day) == tmp_path / "50 Journal" / "weekly" / "2026-W42.md"
    assert daily_week.blank(day) == (
        "# 2026-W42 (2026-10-12 to 2026-10-18)\n\n"
        "**Moved:**\n**Still blocked:**\n**Focus:**\n"
    )


def test_read_days_gives_each_status(tmp_path):
    _daily(tmp_path, "2026-10-12", DAY.format(d="2026-10-12", did="wrote the spec"))
    _daily(tmp_path, "2026-10-13", "# 2026-10-13\n\n**Did:** \n**Blocked:** \n**Next:** \n")
    _daily(tmp_path, "2026-10-14", "# 2026-10-14\n\nno markers here\n")
    days, errors = daily_week.read_days(tmp_path, date(2026, 10, 14), today=date(2026, 10, 16))
    assert [d["status"] for d in days] == [
        "ok", "missing", "unreadable", "missing", "missing", "future", "future"]
    assert days[0] == {"date": "2026-10-12", "status": "ok",
                       "did": "- wrote the spec", "blocked": "", "next": ""}
    assert days[1] == {"date": "2026-10-13", "status": "missing"}
    assert "missing marker" in errors["2026-10-14"]


def test_cards_named_matches_a_link_or_a_whole_word_name():
    cards = [
        {"name": "site", "link": "[[10 Projects/site/_project|site]]", "repos": ["x"],
         "next_action": "ship", "open_decisions": "none.", "folder": "/tmp/x"},
        {"name": "dog", "link": "[[20 Areas/dog/_area|dog]]", "repos": [],
         "next_action": None, "open_decisions": None, "folder": "/tmp/y"},
        {"name": "house", "link": "[[10 Projects/house/_project|house]]", "repos": [],
         "next_action": "measure", "open_decisions": "roof", "folder": "/tmp/z"},
    ]
    days = [
        {"date": "2026-10-12", "status": "ok", "did": "- [[10 Projects/site/_project|site]]: form",
         "blocked": "", "next": "- dog: book the vet"},
        {"date": "2026-10-13", "status": "missing"},
        {"date": "2026-10-14", "status": "ok", "did": "- read about housekeeping", "blocked": "", "next": ""},
    ]
    assert daily_week.cards_named(cards, days) == [
        {"name": "site", "link": "[[10 Projects/site/_project|site]]",
         "next_action": "ship", "open_decisions": "none."},
        {"name": "dog", "link": "[[20 Areas/dog/_area|dog]]",
         "next_action": None, "open_decisions": None},
    ]
