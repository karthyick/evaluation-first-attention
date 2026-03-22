"""Baseline implementations (Section 4.1) — Karthick Raja M, 2026.

7 baselines:
1. Single-pass
2. Self-Refine
3. Rubric-then-Score
4. All-Criteria-at-Once
5. Uniform Reattention
6. Best-of-N (NEW — added per reviewer feedback)
7. FusioN-style (simplified)
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
) -> PipelineResult:
    """Baseline 1: Standard single-pass generation. No criteria, no refinement."""
    gen = LLMClient(model=model, temperature=0.7)
    eval_client = LLMClient(model=evaluator_model or model, temperature=0.1)

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
) -> PipelineResult:
    """Baseline 2: Self-Refine (Madaan et al., 2023). Holistic feedback loop."""
    gen = LLMClient(model=model, temperature=0.7)
    eval_client = LLMClient(model=evaluator_model or model, temperature=0.1)

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
) -> PipelineResult:
    """Baseline 3: Generate criteria, generate WITHOUT criteria, then score.

    Tests whether criteria-aware generation outperforms criteria-unaware.
    """
    gen = LLMClient(model=model, temperature=0.7)
    eval_client = LLMClient(model=evaluator_model or model, temperature=0.1)

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
    )
    result = pipeline.run(prompt)
    result.method = "all-criteria-at-once"
    return result


def run_uniform_reattention(
    prompt: str,
    model: str = "gpt-4o",
    evaluator_model: str | None = None,
    n_criteria: int = 5,
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
) -> PipelineResult:
    """Baseline 6 (NEW): Best-of-N sampling.

    Generate N independent responses, score all, return best.
    Critical baseline per reviewer feedback — cheaper alternative to iterative refinement.
    """
    gen = LLMClient(model=model, temperature=0.9)  # Higher temp for diversity
    eval_client = LLMClient(model=evaluator_model or model, temperature=0.1)

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


# Registry of all baselines
BASELINES = {
    "single-pass": run_single_pass,
    "self-refine": run_self_refine,
    "rubric-then-score": run_rubric_then_score,
    "all-criteria-at-once": run_all_criteria_at_once,
    "uniform-reattention": run_uniform_reattention,
    "best-of-n": run_best_of_n,
}
