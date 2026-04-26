"""End-to-end pipeline tests using the in-memory MockBackend.

These do not call out to any LLM API.
"""

from __future__ import annotations

import json

from rubricon import (
    BackendConfig,
    Criterion,
    PluginSpec,
    RubriconConfig,
    RubriconPipeline,
)
from rubricon.backends import MockBackend, backend_registry


def _make_responses() -> list[str]:
    """Sequence: criteria-gen JSON -> CMPG drafts -> per-criterion judge JSONs."""
    criteria_payload = json.dumps([
        {
            "name": "Clarity",
            "definition": "Easy to understand",
            "rubric": {"1": "bad", "2": "lo", "3": "ok", "4": "good", "5": "great"},
        },
        {
            "name": "Accuracy",
            "definition": "Factually correct",
            "rubric": {"1": "wrong", "2": "lo", "3": "ok", "4": "good", "5": "perfect"},
        },
    ])
    judge_payload = json.dumps({"score": 5, "reasoning": "great"})
    return [
        criteria_payload,
        "Draft response covering both criteria.",
        "Refined final response.",
        judge_payload,
        judge_payload,
    ]


def test_pipeline_runs_with_mock_backend() -> None:
    cfg = RubriconConfig.from_dict({
        "generator": {"backend": "mock", "model": "mock"},
        "criteria": {"n": 2},
        "iteration": {"max_iterations": 1},
        "convergence": {"threshold": 0.5},
        "evaluators": [{"type": "llm_judge"}],
    })
    pipe = RubriconPipeline(cfg)
    pipe._build_components()
    assert pipe._components is not None
    pipe._components.generator_backend = MockBackend(responses=_make_responses())
    pipe._components.evaluator_backend = pipe._components.generator_backend
    pipe._components.criteria_backend = pipe._components.generator_backend
    # Re-bind the LLM-judge evaluator to the new backend so it shares responses.
    from rubricon.evaluators import build_evaluators
    pipe._components.evaluator = build_evaluators(
        cfg.evaluators,
        backend=pipe._components.generator_backend,
        templates=pipe._components.templates,
        threshold=cfg.convergence.threshold,
        rubric_scale=cfg.criteria.rubric_scale,
    )

    result = pipe.run("Explain entropy in one sentence.")
    assert result.method == "rubricon"
    assert len(result.criteria) == 2
    assert result.n_iterations == 1
    assert result.total_tokens > 0


def test_legacy_kwargs_shim() -> None:
    pipe = RubriconPipeline(
        model="gpt-4o-mini",
        evaluator_model="gpt-4o-mini",
        n_criteria=3,
        threshold=0.7,
        max_iterations=2,
        alpha=1.5,
        progressive_masking=False,
        failure_weighting=False,
        iterative=True,
    )
    cfg = pipe.config
    assert cfg.generator.model == "gpt-4o-mini"
    assert cfg.evaluator is not None and cfg.evaluator.model == "gpt-4o-mini"
    assert cfg.criteria.n == 3
    assert cfg.convergence.threshold == 0.7
    assert cfg.iteration.max_iterations == 2
    assert cfg.reattention.alpha == 1.5
    assert cfg.cmpg.enabled is False
    assert cfg.reattention.enabled is False


def test_function_evaluator_pipeline() -> None:
    """End-to-end using only deterministic plugins — no LLM judge."""
    cfg = RubriconConfig.from_dict({
        "generator": {"backend": "mock", "model": "mock"},
        "criteria": {"n": 1, "dynamic": False, "fixed_set": [
            {"name": "non_empty", "definition": "non-empty", "rubric": {1: "no", 5: "yes"}},
        ]},
        "iteration": {"max_iterations": 1},
        "convergence": {"threshold": 0.5},
        "evaluators": [],
    })
    # Inject a function evaluator after construction
    cfg.evaluators = [PluginSpec(type="function", params={"fn": lambda r, c, p: 1.0})]
    pipe = RubriconPipeline(cfg)
    result = pipe.run("Hi")
    assert result.all_pass is True
    assert result.rubric_adherence_score == 1.0


def test_backend_registry_user_extension() -> None:
    @backend_registry.register("custom_test")
    def _factory(**params):  # type: ignore[no-untyped-def]
        return MockBackend(responses=["custom"])

    assert "custom_test" in backend_registry.names()
    backend = backend_registry.create("custom_test")
    assert isinstance(backend, MockBackend)
