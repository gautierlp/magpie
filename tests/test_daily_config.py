import json

import pytest

import daily_config


def test_load_returns_the_defaults_for_a_missing_file(tmp_path):
    assert daily_config.load(tmp_path / "none.json") == daily_config.DEFAULTS


def test_load_merges_the_file_over_the_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"timezone": "Europe/Paris", "calendars": ["a@x.com"]}), encoding="utf-8")
    cfg = daily_config.load(path)
    assert cfg["timezone"] == "Europe/Paris"
    assert cfg["calendars"] == ["a@x.com"]
    assert cfg["vault"] == "~/vault"


def test_load_rejects_an_unknown_key(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"vaul": "x"}), encoding="utf-8")
    with pytest.raises(ValueError, match="vaul"):
        daily_config.load(path)
