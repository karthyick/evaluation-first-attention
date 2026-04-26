"""Public pipeline that wires every configurable layer together.

Single entry point: ``RubriconPipeline(config).run(prompt) -> PipelineResult``.

The configuration object is the contract; everything else is replaceable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from rubricon import cmpg as cmpg_module
from rubricon import criteria as criteria_module
from rubricon.backends import LLMBackend, make_backend
from rubricon.budget import BudgetTracker
from rubricon.callbacks import CallbackBus, callback_registry
from rubricon.config import RubriconConfig
from rubricon.evaluators import Evaluator, build_evaluators
from rubricon.models import EvaluationResult, IterationTrace, PipelineResult
from rubricon.strategies import (
    ConvergencePolicy,
    ReattentionStrategy,
    convergence_registry,
    reattention_registry,
)
from rubricon.templates import TemplateLoader


@dataclass
class _Components:
    """Resolved plugin instances for one pipeline run."""

    generator_backend: LLMBackend
    evaluator_backend: LLMBackend
    criteria_backend: LLMBackend
    templates: TemplateLoader
    evaluator: Evaluator
    reattention: ReattentionStrategy
    convergence: ConvergencePolicy
    callback_bus: CallbackBus = field(default_factory=CallbackBus)


class RubriconPipeline:
    """Configurable evaluation-first generation pipeline.

    Construct from a :class:`RubriconConfig` (preferred) or from kwargs that map
    to the legacy EFA API.
    """

    def __init__(self, config: RubriconConfig | None = None, **kwargs: Any) -> None:
        if config is None:
            config = RubriconConfig.from_dict(_legacy_kwargs_to_dict(kwargs))
        elif kwargs:
            config = config.override(**kwargs)
        self.config = config
        self._components: _Components | None = None

    # ---------- Public API ----------

    def run(self, prompt: str) -> PipelineResult:
        comp = self._build_components()
        cfg = self.config
        bus = comp.callback_bus

        budget = BudgetTracker(config=cfg.budget)
        bus.emit("on_run_start", prompt=prompt, config=cfg)

        criteria = criteria_module.generate(
            backend=comp.criteria_backend,
            templates=comp.templates,
            prompt=prompt,
            config=cfg.criteria,
        )
        bus.emit("on_criteria_generated", criteria=criteria)

        max_iter = cfg.iteration.max_iterations if cfg.iteration.enabled else 1
        history: list[EvaluationResult] = []
        iterations: list[IterationTrace] = []
        prev_response: str | None = None
        prev_total_tokens = 0
        converged = False
        stopped_reason: str | None = None

        for k in range(1, max_iter + 1):
            bus.emit("on_iteration_start", iteration=k)
            iter_start = time.time()
            weights_before = [c.weight for c in criteria]

            response, drafts = cmpg_module.progressive_generate(
                backend=comp.generator_backend,
                templates=comp.templates,
                user_prompt=prompt,
                criteria=criteria,
                previous_response=prev_response,
                cmpg_config=cfg.cmpg,
            )
            for sub_idx, draft in enumerate(drafts):
                bus.emit("on_draft", iteration=k, sub_step=sub_idx, draft=draft)

            evaluation = comp.evaluator.evaluate(response, criteria, prompt=prompt)
            evaluation.threshold = cfg.convergence.threshold
            history.append(evaluation)
            bus.emit("on_evaluation", iteration=k, evaluation=evaluation)

            converged = comp.convergence.converged(
                evaluation,
                criteria,
                threshold=cfg.convergence.threshold,
                history=history,
            )

            weights_after = list(weights_before)
            if not converged and cfg.reattention.enabled:
                comp.reattention.update(
                    criteria,
                    evaluation,
                    threshold=cfg.convergence.threshold,
                    epsilon=cfg.reattention.epsilon,
                    params=cfg.reattention.params,
                )
                weights_after = [c.weight for c in criteria]

            cur_total = comp.generator_backend.usage.total + comp.evaluator_backend.usage.total
            tokens_iter = cur_total - prev_total_tokens
            prev_total_tokens = cur_total
            budget.add_tokens(tokens_iter)
            budget.tick_iteration()

            trace = IterationTrace(
                iteration=k,
                drafts=drafts,
                response=response,
                evaluation=evaluation,
                weights_before=weights_before,
                weights_after=weights_after,
                tokens_used=tokens_iter,
                wall_seconds=time.time() - iter_start,
            )
            iterations.append(trace)
            bus.emit("on_iteration_end", trace=trace)

            if converged:
                break

            stopped_reason = budget.enforce()
            if stopped_reason is not None:
                break

            prev_response = response

        total_tokens = (
            comp.generator_backend.usage.total
            + comp.evaluator_backend.usage.total
            + comp.criteria_backend.usage.total
        )

        result = PipelineResult(
            prompt=prompt,
            response=iterations[-1].response if iterations else "",
            criteria=criteria,
            iterations=iterations,
            converged=converged,
            total_tokens=total_tokens,
            wall_seconds=budget.wall_seconds,
            method=self._method_name(),
            stopped_reason=stopped_reason,
        )
        bus.emit("on_run_end", result=result)
        return result

    def run_batch(self, prompts: list[str]) -> list[PipelineResult]:
        return [self.run(p) for p in prompts]

    # ---------- Internals ----------

    def _build_components(self) -> _Components:
        if self._components is not None:
            return self._components
        cfg = self.config

        gen_backend = make_backend(cfg.generator, retry=cfg.retry)
        eval_cfg = cfg.evaluator or cfg.generator
        crit_cfg = cfg.criteria_generator or cfg.generator
        eval_backend = (
            gen_backend if eval_cfg is cfg.generator else make_backend(eval_cfg, retry=cfg.retry)
        )
        crit_backend = (
            gen_backend if crit_cfg is cfg.generator else make_backend(crit_cfg, retry=cfg.retry)
        )

        templates = TemplateLoader(cfg.templates)

        evaluator = build_evaluators(
            cfg.evaluators,
            backend=eval_backend,
            templates=templates,
            threshold=cfg.convergence.threshold,
            rubric_scale=cfg.criteria.rubric_scale,
        )
        reattn = reattention_registry.create(
            cfg.reattention.strategy,
            alpha=cfg.reattention.alpha,
            **cfg.reattention.params,
        )
        conv = convergence_registry.create(
            cfg.convergence.policy,
            **cfg.convergence.params,
        )

        bus = CallbackBus(
            callbacks=[callback_registry.create(spec.type, **spec.params) for spec in cfg.callbacks]
        )

        self._components = _Components(
            generator_backend=gen_backend,
            evaluator_backend=eval_backend,
            criteria_backend=crit_backend,
            templates=templates,
            evaluator=evaluator,
            reattention=reattn,
            convergence=conv,
            callback_bus=bus,
        )
        return self._components

    def _method_name(self) -> str:
        cfg = self.config
        if not cfg.criteria.dynamic:
            return "rubricon-no-dyncriteria"
        if not cfg.cmpg.enabled:
            return "rubricon-no-cmpg"
        if not cfg.reattention.enabled:
            return "rubricon-no-fwrl"
        if not cfg.iteration.enabled:
            return "rubricon-no-iteration"
        return "rubricon"


# ---------- Backwards-compatible kwargs shim ----------

def _legacy_kwargs_to_dict(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Translate the legacy ``EFAPipeline(model=, n_criteria=, ...)`` kwargs into config."""
    out: dict[str, Any] = {}
    gen: dict[str, Any] = {}
    ev: dict[str, Any] = {}
    if "model" in kwargs:
        gen["model"] = kwargs.pop("model")
    if "gen_temperature" in kwargs:
        gen["temperature"] = kwargs.pop("gen_temperature")
    if "gen_api_base" in kwargs:
        gen["api_base"] = kwargs.pop("gen_api_base")
    if "gen_api_key" in kwargs:
        gen["api_key"] = kwargs.pop("gen_api_key")
    if "gen_call_delay" in kwargs:
        gen["call_delay"] = kwargs.pop("gen_call_delay")
    if "seed" in kwargs:
        gen["seed"] = kwargs["seed"]
        ev["seed"] = kwargs.pop("seed")

    if "evaluator_model" in kwargs:
        ev["model"] = kwargs.pop("evaluator_model")
    if "eval_temperature" in kwargs:
        ev["temperature"] = kwargs.pop("eval_temperature")
    if "eval_api_base" in kwargs:
        ev["api_base"] = kwargs.pop("eval_api_base")
    if "eval_api_key" in kwargs:
        ev["api_key"] = kwargs.pop("eval_api_key")
    if "eval_call_delay" in kwargs:
        ev["call_delay"] = kwargs.pop("eval_call_delay")

    if gen:
        out["generator"] = gen
    if ev:
        out["evaluator"] = ev

    if "n_criteria" in kwargs:
        out.setdefault("criteria", {})["n"] = kwargs.pop("n_criteria")
    if "dynamic_criteria" in kwargs:
        out.setdefault("criteria", {})["dynamic"] = kwargs.pop("dynamic_criteria")

    if "progressive_masking" in kwargs:
        out["cmpg"] = {"enabled": kwargs.pop("progressive_masking")}

    if "iterative" in kwargs:
        out["iteration"] = {"enabled": kwargs.pop("iterative")}
    if "max_iterations" in kwargs:
        out.setdefault("iteration", {})["max_iterations"] = kwargs.pop("max_iterations")

    reattn: dict[str, Any] = {}
    if "failure_weighting" in kwargs:
        reattn["enabled"] = kwargs.pop("failure_weighting")
    if "alpha" in kwargs:
        reattn["alpha"] = kwargs.pop("alpha")
    if "epsilon" in kwargs:
        reattn["epsilon"] = kwargs.pop("epsilon")
    if reattn:
        out["reattention"] = reattn

    if "threshold" in kwargs:
        out["convergence"] = {"threshold": kwargs.pop("threshold")}
    if "batched_eval" in kwargs:
        out["evaluators"] = [{"type": "llm_judge", "params": {"batched": kwargs.pop("batched_eval")}}]

    if kwargs:
        raise ValueError(f"Unknown legacy kwargs: {sorted(kwargs)}")
    return out
