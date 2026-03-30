"""Unit tests for criteria_generator — Karthick Raja M, 2026."""

from __future__ import annotations

import copy
from unittest.mock import MagicMock, patch

import pytest

from efa.criteria_generator import (
    FIXED_CRITERIA,
    _parse_criteria_response,
    generate_criteria,
)
from efa.llm_client import LLMClient
from efa.models import Criterion


# ---------------------------------------------------------------------------
# _parse_criteria_response
# ---------------------------------------------------------------------------


def test_parse_criteria_dict_format():
    """List of dicts with name/definition/rubric produces Criterion objects."""
    raw = [
        {
            "name": "Clarity",
            "definition": "Response is clear and well-organized.",
            "rubric": {"1": "Very unclear", "2": "Unclear", "3": "OK", "4": "Clear", "5": "Very clear"},
        },
        {
            "name": "Accuracy",
            "definition": "Response contains no factual errors.",
            "rubric": {"1": "Many errors", "2": "Some errors", "3": "Minor errors", "4": "Mostly accurate", "5": "Perfect"},
        },
    ]
    criteria = _parse_criteria_response(raw, n_criteria=2)

    assert len(criteria) == 2
    assert all(isinstance(c, Criterion) for c in criteria)
    assert criteria[0].name == "Clarity"
    assert criteria[1].name == "Accuracy"
    assert criteria[0].definition == "Response is clear and well-organized."


def test_parse_criteria_string_format():
    """List of plain strings produces Criterion objects with a generic rubric."""
    raw = ["Clarity", "Accuracy", "Completeness"]
    criteria = _parse_criteria_response(raw, n_criteria=3)

    assert len(criteria) == 3
    assert all(isinstance(c, Criterion) for c in criteria)
    assert criteria[0].name == "Clarity"
    assert criteria[1].name == "Accuracy"
    # Generic rubric must be assigned
    assert 1 in criteria[0].rubric
    assert 5 in criteria[0].rubric


def test_parse_criteria_empty_list():
    """Empty list returns empty list immediately."""
    result = _parse_criteria_response([], n_criteria=5)
    assert result == []


def test_parse_criteria_not_a_list():
    """Non-list input returns empty list."""
    result = _parse_criteria_response({"name": "bad"}, n_criteria=5)  # type: ignore[arg-type]
    assert result == []


def test_parse_criteria_missing_name():
    """Dicts without a 'name' key are silently skipped."""
    raw = [
        {"definition": "no name here", "rubric": {}},
        {"name": "Accuracy", "definition": "correct info", "rubric": {"1": "bad", "5": "great"}},
    ]
    criteria = _parse_criteria_response(raw, n_criteria=5)
    assert len(criteria) == 1
    assert criteria[0].name == "Accuracy"


def test_parse_criteria_truncates_to_n():
    """Response with more items than n_criteria is truncated."""
    raw = [{"name": f"Criterion {i}", "definition": f"Def {i}", "rubric": {}} for i in range(10)]
    criteria = _parse_criteria_response(raw, n_criteria=3)
    assert len(criteria) == 3
    assert criteria[0].name == "Criterion 0"
    assert criteria[2].name == "Criterion 2"


def test_parse_criteria_weight_is_uniform():
    """Each parsed criterion gets weight = 1.0 / n_criteria."""
    raw = [
        {"name": "A", "definition": "def A", "rubric": {"1": "bad", "5": "great"}},
        {"name": "B", "definition": "def B", "rubric": {"1": "bad", "5": "great"}},
        {"name": "C", "definition": "def C", "rubric": {"1": "bad", "5": "great"}},
    ]
    criteria = _parse_criteria_response(raw, n_criteria=3)
    expected_weight = 1.0 / 3
    for c in criteria:
        assert abs(c.weight - expected_weight) < 1e-9


def test_rubric_parsing_int_keys():
    """Rubric string keys '1', '2', etc. are converted to int keys."""
    raw = [
        {
            "name": "Accuracy",
            "definition": "correct",
            "rubric": {"1": "poor", "2": "below avg", "3": "ok", "4": "good", "5": "excellent"},
        }
    ]
    criteria = _parse_criteria_response(raw, n_criteria=1)
    rubric = criteria[0].rubric
    # All keys must be ints, not strings
    assert all(isinstance(k, int) for k in rubric.keys())
    assert rubric[1] == "poor"
    assert rubric[5] == "excellent"


def test_rubric_parsing_int_key_values_are_strings():
    """Rubric values are coerced to str even if the LLM returned numbers."""
    raw = [
        {
            "name": "Score",
            "definition": "test",
            "rubric": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
        }
    ]
    criteria = _parse_criteria_response(raw, n_criteria=1)
    rubric = criteria[0].rubric
    assert all(isinstance(v, str) for v in rubric.values())


def test_parse_criteria_missing_rubric_produces_empty_rubric():
    """Dict without 'rubric' key yields Criterion with an empty rubric dict.
    The default 5-key rubric is only used when the rubric value is not a dict."""
    raw = [{"name": "Quality", "definition": "overall quality"}]
    criteria = _parse_criteria_response(raw, n_criteria=1)
    assert len(criteria) == 1
    # Missing key → item.get("rubric", {}) → {} → empty rubric after comprehension
    assert criteria[0].rubric == {}


def test_parse_criteria_non_dict_rubric_uses_default():
    """When the rubric field is not a dict (e.g. a string or None), the default
    5-key generic rubric is substituted."""
    raw = [{"name": "Quality", "definition": "overall quality", "rubric": "n/a"}]
    criteria = _parse_criteria_response(raw, n_criteria=1)
    assert len(criteria) == 1
    rubric = criteria[0].rubric
    assert set(rubric.keys()) == {1, 2, 3, 4, 5}


# ---------------------------------------------------------------------------
# FIXED_CRITERIA / generate_criteria(dynamic=False)
# ---------------------------------------------------------------------------


def test_fixed_criteria_returns_copies():
    """generate_criteria(dynamic=False) returns deep copies — FIXED_CRITERIA are not mutated."""
    # Capture original weights
    original_weights = [c.weight for c in FIXED_CRITERIA]

    mock_client = MagicMock(spec=LLMClient)
    result = generate_criteria(mock_client, prompt="test", n_criteria=3, dynamic=False)

    # Mutate the returned copies
    for c in result:
        c.weight = 999.0
        c.locked = True

    # FIXED_CRITERIA must be unchanged
    for orig_c, orig_w in zip(FIXED_CRITERIA, original_weights):
        assert orig_c.weight == orig_w
        assert orig_c.locked is False


def test_fixed_criteria_correct_weights():
    """n_criteria=3 → each weight is exactly 1/3."""
    mock_client = MagicMock(spec=LLMClient)
    result = generate_criteria(mock_client, prompt="test", n_criteria=3, dynamic=False)

    assert len(result) == 3
    expected = 1.0 / 3
    for c in result:
        assert abs(c.weight - expected) < 1e-9


def test_fixed_criteria_different_n():
    """Calling with n=3 then n=5 produces correct weights each time."""
    mock_client = MagicMock(spec=LLMClient)

    result3 = generate_criteria(mock_client, prompt="test", n_criteria=3, dynamic=False)
    result5 = generate_criteria(mock_client, prompt="test", n_criteria=5, dynamic=False)

    assert len(result3) == 3
    assert len(result5) == 5

    for c in result3:
        assert abs(c.weight - 1.0 / 3) < 1e-9
    for c in result5:
        assert abs(c.weight - 1.0 / 5) < 1e-9


def test_fixed_criteria_n1():
    """n_criteria=1 → single criterion with weight 1.0."""
    mock_client = MagicMock(spec=LLMClient)
    result = generate_criteria(mock_client, prompt="test", n_criteria=1, dynamic=False)
    assert len(result) == 1
    assert abs(result[0].weight - 1.0) < 1e-9


def test_fixed_criteria_returns_first_n():
    """Returns the first n items from FIXED_CRITERIA in order."""
    mock_client = MagicMock(spec=LLMClient)
    result = generate_criteria(mock_client, prompt="test", n_criteria=2, dynamic=False)
    assert result[0].name == FIXED_CRITERIA[0].name
    assert result[1].name == FIXED_CRITERIA[1].name


# ---------------------------------------------------------------------------
# generate_criteria(dynamic=False) via client mock
# ---------------------------------------------------------------------------


def test_dynamic_false_uses_fixed():
    """dynamic=False returns fixed criteria without calling the LLM."""
    mock_client = MagicMock(spec=LLMClient)
    mock_client.model = "gpt-4o"
    mock_client.temperature = 0.7
    mock_client.max_tokens = 4096
    mock_client.tracker = MagicMock()
    mock_client.api_base = None
    mock_client.api_key = None
    mock_client.call_delay = 0.0

    result = generate_criteria(mock_client, prompt="Explain photosynthesis", n_criteria=3, dynamic=False)

    # LLM must NOT have been called
    mock_client.complete_json.assert_not_called()
    mock_client.complete.assert_not_called()

    assert len(result) == 3
    assert all(isinstance(c, Criterion) for c in result)


def test_dynamic_true_calls_llm():
    """dynamic=True calls complete_json and parses the result."""
    mock_client = MagicMock(spec=LLMClient)
    mock_client.model = "gpt-4o"
    mock_client.temperature = 0.7
    mock_client.max_tokens = 4096
    mock_client.tracker = MagicMock()
    mock_client.api_base = None
    mock_client.api_key = None
    mock_client.call_delay = 0.0
    mock_client.seed = None

    llm_response = [
        {
            "name": "Accuracy",
            "definition": "factual correctness",
            "rubric": {"1": "many errors", "5": "perfect"},
        },
        {
            "name": "Clarity",
            "definition": "clear writing",
            "rubric": {"1": "confusing", "5": "very clear"},
        },
    ]

    # Patch the inner LLMClient that criteria_generator constructs
    with patch("efa.criteria_generator.LLMClient") as MockLLMClient:
        mock_inner = MagicMock()
        mock_inner.complete_json.return_value = llm_response
        MockLLMClient.return_value = mock_inner

        result = generate_criteria(mock_client, prompt="Explain gravity", n_criteria=2, dynamic=True)

    assert len(result) == 2
    assert result[0].name == "Accuracy"
    assert result[1].name == "Clarity"


def test_dynamic_true_falls_back_on_llm_failure():
    """When dynamic generation fails both attempts, fixed criteria are returned."""
    mock_client = MagicMock(spec=LLMClient)
    mock_client.model = "gpt-4o"
    mock_client.temperature = 0.7
    mock_client.max_tokens = 4096
    mock_client.tracker = MagicMock()
    mock_client.api_base = None
    mock_client.api_key = None
    mock_client.call_delay = 0.0
    mock_client.seed = None

    with patch("efa.criteria_generator.LLMClient") as MockLLMClient:
        mock_inner = MagicMock()
        mock_inner.complete_json.side_effect = ValueError("LLM parse error")
        MockLLMClient.return_value = mock_inner

        result = generate_criteria(mock_client, prompt="bad prompt", n_criteria=3, dynamic=True)

    # Falls back to fixed criteria
    assert len(result) == 3
    assert all(isinstance(c, Criterion) for c in result)
    expected_weight = 1.0 / 3
    for c in result:
        assert abs(c.weight - expected_weight) < 1e-9
