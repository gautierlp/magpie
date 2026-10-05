import transcript


def test_iter_records_skips_blank_and_corrupt_lines():
    records = list(transcript.iter_records("tests/fixtures/basic.jsonl"))
    assert len(records) == 2
    assert records[0]["type"] == "user"
    assert records[1]["type"] == "assistant"


def _load(name):
    return list(transcript.iter_records(f"tests/fixtures/{name}"))


def test_is_human_turn_true_for_string_and_text_block():
    recs = _load("blocks.jsonl")
    assert transcript.is_human_turn(recs[0]) is True   # string content
    assert transcript.is_human_turn(recs[2]) is True   # text block


def test_is_human_turn_false_for_tool_result_and_assistant():
    recs = _load("blocks.jsonl")
    assert transcript.is_human_turn(recs[1]) is False  # tool_result
    assert transcript.is_human_turn(recs[3]) is False  # assistant


def test_human_text_extracts_string_and_block():
    recs = _load("blocks.jsonl")
    assert transcript.human_text(recs[0]) == "typed by human"
    assert transcript.human_text(recs[2]) == "human via block"


def test_assistant_blocks_returns_block_list():
    recs = _load("blocks.jsonl")
    blocks = transcript.assistant_blocks(recs[3])
    assert [b["type"] for b in blocks] == ["thinking", "text", "tool_use"]
    assert transcript.assistant_blocks(recs[0]) == []


def test_tool_results_and_result_text():
    recs = _load("blocks.jsonl")
    results = list(transcript.tool_results(recs[1]))
    assert len(results) == 1
    assert results[0]["is_error"] is True
    assert transcript.result_text(results[0]) == "boom failed"


from datetime import datetime, timezone


def test_parse_ts_handles_z_and_bad_input():
    assert transcript.parse_ts("2026-07-01T09:00:00.000Z") == datetime(2026, 7, 1, 9, tzinfo=timezone.utc)
    assert transcript.parse_ts("") is None
    assert transcript.parse_ts("garbage") is None


def test_is_injected_flags_harness_text_only():
    assert transcript.is_injected("<command-name>/clear</command-name>")
    assert transcript.is_injected("Base directory for this skill: /x")
    assert not transcript.is_injected("fix the parser")


def test_iter_records_survives_an_invalid_utf8_byte(tmp_path):
    path = tmp_path / "cut.jsonl"
    good = b'{"type": "user", "n": 1}\n'
    bad = b'{"type": "user", "text": "caf\xc3"}\n'
    path.write_bytes(good + bad + b'{"type": "assistant", "n": 2}\n')
    records = list(transcript.iter_records(path))
    assert [r["type"] for r in records] == ["user", "user", "assistant"]
    assert records[0]["n"] == 1 and records[2]["n"] == 2
