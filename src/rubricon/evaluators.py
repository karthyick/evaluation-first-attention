"""Evaluator protocol + registry.

The killer feature: evaluators are pluggable and can be mixed per-criterion.
A single rubric can use ``llm_judge`` for "Clarity", ``regex`` for "Must mention X",
and ``function`` for arbitrary Python checks. Aggregation is configurable.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from rubricon.backends import LLMBackend, complete_json
from rubricon.config import PluginSpec
from rubricon.models import Criterion, EvaluationResult
from rubricon.registry import Registry
from rubricon.templates import TemplateLoader


@runtime_checkable
class Evaluator(Protocol):
    """Score a single response against a list of criteria.

    Implementations may be LLM-based, regex-based, code-execution-based, or
    arbitrary Python functions.
    """

    name: str

    def evaluate(
        self,
        response: str,
        criteria: list[Criterion],
        *,
        prompt: str = "",
    ) -> EvaluationResult: ...


evaluator_registry: Registry[Evaluator] = Registry("evaluator")


# ---------------- LLM-judge evaluator ----------------

@dataclass
class LLMJudgeEvaluator:
    backend: LLMBackend
    templates: TemplateLoader
    threshold: float = 0.6
    rubric_scale: int = 5
    batched: bool = False
    name: str = "llm_judge"

    def evaluate(
        self,
        response: str,
        criteria: list[Criterion],
        *,
        prompt: str = "",
    ) -> EvaluationResult:
        if self.batched:
            return self._batch(response, criteria)
        return self._individual(response, criteria)

    def _individual(self, response: str, criteria: list[Criterion]) -> EvaluationResult:
        raw_scores: list[int] = []
        norm: list[float] = []
        reasons: list[str] = []
        for c in criteria:
            score, reason = self._score_one(c, response)
            raw_scores.append(score)
            norm.append(score / self.rubric_scale)
            reasons.append(reason)
        return EvaluationResult(scores=norm, raw_scores=raw_scores, reasoning=reasons, threshold=self.threshold)

    def _score_one(self, c: Criterion, response: str) -> tuple[int, str]:
        sys = self.templates.render("judge_single_system", scale=self.rubric_scale)
        user = self.templates.render(
            "judge_single_user",
            criterion=c,
            response=response,
            scale=self.rubric_scale,
        )
        for _ in range(2):
            try:
                out = complete_json(self.backend, sys, user)
                score = max(1, min(self.rubric_scale, int(out["score"])))
                return score, str(out.get("reasoning", ""))
            except (ValueError, KeyError, TypeError):
                continue
        return 3, "evaluator_parse_failed"

    def _batch(self, response: str, criteria: list[Criterion]) -> EvaluationResult:
        sys = self.templates.render("judge_batch_system", scale=self.rubric_scale)
        user = self.templates.render(
            "judge_batch_user",
            criteria=criteria,
            response=response,
            scale=self.rubric_scale,
        )
        try:
            results = complete_json(self.backend, sys, user)
        except (ValueError, KeyError, TypeError):
            results = []
        raw_scores: list[int] = []
        norm: list[float] = []
        reasons: list[str] = []
        for i, c in enumerate(criteria):
            if isinstance(results, list) and i < len(results):
                try:
                    s = max(1, min(self.rubric_scale, int(results[i]["score"])))
                    r = str(results[i].get("reasoning", ""))
                except (KeyError, TypeError, ValueError):
                    s, r = 3, "evaluator_parse_failed"
            else:
                s, r = 3, "not_evaluated"
            raw_scores.append(s)
            norm.append(s / self.rubric_scale)
            reasons.append(r)
        return EvaluationResult(scores=norm, raw_scores=raw_scores, reasoning=reasons, threshold=self.threshold)


@evaluator_registry.register("llm_judge")
def _make_llm_judge(**params: Any) -> LLMJudgeEvaluator:
    return LLMJudgeEvaluator(
        backend=params["backend"],
        templates=params["templates"],
        threshold=params.get("threshold", 0.6),
        rubric_scale=params.get("rubric_scale", 5),
        batched=params.get("batched", False),
    )


# ---------------- Regex evaluator ----------------

@dataclass
class RegexEvaluator:
    """Score 1 if pattern matches (or doesn't, when ``mode='not_match'``), else 0.

    The criterion's ``metadata`` dict drives behaviour: ``{"pattern": ..., "mode": ...}``.
    """

    threshold: float = 0.6
    name: str = "regex"

    def evaluate(
        self,
        response: str,
        criteria: list[Criterion],
        *,
        prompt: str = "",
    ) -> EvaluationResult:
        scores: list[float] = []
        raws: list[int] = []
        reasons: list[str] = []
        for c in criteria:
            pattern = c.metadata.get("pattern", "")
            mode = c.metadata.get("mode", "match")
            flags = c.metadata.get("flags", 0) or 0
            try:
                hit = bool(re.search(pattern, response, flags))
            except re.error as exc:
                scores.append(0.0)
                raws.append(1)
                reasons.append(f"invalid_regex:{exc}")
                continue
            passed = hit if mode == "match" else not hit
            scores.append(1.0 if passed else 0.0)
            raws.append(5 if passed else 1)
            reasons.append(f"pattern={pattern!r} mode={mode} matched={hit}")
        return EvaluationResult(scores=scores, raw_scores=raws, reasoning=reasons, threshold=self.threshold)


@evaluator_registry.register("regex")
def _make_regex(**params: Any) -> RegexEvaluator:
    return RegexEvaluator(threshold=params.get("threshold", 0.6))


# ---------------- Function evaluator ----------------

@dataclass
class FunctionEvaluator:
    """Wrap an arbitrary callable. Function signature: ``(response, criterion, prompt) -> float``."""

    fn: Callable[[str, Criterion, str], float]
    threshold: float = 0.6
    name: str = "function"

    def evaluate(
        self,
        response: str,
        criteria: list[Criterion],
        *,
        prompt: str = "",
    ) -> EvaluationResult:
        scores: list[float] = []
        raws: list[int] = []
        reasons: list[str] = []
        for c in criteria:
            try:
                s = float(self.fn(response, c, prompt))
            except Exception as exc:
                scores.append(0.0)
                raws.append(1)
                reasons.append(f"function_error:{exc}")
                continue
            s = max(0.0, min(1.0, s))
            scores.append(s)
            raws.append(int(round(s * 5)) or 1)
            reasons.append("function_score")
        return EvaluationResult(scores=scores, raw_scores=raws, reasoning=reasons, threshold=self.threshold)


@evaluator_registry.register("function")
def _make_function(**params: Any) -> FunctionEvaluator:
    fn = params["fn"]
    return FunctionEvaluator(fn=fn, threshold=params.get("threshold", 0.6))


# ---------------- Ensemble ----------------

@dataclass
class EnsembleEvaluator:
    """Combine multiple evaluators into one. Aggregation: min / mean / weighted."""

    members: list[Evaluator]
    aggregation: str = "mean"
    weights: list[float] | None = None
    threshold: float = 0.6
    name: str = "ensemble"

    def evaluate(
        self,
        response: str,
        criteria: list[Criterion],
        *,
        prompt: str = "",
    ) -> EvaluationResult:
        per_member = [m.evaluate(response, criteria, prompt=prompt) for m in self.members]
        n = len(criteria)
        out_scores: list[float] = []
        out_raws: list[int] = []
        out_reasons: list[str] = []

        for i in range(n):
            vals = [r.scores[i] for r in per_member]
            if self.aggregation == "min":
                agg = min(vals)
            elif self.aggregation == "weighted" and self.weights:
                w = self.weights[: len(vals)]
                total_w = sum(w) or 1.0
                agg = sum(v * wi for v, wi in zip(vals, w)) / total_w
            else:
                agg = sum(vals) / len(vals)
            out_scores.append(agg)
            out_raws.append(int(round(agg * 5)) or 1)
            out_reasons.append(
                "; ".join(f"{m.name}={r.scores[i]:.2f}" for m, r in zip(self.members, per_member))
            )
        return EvaluationResult(
            scores=out_scores, raw_scores=out_raws, reasoning=out_reasons, threshold=self.threshold
        )


@evaluator_registry.register("ensemble")
def _make_ensemble(**params: Any) -> EnsembleEvaluator:
    return EnsembleEvaluator(
        members=params["members"],
        aggregation=params.get("aggregation", "mean"),
        weights=params.get("weights"),
        threshold=params.get("threshold", 0.6),
    )


# ---------------- Builder ----------------

def build_evaluators(
    specs: list[PluginSpec],
    *,
    backend: LLMBackend,
    templates: TemplateLoader,
    threshold: float,
    rubric_scale: int,
) -> Evaluator:
    """Resolve ``PluginSpec`` list into a single (possibly ensembled) evaluator."""
    built: list[Evaluator] = []
    for spec in specs:
        params = dict(spec.params)
        if spec.type == "llm_judge":
            params.setdefault("backend", backend)
            params.setdefault("templates", templates)
            params.setdefault("threshold", threshold)
            params.setdefault("rubric_scale", rubric_scale)
        else:
            params.setdefault("threshold", threshold)
        built.append(evaluator_registry.create(spec.type, **params))
    if len(built) == 1:
        return built[0]
    return EnsembleEvaluator(members=built, threshold=threshold)
