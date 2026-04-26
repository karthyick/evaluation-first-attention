"""Tests for the plugin registry layers."""

from __future__ import annotations

from rubricon import (
    AllPass,
    BudgetConfig,
    BudgetTracker,
    Criterion,
    EvaluationResult,
    FocalReattention,
    FunctionEvaluator,
    MeanThreshold,
    NoImprovement,
    PluginSpec,
    RegexEvaluator,
    SoftmaxReattention,
    UniformReattention,
    backend_registry,
    convergence_registry,
    evaluator_registry,
    reattention_registry,
)


def _make_criteria(n: int = 3) -> list[Criterion]:
    return [
        Criterion(
            name=f"c{i}",
            definition=f"def{i}",
            rubric={1: "low", 2: "lo", 3: "mid", 4: "hi", 5: "top"},
            weight=1.0 / n,
        )
        for i in range(n)
    ]


def test_registries_have_builtins() -> None:
    assert "litellm" in backend_registry.names()
    assert "mock" in backend_registry.names()
    assert {"llm_judge", "regex", "function", "ensemble"}.issubset(set(evaluator_registry.names()))
    assert {"focal", "uniform", "softmax"}.issubset(set(reattention_registry.names()))
    assert {"all_pass", "mean_threshold", "no_improvement"}.issubset(set(convergence_registry.names()))


def test_focal_reattention_increases_failing_weight() -> None:
    crits = _make_criteria(3)
    ev = EvaluationResult(scores=[0.9, 0.2, 0.8], raw_scores=[5, 1, 4], reasoning=["", "", ""])
    initial = [c.weight for c in crits]
    FocalReattention(alpha=2.0).update(crits, ev, threshold=0.6, epsilon=0.1, params={})
    assert crits[1].weight > initial[1]
    assert abs(sum(c.weight for c in crits) - 1.0) < 1e-6


def test_uniform_reattention_keeps_weights_equal() -> None:
    crits = _make_criteria(3)
    ev = EvaluationResult(scores=[0.9, 0.2, 0.8], raw_scores=[5, 1, 4], reasoning=["", "", ""])
    UniformReattention().update(crits, ev, threshold=0.6, epsilon=0.1, params={})
    weights = [c.weight for c in crits]
    assert max(weights) - min(weights) < 1e-6


def test_softmax_reattention_normalises() -> None:
    crits = _make_criteria(3)
    ev = EvaluationResult(scores=[0.9, 0.1, 0.5], raw_scores=[5, 1, 3], reasoning=["", "", ""])
    SoftmaxReattention(temperature=0.5).update(crits, ev, threshold=0.6, epsilon=0.1, params={})
    assert abs(sum(c.weight for c in crits) - 1.0) < 1e-6


def test_all_pass_policy() -> None:
    crits = _make_criteria(2)
    policy = AllPass()
    failing = EvaluationResult(scores=[0.9, 0.4], raw_scores=[5, 2], reasoning=["", ""])
    passing = EvaluationResult(scores=[0.9, 0.7], raw_scores=[5, 4], reasoning=["", ""])
    assert policy.converged(failing, crits, threshold=0.6, history=[failing]) is False
    assert policy.converged(passing, crits, threshold=0.6, history=[passing]) is True


def test_mean_threshold_policy() -> None:
    crits = _make_criteria(2)
    policy = MeanThreshold()
    high = EvaluationResult(scores=[0.5, 0.9], raw_scores=[3, 5], reasoning=["", ""])
    low = EvaluationResult(scores=[0.4, 0.5], raw_scores=[2, 3], reasoning=["", ""])
    assert policy.converged(high, crits, threshold=0.6, history=[high]) is True
    assert policy.converged(low, crits, threshold=0.6, history=[low]) is False


def test_no_improvement_policy_triggers_after_patience() -> None:
    crits = _make_criteria(1)
    policy = NoImprovement(patience=2, min_delta=0.05)
    e1 = EvaluationResult(scores=[0.5], raw_scores=[3], reasoning=[""])
    e2 = EvaluationResult(scores=[0.5], raw_scores=[3], reasoning=[""])
    e3 = EvaluationResult(scores=[0.51], raw_scores=[3], reasoning=[""])
    assert policy.converged(e3, crits, threshold=0.6, history=[e1, e2, e3]) is True


def test_regex_evaluator() -> None:
    ev = RegexEvaluator()
    crits = [
        Criterion(
            name="must_mention_python",
            definition="contains 'python'",
            rubric={1: "no", 5: "yes"},
            weight=1.0,
            metadata={"pattern": r"python", "mode": "match"},
        ),
    ]
    res = ev.evaluate("I love Python and rust", crits)
    assert res.scores[0] in (0.0, 1.0)


def test_function_evaluator() -> None:
    ev = FunctionEvaluator(fn=lambda r, c, p: 0.8 if "good" in r else 0.2)
    crits = [Criterion(name="quality", definition="x", rubric={1: "x", 5: "y"}, weight=1.0)]
    assert ev.evaluate("good answer", crits).scores[0] == 0.8
    assert ev.evaluate("bad answer", crits).scores[0] == 0.2


def test_evaluator_factory_via_registry() -> None:
    ev = evaluator_registry.create("function", fn=lambda r, c, p: 0.5)
    assert isinstance(ev, FunctionEvaluator)


def test_budget_tracker_stops_on_iterations() -> None:
    cfg = BudgetConfig(max_iterations=2)
    tracker = BudgetTracker(config=cfg)
    tracker.tick_iteration()
    assert tracker.exhausted() is None
    tracker.tick_iteration()
    assert tracker.exhausted() is not None


def test_plugin_spec_validates() -> None:
    spec = PluginSpec(type="regex", params={"threshold": 0.7})
    assert spec.type == "regex"
    assert spec.params["threshold"] == 0.7
