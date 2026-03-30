"""Unit tests for per-criterion evaluator — Karthick Raja M, 2026."""

from unittest.mock import MagicMock

from efa.evaluator import evaluate_per_criterion
from efa.models import Criterion


def _make_criterion(name: str = "Accuracy") -> Criterion:
    return Criterion(
        name=name,
        definition="The response is factually correct.",
        rubric={
            1: "Completely wrong",
            2: "Mostly wrong",
            3: "Partially correct",
            4: "Mostly correct",
            5: "Fully correct",
        },
    )


def _make_criteria(names: list[str]) -> list[Criterion]:
    return [_make_criterion(name) for name in names]


# ---------------------------------------------------------------------------
# Score clamping and normalization (individual path)
# ---------------------------------------------------------------------------


def test_score_clamping_below():
    """Raw score 0 from LLM should be clamped to 1 and normalized to 0.2."""
    client = MagicMock()
    client.complete_json.return_value = {"score": 0, "reasoning": "too low"}

    criteria = [_make_criterion("Accuracy")]
    result = evaluate_per_criterion(client, "some response", criteria, batched=False)

    assert result.raw_scores[0] == 1
    assert abs(result.scores[0] - 0.2) < 1e-9


def test_score_clamping_above():
    """Raw score 6 from LLM should be clamped to 5 and normalized to 1.0."""
    client = MagicMock()
    client.complete_json.return_value = {"score": 6, "reasoning": "too high"}

    criteria = [_make_criterion("Accuracy")]
    result = evaluate_per_criterion(client, "some response", criteria, batched=False)

    assert result.raw_scores[0] == 5
    assert abs(result.scores[0] - 1.0) < 1e-9


def test_score_normalization():
    """Raw score 4 should normalize to 0.8."""
    client = MagicMock()
    client.complete_json.return_value = {"score": 4, "reasoning": "good"}

    criteria = [_make_criterion("Accuracy")]
    result = evaluate_per_criterion(client, "some response", criteria, batched=False)

    assert result.raw_scores[0] == 4
    assert abs(result.scores[0] - 0.8) < 1e-9


# ---------------------------------------------------------------------------
# Result count (individual path)
# ---------------------------------------------------------------------------


def test_individual_eval_returns_correct_count():
    """N criteria should produce exactly N scores in individual eval mode."""
    client = MagicMock()
    client.complete_json.return_value = {"score": 3, "reasoning": "ok"}

    criteria = _make_criteria(["Accuracy", "Clarity", "Relevance"])
    result = evaluate_per_criterion(client, "some response", criteria, batched=False)

    assert len(result.scores) == 3
    assert len(result.raw_scores) == 3
    assert len(result.reasoning) == 3
    # One LLM call per criterion
    assert client.complete_json.call_count == 3


# ---------------------------------------------------------------------------
# Batched eval — default for missing results
# ---------------------------------------------------------------------------


def test_batched_eval_default_for_missing():
    """If the LLM returns fewer results than criteria, missing ones default to score 3."""
    client = MagicMock()
    # Only returns 2 results for 3 criteria
    client.complete_json.return_value = [
        {"criterion": "Accuracy", "score": 4, "reasoning": "ok"},
        {"criterion": "Clarity", "score": 5, "reasoning": "clear"},
    ]

    criteria = _make_criteria(["Accuracy", "Clarity", "Relevance"])
    result = evaluate_per_criterion(client, "some response", criteria, batched=True)

    assert len(result.scores) == 3
    assert len(result.raw_scores) == 3
    # Third criterion falls back to default score of 3
    assert result.raw_scores[2] == 3
    assert abs(result.scores[2] - 0.6) < 1e-9
    assert result.reasoning[2] == "Not evaluated"


# ---------------------------------------------------------------------------
# Reasoning capture (individual path)
# ---------------------------------------------------------------------------


def test_eval_reasoning_captured():
    """Reasoning strings returned by the LLM are stored per-criterion."""
    client = MagicMock()
    client.complete_json.side_effect = [
        {"score": 4, "reasoning": "factually accurate"},
        {"score": 3, "reasoning": "somewhat clear"},
    ]

    criteria = _make_criteria(["Accuracy", "Clarity"])
    result = evaluate_per_criterion(client, "some response", criteria, batched=False)

    assert result.reasoning[0] == "factually accurate"
    assert result.reasoning[1] == "somewhat clear"
