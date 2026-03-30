"""Baseline implementations (Section 4.1) — Karthick Raja M, 2026.

7 baselines:
1. Single-pass
2. Self-Refine
3. Rubric-then-Score
4. All-Criteria-at-Once
5. Uniform Reattention
6. Best-of-N (NEW — added per reviewer feedback)
7. FusioN-style (simplified) — multi-candidate synthesis (Agarwal et al., 2025)
"""

from __future__ import annotations

from efa.criteria_generator import generate_criteria
from efa.evaluator import evaluate_per_criterion
from efa.llm_client import LLMClient
from efa.models import EvaluationResult, IterationTrace, PipelineResult


def run_single_pass(
    prompt: str,
    model: str = "gpt-4o",
    evaluator_model: str | None = None,
    n_criteria: int = 5,
    gen_api_base: str | None = None,
    gen_api_key: str | None = None,
    eval_api_base: str | None = None,
    eval_api_key: str | None = None,
) -> PipelineResult:
    """Baseline 1: Standard single-pass generation. No criteria, no refinement."""
    gen = LLMClient(model=model, temperature=0.7, api_base=gen_api_base, api_key=gen_api_key)
    eval_client = LLMClient(model=evaluator_model or model, temperature=0.1, api_base=eval_api_base, api_key=eval_api_key)

    response = gen.complete(
        system="You are a helpful assistant.",
        user=prompt,
    )

    # Still evaluate with criteria for fair comparison
    criteria = generate_criteria(gen, prompt, n_criteria, dynamic=True)
    evaluation = evaluate_per_criterion(eval_client, response, criteria)

    return PipelineResult(
        prompt=prompt,
        response=response,
        criteria=criteria,
        iterations=[IterationTrace(
            iteration=1, drafts=[response], response=response,
            evaluation=evaluation,
            weights_before=[1 / n_criteria] * n_criteria,
            weights_after=[1 / n_criteria] * n_criteria,
            tokens_used=gen.tracker.total + eval_client.tracker.total,
        )],
        converged=evaluation.all_pass,
        total_tokens=gen.tracker.total + eval_client.tracker.total,
        method="single-pass",
    )


def run_self_refine(
    prompt: str,
    model: str = "gpt-4o",
    evaluator_model: str | None = None,
    n_criteria: int = 5,
    max_iterations: int = 3,
    gen_api_base: str | None = None,
    gen_api_key: str | None = None,
    eval_api_base: str | None = None,
    eval_api_key: str | None = None,
) -> PipelineResult:
    """Baseline 2: Self-Refine (Madaan et al., 2023). Holistic feedback loop."""
    gen = LLMClient(model=model, temperature=0.7, api_base=gen_api_base, api_key=gen_api_key)
    eval_client = LLMClient(model=evaluator_model or model, temperature=0.1, api_base=eval_api_base, api_key=eval_api_key)

    # Generate criteria for evaluation (but NOT shown to generator)
    criteria = generate_criteria(gen, prompt, n_criteria, dynamic=True)

    # Initial generation
    response = gen.complete(
        system="You are a helpful assistant.",
        user=prompt,
    )

    iterations: list[IterationTrace] = []
    uniform_w = [1 / n_criteria] * n_criteria

    for k in range(1, max_iterations + 1):
        evaluation = evaluate_per_criterion(eval_client, response, criteria)

        iterations.append(IterationTrace(
            iteration=k, drafts=[response], response=response,
            evaluation=evaluation,
            weights_before=uniform_w, weights_after=uniform_w,
            tokens_used=gen.tracker.total + eval_client.tracker.total,
        ))

        if evaluation.all_pass:
            break

        # Self-Refine: holistic feedback + refinement
        feedback = gen.complete(
            system="You are a critical reviewer. Provide specific, actionable feedback on how to improve this response.",
            user=f"Original prompt: {prompt}\n\nResponse:\n{response}\n\nProvide feedback on what needs improvement.",
        )
        response = gen.complete(
            system="You are a helpful assistant. Improve your previous response based on the feedback.",
            user=f"Original prompt: {prompt}\n\nPrevious response:\n{response}\n\nFeedback:\n{feedback}\n\nProvide an improved response.",
        )

    return PipelineResult(
        prompt=prompt,
        response=response,
        criteria=criteria,
        iterations=iterations,
        converged=iterations[-1].evaluation.all_pass if iterations else False,
        total_tokens=gen.tracker.total + eval_client.tracker.total,
        method="self-refine",
    )


def run_rubric_then_score(
    prompt: str,
    model: str = "gpt-4o",
    evaluator_model: str | None = None,
    n_criteria: int = 5,
    gen_api_base: str | None = None,
    gen_api_key: str | None = None,
    eval_api_base: str | None = None,
    eval_api_key: str | None = None,
) -> PipelineResult:
    """Baseline 3: Generate criteria, generate WITHOUT criteria, then score.

    Tests whether criteria-aware generation outperforms criteria-unaware.
    """
    gen = LLMClient(model=model, temperature=0.7, api_base=gen_api_base, api_key=gen_api_key)
    eval_client = LLMClient(model=evaluator_model or model, temperature=0.1, api_base=eval_api_base, api_key=eval_api_key)

    # Generate criteria
    criteria = generate_criteria(gen, prompt, n_criteria, dynamic=True)

    # Generate WITHOUT criteria conditioning (key difference from EFA)
    response = gen.complete(
        system="You are a helpful assistant.",
        user=prompt,
    )

    # Score with the rubric
    evaluation = evaluate_per_criterion(eval_client, response, criteria)

    return PipelineResult(
        prompt=prompt,
        response=response,
        criteria=criteria,
        iterations=[IterationTrace(
            iteration=1, drafts=[response], response=response,
            evaluation=evaluation,
            weights_before=[1 / n_criteria] * n_criteria,
            weights_after=[1 / n_criteria] * n_criteria,
            tokens_used=gen.tracker.total + eval_client.tracker.total,
        )],
        converged=evaluation.all_pass,
        total_tokens=gen.tracker.total + eval_client.tracker.total,
        method="rubric-then-score",
    )


def run_all_criteria_at_once(
    prompt: str,
    model: str = "gpt-4o",
    evaluator_model: str | None = None,
    n_criteria: int = 5,
    gen_api_base: str | None = None,
    gen_api_key: str | None = None,
    eval_api_base: str | None = None,
    eval_api_key: str | None = None,
) -> PipelineResult:
    """Baseline 4: All criteria shown at once (no progressive masking).

    Same as EFA but skips CMPG — all criteria visible from start.
    """
    from efa.pipeline import EFAPipeline

    pipeline = EFAPipeline(
        model=model,
        evaluator_model=evaluator_model,
        n_criteria=n_criteria,
        progressive_masking=False,  # Key: disable CMPG
        failure_weighting=True,
        iterative=True,
        gen_api_base=gen_api_base,
        gen_api_key=gen_api_key,
        eval_api_base=eval_api_base,
        eval_api_key=eval_api_key,
    )
    result = pipeline.run(prompt)
    result.method = "all-criteria-at-once"
    return result


def run_uniform_reattention(
    prompt: str,
    model: str = "gpt-4o",
    evaluator_model: str | None = None,
    n_criteria: int = 5,
    gen_api_base: str | None = None,
    gen_api_key: str | None = None,
    eval_api_base: str | None = None,
    eval_api_key: str | None = None,
) -> PipelineResult:
    """Baseline 5: Criteria + iteration but uniform weights (no FWRL).

    Tests whether failure-weighted reattention outperforms uniform retry.
    """
    from efa.pipeline import EFAPipeline

    pipeline = EFAPipeline(
        model=model,
        evaluator_model=evaluator_model,
        n_criteria=n_criteria,
        progressive_masking=True,
        failure_weighting=False,  # Key: disable FWRL
        iterative=True,
        gen_api_base=gen_api_base,
        gen_api_key=gen_api_key,
        eval_api_base=eval_api_base,
        eval_api_key=eval_api_key,
    )
    result = pipeline.run(prompt)
    result.method = "uniform-reattention"
    return result


def run_best_of_n(
    prompt: str,
    model: str = "gpt-4o",
    evaluator_model: str | None = None,
    n_criteria: int = 5,
    n_samples: int = 5,
    gen_api_base: str | None = None,
    gen_api_key: str | None = None,
    eval_api_base: str | None = None,
    eval_api_key: str | None = None,
) -> PipelineResult:
    """Baseline 6 (NEW): Best-of-N sampling.

    Generate N independent responses, score all, return best.
    Critical baseline per reviewer feedback — cheaper alternative to iterative refinement.
    """
    gen = LLMClient(model=model, temperature=0.9, api_base=gen_api_base, api_key=gen_api_key)
    eval_client = LLMClient(model=evaluator_model or model, temperature=0.1, api_base=eval_api_base, api_key=eval_api_key)

    criteria = generate_criteria(gen, prompt, n_criteria, dynamic=True)

    best_response = ""
    best_score = -1.0
    best_eval = None
    all_responses: list[str] = []

    for _ in range(n_samples):
        response = gen.complete(
            system="You are a helpful assistant.",
            user=prompt,
        )
        all_responses.append(response)

        evaluation = evaluate_per_criterion(eval_client, response, criteria, batched=True)
        mean_score = evaluation.mean_score

        if mean_score > best_score:
            best_score = mean_score
            best_response = response
            best_eval = evaluation

    return PipelineResult(
        prompt=prompt,
        response=best_response,
        criteria=criteria,
        iterations=[IterationTrace(
            iteration=1, drafts=all_responses, response=best_response,
            evaluation=best_eval or EvaluationResult([], [], []),
            weights_before=[1 / n_criteria] * n_criteria,
            weights_after=[1 / n_criteria] * n_criteria,
            tokens_used=gen.tracker.total + eval_client.tracker.total,
        )],
        converged=best_eval.all_pass if best_eval else False,
        total_tokens=gen.tracker.total + eval_client.tracker.total,
        method=f"best-of-{n_samples}",
    )


_FUSION_SYNTHESIS_SYSTEM = (
    "You are an expert synthesizer. You have been given multiple candidate responses "
    "to a user's question. Your task is to produce a SINGLE superior response that "
    "combines the best aspects of ALL candidates. Do not simply copy one response — "
    "actively merge complementary strengths, discard weaknesses, and fill gaps."
)

_FUSION_SYNTHESIS_USER_TEMPLATE = """\
User prompt: {prompt}

{candidates}

Synthesize a single superior response that integrates the strongest elements from \
each candidate above. Cover what they collectively cover best, without redundancy.\
"""


def run_fusion(
    prompt: str,
    model: str = "gpt-4o",
    evaluator_model: str | None = None,
    n_criteria: int = 5,
    n_candidates: int = 3,
    gen_api_base: str | None = None,
    gen_api_key: str | None = None,
    eval_api_base: str | None = None,
    eval_api_key: str | None = None,
) -> PipelineResult:
    """Baseline 7: FusioN-style multi-candidate synthesis (Agarwal et al., 2025).

    Implements a simplified version of "Making, not Taking, the Best of N":
    generate N independent candidate responses, then use the LLM to synthesize
    a single superior response that actively combines the strengths of all
    candidates rather than selecting the best one.

    Reference: Agarwal et al. (2025), https://arxiv.org/abs/2510.00931

    Args:
        prompt: User prompt to respond to.
        model: Generation model identifier (LiteLLM format).
        evaluator_model: Separate evaluator model. Falls back to ``model`` if None.
        n_criteria: Number of evaluation criteria to generate.
        n_candidates: Number of independent candidate responses to generate (N).
        gen_api_base: Optional API base URL for the generation client.
        gen_api_key: Optional API key for the generation client.
        eval_api_base: Optional API base URL for the evaluation client.
        eval_api_key: Optional API key for the evaluation client.

    Returns:
        PipelineResult with method="fusion", containing the synthesized response
        and its evaluation scores. The ``drafts`` field of the single
        IterationTrace holds all N candidates plus the final synthesis.
    """
    gen = LLMClient(
        model=model,
        temperature=0.9,  # Higher temp for candidate diversity
        api_base=gen_api_base,
        api_key=gen_api_key,
    )
    synth = LLMClient(
        model=model,
        temperature=0.4,  # Lower temp for coherent synthesis
        api_base=gen_api_base,
        api_key=gen_api_key,
    )
    eval_client = LLMClient(
        model=evaluator_model or model,
        temperature=0.1,
        api_base=eval_api_base,
        api_key=eval_api_key,
    )

    # Generate criteria once (shared for all candidates and the synthesis)
    criteria = generate_criteria(gen, prompt, n_criteria, dynamic=True)

    # Phase 1: generate N independent candidates
    candidates: list[str] = []
    for _ in range(n_candidates):
        candidate = gen.complete(
            system="You are a helpful assistant.",
            user=prompt,
        )
        candidates.append(candidate)

    # Phase 2: synthesize — actively combine the best of all candidates
    candidate_block = "\n\n".join(
        f"Candidate {i + 1}:\n{c}" for i, c in enumerate(candidates)
    )
    synthesis_user = _FUSION_SYNTHESIS_USER_TEMPLATE.format(
        prompt=prompt,
        candidates=candidate_block,
    )
    synthesized = synth.complete(
        system=_FUSION_SYNTHESIS_SYSTEM,
        user=synthesis_user,
    )

    # Phase 3: evaluate the synthesized response
    evaluation = evaluate_per_criterion(eval_client, synthesized, criteria, batched=True)

    # Aggregate tokens from all three clients
    total_tokens = gen.tracker.total + synth.tracker.total + eval_client.tracker.total

    return PipelineResult(
        prompt=prompt,
        response=synthesized,
        criteria=criteria,
        iterations=[
            IterationTrace(
                iteration=1,
                # Store all candidates + final synthesis for full traceability
                drafts=[*candidates, synthesized],
                response=synthesized,
                evaluation=evaluation,
                weights_before=[1 / n_criteria] * n_criteria,
                weights_after=[1 / n_criteria] * n_criteria,
                tokens_used=total_tokens,
            )
        ],
        converged=evaluation.all_pass,
        total_tokens=total_tokens,
        method="fusion",
    )


# Registry of all baselines
BASELINES = {
    "single-pass": run_single_pass,
    "self-refine": run_self_refine,
    "rubric-then-score": run_rubric_then_score,
    "all-criteria-at-once": run_all_criteria_at_once,
    "uniform-reattention": run_uniform_reattention,
    "best-of-n": run_best_of_n,
    "fusion": run_fusion,
}
