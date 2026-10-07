from datetime import date

import daily_vault

PROJECT_CARD = (
    "---\nstatus: active\nrepo: https://github.com/me/vault\n---\n# Vault setup\n"
    "**Next action:** rewrite the finance notes.\n**Open decisions:** none.\n"
)
AREA_CARD = (
    "---\ntype: area\nrepo: https://github.com/me/alpha, https://github.com/me/beta.git\n"
    "---\n# Learning\n**Current goals:** code.\n"
)


def _vault(tmp_path):
    project = tmp_path / "10 Projects" / "vault-setup"
    (project / "log").mkdir(parents=True)
    (project / "_project.md").write_text(PROJECT_CARD, encoding="utf-8")
    (project / "log" / "2026-10-05.md").write_text("# 2026-10-05\n\nWrote the spec.\n", encoding="utf-8")
    area = tmp_path / "20 Areas" / "learning"
    area.mkdir(parents=True)
    (area / "_area.md").write_text(AREA_CARD, encoding="utf-8")
    return tmp_path


def test_load_cards_reads_links_repos_and_fields(tmp_path):
    cards = daily_vault.load_cards(_vault(tmp_path))
    assert [c["name"] for c in cards] == ["vault-setup", "learning"]
    project, area = cards
    assert project["link"] == "[[10 Projects/vault-setup/_project|vault-setup]]"
    assert project["repos"] == ["vault"]
    assert project["next_action"] == "rewrite the finance notes."
    assert project["open_decisions"] == "none."
    assert area["link"] == "[[20 Areas/learning/_area|learning]]"
    assert area["repos"] == ["alpha", "beta"]
    assert area["next_action"] is None


def test_logs_for_day_maps_a_card_to_its_log_text(tmp_path):
    cards = daily_vault.load_cards(_vault(tmp_path))
    assert daily_vault.logs_for_day(cards, date(2026, 10, 5)) == {
        "vault-setup": ["# 2026-10-05\n\nWrote the spec.\n"]
    }
    assert daily_vault.logs_for_day(cards, date(2026, 10, 4)) == {}


from daily_vault import next_action


def test_next_action_reads_the_box_under_the_label():
    text = "# a\n**Next action:**\n- [ ] Read the runs ⏫ 📅 2026-10-09\n**Open decisions:** none.\n"
    assert next_action(text) == "Read the runs"


def test_next_action_keeps_the_one_line_form():
    assert next_action("**Next action:** rewrite the notes.\n") == "rewrite the notes."


def test_next_action_is_none_when_ticked_or_missing():
    assert next_action("**Next action:**\n- [x] done\n") is None
    assert next_action("**Next action:**\n**Open decisions:** none.\n") is None
    assert next_action("# no label\n") is None
