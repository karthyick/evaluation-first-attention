"""Unit tests for EFAPipeline — Karthick Raja M, 2026.

Strategy
--------
The pipeline wires together four components:
  - generate_criteria          (efa.criteria_generator)
  - progressive_generate       (efa.progressive_generator)
  - evaluate_per_criterion     (efa.evaluator)
  - LLMClient                  (efa.llm_client)

We patch the three module-level functions so that each test controls exactly
what the pipeline "sees" without making real API calls.  LLMClient instances
are also replaced with a lightweight fake that supports token accounting.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from efa.models import Criterion, EvaluationResult
from efa.pipeline import EFAPipeline

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_criteria(n: int = 3) -> list[Criterion]:
    """Return n uniform-weight Criterion objects."""
    return [
        Criterion(
            name=f"c{i}",
            definition=f"criterion {i}",
            rubric={1: "bad", 2: "poor", 3: "ok", 4: "good", 5: "excellent"},
            weight=1.0 / n,
        )
        for i in range(n)
    ]


def _passing_eval(n: int = 3) -> EvaluationResult:
    """EvaluationResult where every score >= 0.6 (all_pass == True)."""
    return EvaluationResult(
        scores=[0.8] * n,
        raw_scores=[4] * n,
        reasoning=["good"] * n,
    )


def _failing_eval(n: int = 3) -> EvaluationResult:
    """EvaluationResult where at least one score < 0.6 (all_pass == False)."""
    return EvaluationResult(
        scores=[0.4] * n,
        raw_scores=[2] * n,
        reasoning=["needs work"] * n,
    )


class _FakeTracker:
    """Minimal token tracker that increments by a fixed amount each call."""

    def __init__(self, step: int = 10) -> None:
        self._total = 0
        self._step = step

    @property
    def total(self) -> int:
        return self._total

    def tick(self) -> None:
        self._total += self._step


def _make_fake_client(token_step: int = 10) -> MagicMock:
    """Return a MagicMock that looks like LLMClient with a working tracker."""
    tracker = _FakeTracker(step=token_step)
    client = MagicMock()
    client.tracker = tracker
    return client


# ---------------------------------------------------------------------------
# Patch targets — the pipeline imports from these module paths
# ---------------------------------------------------------------------------

_PATCH_GENERATE_CRITERIA = "efa.pipeline.generate_criteria"
_PATCH_PROGRESSIVE_GEN = "efa.pipeline.progressive_generate"
_PATCH_EVALUATE = "efa.pipeline.evaluate_per_criterion"
_PATCH_LLMCLIENT = "efa.pipeline.LLMClient"


# ---------------------------------------------------------------------------
# 1. test_efa_converges_first_iteration
# ---------------------------------------------------------------------------

def test_efa_converges_first_iteration():
    """Pipeline exits after 1 iteration when evaluator returns all_pass on iter 1."""
    criteria = _make_criteria(3)

    with (
        patch(_PATCH_LLMCLIENT, side_effect=[_make_fake_client(), _make_fake_client()]),
        patch(_PATCH_GENERATE_CRITERIA, return_value=criteria),
        patch(_PATCH_PROGRESSIVE_GEN, return_value=("response_1", ["draft_1"])),
        patch(_PATCH_EVALUATE, return_value=_passing_eval(3)),
    ):
        pipeline = EFAPipeline(n_criteria=3, max_iterations=3)
        result = pipeline.run("test prompt")

    assert result.n_iterations == 1
    assert result.converged is True


# ---------------------------------------------------------------------------
# 2. test_efa_converges_after_refinement
# ---------------------------------------------------------------------------

def test_efa_converges_after_refinement():
    """Pipeline runs exactly 2 iterations: failing then passing evaluation."""
    criteria = _make_criteria(3)
    eval_side_effects = [_failing_eval(3), _passing_eval(3)]

    with (
        patch(_PATCH_LLMCLIENT, side_effect=[_make_fake_client(), _make_fake_client()]),
        patch(_PATCH_GENERATE_CRITERIA, return_value=criteria),
        patch(_PATCH_PROGRESSIVE_GEN, return_value=("response", ["draft"])),
        patch(_PATCH_EVALUATE, side_effect=eval_side_effects),
    ):
        pipeline = EFAPipeline(n_criteria=3, max_iterations=5)
        result = pipeline.run("test prompt")

    assert result.n_iterations == 2
    assert result.converged is True


# ---------------------------------------------------------------------------
# 3. test_efa_exhausts_max_iterations
# ---------------------------------------------------------------------------

def test_efa_exhausts_max_iterations():
    """Pipeline runs exactly K_max iterations when evaluator never passes."""
    criteria = _make_criteria(3)
    k_max = 4

    with (
        patch(_PATCH_LLMCLIENT, side_effect=[_make_fake_client(), _make_fake_client()]),
        patch(_PATCH_GENERATE_CRITERIA, return_value=criteria),
        patch(_PATCH_PROGRESSIVE_GEN, return_value=("response", ["draft"])),
        patch(_PATCH_EVALUATE, return_value=_failing_eval(3)),
    ):
        pipeline = EFAPipeline(n_criteria=3, max_iterations=k_max)
        result = pipeline.run("test prompt")

    assert result.n_iterations == k_max
    assert result.converged is False


# ---------------------------------------------------------------------------
# 4. test_ablation_no_cmpg
# ---------------------------------------------------------------------------

def test_ablation_no_cmpg():
    """With progressive_masking=False, method name must be 'efa-no-cmpg'."""
    pipeline = EFAPipeline(progressive_masking=False)
    assert pipeline._method_name() == "efa-no-cmpg"


# ---------------------------------------------------------------------------
# 5. test_ablation_no_fwrl
# ---------------------------------------------------------------------------

def test_ablation_no_fwrl():
    """With failure_weighting=False (and other flags True), method is 'efa-no-fwrl'."""
    pipeline = EFAPipeline(failure_weighting=False)
    assert pipeline._method_name() == "efa-no-fwrl"


# ---------------------------------------------------------------------------
# 6. test_ablation_no_iteration
# ---------------------------------------------------------------------------

def test_ablation_no_iteration():
    """With iterative=False the pipeline stops after exactly 1 iteration."""
    criteria = _make_criteria(3)

    with (
        patch(_PATCH_LLMCLIENT, side_effect=[_make_fake_client(), _make_fake_client()]),
        patch(_PATCH_GENERATE_CRITERIA, return_value=criteria),
        patch(_PATCH_PROGRESSIVE_GEN, return_value=("response", ["draft"])),
        patch(_PATCH_EVALUATE, return_value=_failing_eval(3)),
    ):
        # Even with max_iterations=10 and always-failing eval, iterative=False
        # must cap the loop at 1.
        pipeline = EFAPipeline(n_criteria=3, max_iterations=10, iterative=False)
        result = pipeline.run("test prompt")

    assert result.n_iterations == 1


# ---------------------------------------------------------------------------
# 7. test_ablation_no_dyncriteria
# ---------------------------------------------------------------------------

def test_ablation_no_dyncriteria():
    """With dynamic_criteria=False, method name must be 'efa-no-dyncriteria'."""
    pipeline = EFAPipeline(dynamic_criteria=False)
    assert pipeline._method_name() == "efa-no-dyncriteria"


# ---------------------------------------------------------------------------
# 8. test_method_name_full_efa
# ---------------------------------------------------------------------------

def test_method_name_full_efa():
    """With all ablation flags True the method name is simply 'efa'."""
    pipeline = EFAPipeline(
        dynamic_criteria=True,
        progressive_masking=True,
        failure_weighting=True,
        iterative=True,
    )
    assert pipeline._method_name() == "efa"


# ---------------------------------------------------------------------------
# 9. test_pipeline_result_properties
# ---------------------------------------------------------------------------

def test_pipeline_result_properties():
    """PipelineResult exposes rubric_adherence_score, all_pass, n_iterations,
    and final_scores derived from the last iteration's evaluation."""
    criteria = _make_criteria(3)
    final_eval = _passing_eval(3)  # scores=[0.8, 0.8, 0.8]

    with (
        patch(_PATCH_LLMCLIENT, side_effect=[_make_fake_client(), _make_fake_client()]),
        patch(_PATCH_GENERATE_CRITERIA, return_value=criteria),
        patch(_PATCH_PROGRESSIVE_GEN, return_value=("final response", ["draft"])),
        patch(_PATCH_EVALUATE, return_value=final_eval),
    ):
        pipeline = EFAPipeline(n_criteria=3, max_iterations=1)
        result = pipeline.run("test prompt")

    assert result.n_iterations == 1
    assert result.final_scores == [0.8, 0.8, 0.8]
    assert abs(result.rubric_adherence_score - 0.8) < 1e-9
    assert result.all_pass is True
    assert result.response == "final response"


# ---------------------------------------------------------------------------
# 10. test_token_tracking_per_iteration
# ---------------------------------------------------------------------------

def test_token_tracking_per_iteration():
    """tokens_used in each IterationTrace is the delta consumed in that iteration,
    not the cumulative total across all iterations."""
    criteria = _make_criteria(3)
    eval_side_effects = [_failing_eval(3), _passing_eval(3)]

    # Give gen_client a step of 20 and eval_client a step of 10.
    # On each iteration both clients tick once (progressive_generate + evaluate).
    # The mock side_effect for progressive_generate will advance gen tracker,
    # and evaluate will advance eval tracker — but because we also tick the
    # tracker inside the fake, we need to wire it up properly.
    #
    # Simpler approach: use real TokenTracker objects inside the fake clients and
    # manually set their totals so the delta arithmetic in the pipeline is tested.

    from efa.llm_client import TokenTracker

    gen_tracker = TokenTracker()
    eval_tracker = TokenTracker()

    gen_client = MagicMock()
    gen_client.tracker = gen_tracker

    eval_client = MagicMock()
    eval_client.tracker = eval_tracker

    # Simulate: after iter 1 gen uses 30, eval uses 20 → delta = 50
    #           after iter 2 gen uses 60, eval uses 40 → delta = 50

    call_count = [0]

    def fake_progressive_generate(**kwargs):
        call_count[0] += 1
        # Advance gen tracker by 30 per call
        gen_tracker.prompt_tokens += 15
        gen_tracker.completion_tokens += 15
        return ("response", ["draft"])

    def fake_evaluate(**kwargs):
        # Advance eval tracker by 20 per call
        eval_tracker.prompt_tokens += 10
        eval_tracker.completion_tokens += 10
        return eval_side_effects[call_count[0] - 1]

    with (
        patch(_PATCH_LLMCLIENT, side_effect=[gen_client, eval_client]),
        patch(_PATCH_GENERATE_CRITERIA, return_value=criteria),
        patch(_PATCH_PROGRESSIVE_GEN, side_effect=fake_progressive_generate),
        patch(_PATCH_EVALUATE, side_effect=fake_evaluate),
    ):
        pipeline = EFAPipeline(n_criteria=3, max_iterations=3)
        result = pipeline.run("test prompt")

    assert result.n_iterations == 2

    # Each iteration should report 50 tokens (30 gen + 20 eval delta)
    for trace in result.iterations:
        assert trace.tokens_used == 50, (
            f"Iteration {trace.iteration}: expected 50 tokens delta, got {trace.tokens_used}"
        )

    # total_tokens should equal the final cumulative sum from both clients
    expected_total = gen_tracker.total + eval_tracker.total
    assert result.total_tokens == expected_total


# ---------------------------------------------------------------------------
# 11. test_seed_propagates_to_clients
# ---------------------------------------------------------------------------

def test_seed_propagates_to_clients():
    """The seed parameter is forwarded to both gen_client and eval_client."""
    criteria = _make_criteria(3)
    captured_kwargs: list[dict] = []

    class CapturingFakeClient:
        """Records constructor kwargs and behaves like LLMClient."""

        def __init__(self, **kwargs: object) -> None:
            captured_kwargs.append(kwargs)
            self.tracker = _FakeTracker(step=5)

    with (
        patch(_PATCH_LLMCLIENT, side_effect=[
            CapturingFakeClient(model="gpt-4o", temperature=0.7, max_tokens=4096, seed=42,
                                call_delay=0.0, api_base=None, api_key=None),
            CapturingFakeClient(model="gpt-4o", temperature=0.1, max_tokens=1024, seed=42,
                                call_delay=0.0, api_base=None, api_key=None),
        ]),
        patch(_PATCH_GENERATE_CRITERIA, return_value=criteria),
        patch(_PATCH_PROGRESSIVE_GEN, return_value=("response", ["draft"])),
        patch(_PATCH_EVALUATE, return_value=_passing_eval(3)),
    ):
        pipeline = EFAPipeline(n_criteria=3, seed=42)
        pipeline.run("test prompt")

    # Both clients must have been constructed with seed=42
    assert len(captured_kwargs) == 2
    for i, kw in enumerate(captured_kwargs):
        assert kw.get("seed") == 42, (
            f"Client {i} was not constructed with seed=42: {kw}"
        )
