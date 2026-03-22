"""Unit tests for EFA data models — Karthick Raja M, 2026."""

from efa.models import Criterion, EvaluationResult


def test_criterion_priority_label_critical():
    c = Criterion(name="test", definition="test", rubric={}, weight=0.5)
    # With n=5, uniform = 0.2, threshold for CRITICAL = 0.4
    assert "CRITICAL" in c.priority_label(5)


def test_criterion_priority_label_standard():
    c = Criterion(name="test", definition="test", rubric={}, weight=0.2)
    assert "STANDARD" in c.priority_label(5)


def test_criterion_priority_label_secondary():
    c = Criterion(name="test", definition="test", rubric={}, weight=0.05)
    assert "SECONDARY" in c.priority_label(5)


def test_evaluation_result_min_score():
    er = EvaluationResult(scores=[0.8, 0.4, 0.6], raw_scores=[4, 2, 3], reasoning=["", "", ""])
    assert er.min_score == 0.4


def test_evaluation_result_mean_score():
    er = EvaluationResult(scores=[0.8, 0.4, 0.6], raw_scores=[4, 2, 3], reasoning=["", "", ""])
    assert abs(er.mean_score - 0.6) < 1e-6


def test_evaluation_result_all_pass():
    passing = EvaluationResult(scores=[0.8, 0.6, 0.7], raw_scores=[4, 3, 3], reasoning=[""] * 3)
    assert passing.all_pass

    failing = EvaluationResult(scores=[0.8, 0.4, 0.7], raw_scores=[4, 2, 3], reasoning=[""] * 3)
    assert not failing.all_pass
