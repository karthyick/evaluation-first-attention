"""Unit tests for baseline implementations — Karthick Raja M, 2026.

Strategy
--------
Baselines call LLMClient directly (not via EFAPipeline), so we patch
efa.baselines.LLMClient and the two shared helpers:
  - efa.baselines.generate_criteria
  - efa.baselines.evaluate_per_criterion

The fusion synthesis test additionally inspects the user-message passed to
the synthesis client's .complete() call to assert all candidates are embedded.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from efa.baselines import (
    BASELINES,
    run_fusion,
)
from efa.models import Criterion, EvaluationResult

# ---------------------------------------------------------------------------
# Patch targets
# ---------------------------------------------------------------------------

_PATCH_LLMCLIENT = "efa.baselines.LLMClient"
_PATCH_GEN_CRITERIA = "efa.baselines.generate_criteria"
_PATCH_EVALUATE = "efa.baselines.evaluate_per_criterion"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_criteria(n: int = 3) -> list[Criterion]:
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
    return EvaluationResult(
        scores=[0.8] * n,
        raw_scores=[4] * n,
        reasoning=["good"] * n,
    )


class _FakeTracker:
    """Minimal token tracker."""

    def __init__(self) -> None:
        self.prompt_tokens = 0
        self.completion_tokens = 0

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens


def _make_fake_client(complete_return: str = "generated text") -> MagicMock:
    """LLMClient mock that returns a fixed string from .complete()."""
    client = MagicMock()
    client.tracker = _FakeTracker()
    client.complete.return_value = complete_return
    return client


# ---------------------------------------------------------------------------
# 1. test_baselines_registry_has_seven_entries
# ---------------------------------------------------------------------------

def test_baselines_registry_has_seven_entries():
    """BASELINES dict must contain exactly 7 entries."""
    assert len(BASELINES) == 7


# ---------------------------------------------------------------------------
# 2. test_all_baselines_are_callable
# ---------------------------------------------------------------------------

def test_all_baselines_are_callable():
    """Every value stored in BASELINES must be a callable."""
    for name, fn in BASELINES.items():
        assert callable(fn), f"BASELINES['{name}'] is not callable"


# ---------------------------------------------------------------------------
# 3. test_baseline_names
# ---------------------------------------------------------------------------

def test_baseline_names():
    """BASELINES must contain exactly the seven expected method keys."""
    expected = {
        "single-pass",
        "self-refine",
        "rubric-then-score",
        "all-criteria-at-once",
        "uniform-reattention",
        "best-of-n",
        "fusion",
    }
    assert set(BASELINES.keys()) == expected


# ---------------------------------------------------------------------------
# 4. test_fusion_synthesis_prompt_includes_candidates
# ---------------------------------------------------------------------------

def test_fusion_synthesis_prompt_includes_candidates():
    """The synthesis LLM call must embed each candidate response in its user message."""
    n_candidates = 3
    criteria = _make_criteria(3)

    candidate_texts = [f"candidate response {i}" for i in range(n_candidates)]

    # gen client: returns candidates in sequence
    gen_client = _make_fake_client()
    gen_client.complete.side_effect = candidate_texts

    # synth client: captures the call and returns a fixed synthesis
    synth_client = _make_fake_client(complete_return="synthesized response")

    # eval client: returns passing scores
    eval_client = _make_fake_client()

    # run_fusion creates three LLMClient instances in this order: gen, synth, eval
    with (
        patch(_PATCH_LLMCLIENT, side_effect=[gen_client, synth_client, eval_client]),
        patch(_PATCH_GEN_CRITERIA, return_value=criteria),
        patch(_PATCH_EVALUATE, return_value=_passing_eval(3)),
    ):
        result = run_fusion(
            prompt="test prompt",
            model="gpt-4o",
            n_criteria=3,
            n_candidates=n_candidates,
        )

    # Verify synthesis client was called exactly once
    assert synth_client.complete.call_count == 1

    # Retrieve the user argument passed to synth_client.complete(system=..., user=...)
    synth_call_kwargs = synth_client.complete.call_args
    user_arg: str = synth_call_kwargs.kwargs.get("user") or synth_call_kwargs.args[1]

    # Every candidate text must appear in the synthesis user prompt
    for candidate_text in candidate_texts:
        assert candidate_text in user_arg, (
            f"Candidate text not found in synthesis prompt.\n"
            f"Missing: {candidate_text!r}\n"
            f"Prompt: {user_arg[:300]!r}"
        )

    # Result method and response
    assert result.method == "fusion"
    assert result.response == "synthesized response"
