"""Full EFA Pipeline — Algorithm 1 from paper — Karthick Raja M, 2026."""

from __future__ import annotations

from dataclasses import dataclass, field

from efa.criteria_generator import generate_criteria
from efa.evaluator import evaluate_per_criterion
from efa.llm_client import LLMClient
from efa.models import Criterion, IterationTrace, PipelineResult
from efa.progressive_generator import progressive_generate
from efa.reattention import check_convergence, update_weights


@dataclass
class EFAPipeline:
    """Complete Evaluation-First Attention pipeline.

    Implements Algorithm 1: Criteria Generation -> CMPG -> FWRL loop.
    """

    # Model configuration
    model: str = "gpt-4o"
    evaluator_model: str | None = None  # None = same model (paper default)

    # Hyperparameters (Section 4.4)
    n_criteria: int = 5
    threshold: float = 0.6  # tau
    max_iterations: int = 3  # K_max
    alpha: float = 2.0  # Reattention strength
    epsilon: float = 0.1  # Regression tolerance

    # Ablation flags
    dynamic_criteria: bool = True  # False = -DynCriteria ablation
    progressive_masking: bool = True  # False = -CMPG ablation
    failure_weighting: bool = True  # False = -FWRL ablation
    iterative: bool = True  # False = -Iteration ablation
    batched_eval: bool = False  # True = cheaper evaluation

    # Temperature
    gen_temperature: float = 0.7
    eval_temperature: float = 0.1  # Low temp for consistent scoring

    # Rate limiting
    gen_call_delay: float = 0.0  # Delay between generator calls (seconds)
    eval_call_delay: float = 0.0  # Delay between evaluator calls (seconds)

    # Custom API endpoints (for OpenAI-compatible providers like MiniMax)
    gen_api_base: str | None = None
    gen_api_key: str | None = None
    eval_api_base: str | None = None
    eval_api_key: str | None = None

    # Reproducibility
    seed: int | None = None  # Passed to both gen_client and eval_client

    def run(self, prompt: str) -> PipelineResult:
        """Execute full EFA pipeline on a single prompt."""
        # Initialize clients
        gen_client = LLMClient(
            model=self.model,
            temperature=self.gen_temperature,
            max_tokens=4096,
            seed=self.seed,
            call_delay=self.gen_call_delay,
            api_base=self.gen_api_base,
            api_key=self.gen_api_key,
        )
        eval_client = LLMClient(
            model=self.evaluator_model or self.model,
            temperature=self.eval_temperature,
            max_tokens=1024,
            seed=self.seed,
            call_delay=self.eval_call_delay,
            api_base=self.eval_api_base,
            api_key=self.eval_api_key,
        )

        # Phase 1: Generate criteria
        criteria = generate_criteria(
            client=gen_client,
            prompt=prompt,
            n_criteria=self.n_criteria,
            dynamic=self.dynamic_criteria,
        )

        # Handle -Iteration ablation: single pass, no loop
        effective_max_iter = self.max_iterations if self.iterative else 1

        iterations: list[IterationTrace] = []
        previous_response: str | None = None
        converged = False
        prev_gen_tokens = 0
        prev_eval_tokens = 0

        for k in range(1, effective_max_iter + 1):
            weights_before = [c.weight for c in criteria]

            # Phase 2: Criteria-Masked Progressive Generation
            response, drafts = progressive_generate(
                client=gen_client,
                user_prompt=prompt,
                criteria=criteria,
                previous_response=previous_response,
                use_progressive_masking=self.progressive_masking,
            )

            # Phase 3: Per-Criterion Evaluation
            evaluation = evaluate_per_criterion(
                client=eval_client,
                response=response,
                criteria=criteria,
                batched=self.batched_eval,
            )

            # Checkpoint + Convergence Check
            converged = check_convergence(evaluation, criteria, self.threshold)

            # Record weights before reattention
            weights_after = [c.weight for c in criteria]

            # Apply FWRL (or uniform if ablation)
            if not converged and self.failure_weighting:
                update_weights(
                    criteria=criteria,
                    evaluation=evaluation,
                    alpha=self.alpha,
                    threshold=self.threshold,
                    epsilon=self.epsilon,
                )
                weights_after = [c.weight for c in criteria]

            cur_gen_tokens = gen_client.tracker.total
            cur_eval_tokens = eval_client.tracker.total
            tokens_this_iter = (cur_gen_tokens - prev_gen_tokens) + (cur_eval_tokens - prev_eval_tokens)
            prev_gen_tokens = cur_gen_tokens
            prev_eval_tokens = cur_eval_tokens

            iterations.append(IterationTrace(
                iteration=k,
                drafts=drafts,
                response=response,
                evaluation=evaluation,
                weights_before=weights_before,
                weights_after=weights_after,
                tokens_used=tokens_this_iter,
            ))

            if converged:
                break

            previous_response = response

        total_tokens = gen_client.tracker.total + eval_client.tracker.total

        return PipelineResult(
            prompt=prompt,
            response=iterations[-1].response if iterations else "",
            criteria=criteria,
            iterations=iterations,
            converged=converged if iterations else False,
            total_tokens=total_tokens,
            method=self._method_name(),
        )

    def _method_name(self) -> str:
        """Generate method name based on configuration."""
        if not self.dynamic_criteria:
            return "efa-no-dyncriteria"
        if not self.progressive_masking:
            return "efa-no-cmpg"
        if not self.failure_weighting:
            return "efa-no-fwrl"
        if not self.iterative:
            return "efa-no-iteration"
        return "efa"
