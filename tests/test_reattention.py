"""Unit tests for FWRL reattention logic — Karthick Raja M, 2026."""

from efa.models import Criterion, EvaluationResult
from efa.reattention import check_convergence, update_weights


def _make_criteria(weights: list[float]) -> list[Criterion]:
    return [
        Criterion(name=f"c{i}", definition="", rubric={}, weight=w)
        for i, w in enumerate(weights)
    ]


def test_passing_criteria_unchanged():
    """Criteria scoring above threshold should keep weight unchanged."""
    criteria = _make_criteria([0.2, 0.2, 0.2, 0.2, 0.2])
    evaluation = EvaluationResult(
        scores=[0.8, 0.8, 0.8, 0.8, 0.8],
        raw_scores=[4, 4, 4, 4, 4],
        reasoning=[""] * 5,
    )
    update_weights(criteria, evaluation, alpha=2.0, threshold=0.6)
    # All passing — weights should stay equal (after normalization)
    for c in criteria:
        assert abs(c.weight - 0.2) < 0.01


def test_failing_criteria_get_boosted():
    """Criteria below threshold should have weight increased."""
    criteria = _make_criteria([0.2, 0.2, 0.2, 0.2, 0.2])
    evaluation = EvaluationResult(
        scores=[0.8, 0.2, 0.8, 0.8, 0.8],
        raw_scores=[4, 1, 4, 4, 4],
        reasoning=[""] * 5,
    )
    update_weights(criteria, evaluation, alpha=2.0, threshold=0.6)
    # Criterion 1 (score=0.2) should be boosted relative to others
    # The raw weight before normalization: 0.2 * (1 + 2.0 * 0.4) = 0.2 * 1.8 = 0.36
    assert criteria[1].weight > criteria[0].weight


def test_worse_failure_gets_bigger_boost():
    """More severe failure should produce larger weight boost."""
    criteria = _make_criteria([0.2, 0.2, 0.2])
    evaluation = EvaluationResult(
        scores=[0.8, 0.2, 0.4],  # c1 fails more than c2
        raw_scores=[4, 1, 2],
        reasoning=[""] * 3,
    )
    update_weights(criteria, evaluation, alpha=2.0, threshold=0.6)
    # c1 (score=0.2, gap=0.4) should be boosted more than c2 (score=0.4, gap=0.2)
    assert criteria[1].weight > criteria[2].weight


def test_checkpoint_locks_regressed_criterion():
    """Criterion that previously passed but regressed should be locked."""
    criteria = _make_criteria([0.2, 0.2, 0.2])
    criteria[0].best_score = 0.8  # Previously passed

    evaluation = EvaluationResult(
        scores=[0.5, 0.8, 0.8],  # c0 regressed below best - epsilon
        raw_scores=[2, 4, 4],
        reasoning=[""] * 3,
    )
    update_weights(criteria, evaluation, alpha=2.0, threshold=0.6, epsilon=0.1)
    assert criteria[0].locked


def test_convergence_check():
    """All criteria above threshold should signal convergence."""
    criteria = _make_criteria([0.2, 0.2, 0.2])
    passing = EvaluationResult(scores=[0.8, 0.6, 0.7], raw_scores=[4, 3, 3], reasoning=[""] * 3)
    failing = EvaluationResult(scores=[0.8, 0.4, 0.7], raw_scores=[4, 2, 3], reasoning=[""] * 3)

    assert check_convergence(passing, criteria, threshold=0.6)
    assert not check_convergence(failing, criteria, threshold=0.6)
