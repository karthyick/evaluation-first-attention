"""Unit tests for LLM client JSON utilities and TokenTracker — Karthick Raja M, 2026."""

import pytest

from efa.llm_client import TokenTracker, _extract_json, _repair_json


# ---------------------------------------------------------------------------
# _repair_json
# ---------------------------------------------------------------------------


def test_repair_json_trailing_comma():
    """Trailing comma before } is removed."""
    raw = '{"a": 1,}'
    repaired = _repair_json(raw)
    import json

    result = json.loads(repaired)
    assert result == {"a": 1}


def test_repair_json_trailing_comma_array():
    """Trailing comma before ] is removed."""
    raw = "[1, 2,]"
    repaired = _repair_json(raw)
    import json

    result = json.loads(repaired)
    assert result == [1, 2]


def test_repair_json_control_chars():
    """Control characters 0x00-0x08, 0x0b, 0x0c, 0x0e-0x1f are stripped.
    Newline (0x0a) and tab (0x09) must be preserved."""
    # BEL (0x07) and SOH (0x01) in a position that does not break JSON structure.
    # Newline and tab outside string values so the result remains valid JSON.
    raw = '\x07\x01{"key": "value"}'
    repaired = _repair_json(raw)
    assert "\x07" not in repaired
    assert "\x01" not in repaired
    # Newline and tab outside strings are harmless whitespace — verify they survive
    raw2 = '{"a": 1\x0c,\n\t"b": 2}'
    repaired2 = _repair_json(raw2)
    assert "\x0c" not in repaired2  # form feed stripped
    assert "\n" in repaired2        # newline preserved
    assert "\t" in repaired2        # tab preserved
    import json

    result = json.loads(repaired2)
    assert result == {"a": 1, "b": 2}


def test_repair_json_single_quotes():
    """Single quotes are replaced with double quotes when no double quotes present."""
    raw = "{'a': 'b'}"
    repaired = _repair_json(raw)
    import json

    result = json.loads(repaired)
    assert result == {"a": "b"}


def test_repair_json_single_quotes_not_applied_when_double_quotes_present():
    """Single-quote replacement is skipped when double quotes already exist.
    This prevents corrupting valid JSON that also contains single-quoted contractions."""
    raw = '{"key": "it\'s fine"}'
    repaired = _repair_json(raw)
    # String must be unchanged — double quotes were present
    assert repaired == raw


def test_repair_json_preserves_valid():
    """Valid JSON passes through _repair_json without alteration."""
    valid = '{"score": 4, "reasoning": "good answer"}'
    assert _repair_json(valid) == valid


# ---------------------------------------------------------------------------
# _extract_json
# ---------------------------------------------------------------------------


def test_extract_json_direct_object():
    """Clean JSON object string is parsed directly."""
    result = _extract_json('{"score": 4}')
    assert result == {"score": 4}


def test_extract_json_direct_array():
    """Clean JSON array string is parsed directly."""
    result = _extract_json('[{"name": "x"}]')
    assert result == [{"name": "x"}]


def test_extract_json_with_think_tags():
    """<think>...</think> blocks are stripped before parsing."""
    text = "<think>some long reasoning here\nmultiline</think>  {\"score\": 3}"
    result = _extract_json(text)
    assert result == {"score": 3}


def test_extract_json_with_code_fences():
    """Markdown code fences (``` and ```json) are stripped."""
    text = "```json\n{\"score\": 5}\n```"
    result = _extract_json(text)
    assert result == {"score": 5}


def test_extract_json_with_code_fences_no_lang():
    """Plain ``` fences without language tag are also stripped."""
    text = "```\n{\"score\": 2}\n```"
    result = _extract_json(text)
    assert result == {"score": 2}


def test_extract_json_with_preamble():
    """Leading prose before JSON object is ignored."""
    text = 'Here is the result: {"score": 4}'
    result = _extract_json(text)
    assert result == {"score": 4}


def test_extract_json_nested_objects():
    """Nested JSON structures are parsed correctly."""
    text = '{"outer": {"inner": [1, 2, 3], "flag": true}}'
    result = _extract_json(text)
    assert result == {"outer": {"inner": [1, 2, 3], "flag": True}}


def test_extract_json_no_json_raises():
    """Plain text with no JSON raises ValueError."""
    with pytest.raises(ValueError, match="No JSON found"):
        _extract_json("no json here")


def test_extract_json_array_of_objects():
    """Array of objects is parsed even when trailing text follows the closing ]."""
    text = '[{"name": "Clarity"}, {"name": "Accuracy"}] done'
    result = _extract_json(text)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["name"] == "Clarity"
    assert result[1]["name"] == "Accuracy"


def test_extract_json_array_of_objects_fallback():
    """When the outer [] is malformed but inner objects are valid, they are recovered."""
    # Simulate a truncated array where the closing ] is missing — the fallback
    # object-scanning path should still collect all complete {...} blocks.
    text = '[{"name": "A"}, {"name": "B"}'
    result = _extract_json(text)
    assert isinstance(result, list)
    assert any(item.get("name") == "A" for item in result)
    assert any(item.get("name") == "B" for item in result)


def test_extract_json_think_tags_multiline():
    """Multi-line think blocks spanning many lines are fully stripped."""
    text = (
        "<think>\n"
        "Step 1: consider the answer.\n"
        "Step 2: finalize.\n"
        "</think>\n"
        '[{"score": 5, "reasoning": "great"}]'
    )
    result = _extract_json(text)
    assert result == [{"score": 5, "reasoning": "great"}]


# ---------------------------------------------------------------------------
# TokenTracker
# ---------------------------------------------------------------------------


def test_token_tracker_add():
    """add() accumulates prompt and completion tokens correctly."""
    tracker = TokenTracker()
    tracker.add({"prompt_tokens": 100, "completion_tokens": 50})
    assert tracker.prompt_tokens == 100
    assert tracker.completion_tokens == 50
    assert tracker.total == 150

    tracker.add({"prompt_tokens": 200, "completion_tokens": 75})
    assert tracker.prompt_tokens == 300
    assert tracker.completion_tokens == 125
    assert tracker.total == 425


def test_token_tracker_add_missing_keys():
    """add() handles dicts with missing keys gracefully (defaults to 0)."""
    tracker = TokenTracker()
    tracker.add({})
    assert tracker.prompt_tokens == 0
    assert tracker.completion_tokens == 0
    assert tracker.total == 0


def test_token_tracker_add_partial_keys():
    """add() handles dict with only one key."""
    tracker = TokenTracker()
    tracker.add({"prompt_tokens": 42})
    assert tracker.prompt_tokens == 42
    assert tracker.completion_tokens == 0


def test_token_tracker_reset():
    """reset() zeros out both counters."""
    tracker = TokenTracker()
    tracker.add({"prompt_tokens": 500, "completion_tokens": 300})
    assert tracker.total == 800

    tracker.reset()
    assert tracker.prompt_tokens == 0
    assert tracker.completion_tokens == 0
    assert tracker.total == 0


def test_token_tracker_reset_then_accumulate():
    """After reset, add() accumulates from zero correctly."""
    tracker = TokenTracker()
    tracker.add({"prompt_tokens": 100, "completion_tokens": 50})
    tracker.reset()
    tracker.add({"prompt_tokens": 10, "completion_tokens": 5})
    assert tracker.total == 15
