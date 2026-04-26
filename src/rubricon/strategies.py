"""Reattention + Convergence plugin layers.

Both are tiny protocols with a registry, so a user can swap the FWRL formula or
the convergence rule without touching the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp
from typing import Any, Protocol, runtime_checkable

from rubricon.models import Criterion, EvaluationResult
from rubricon.registry import Registry


# ---------------- Reattention ----------------

@runtime_checkable
class ReattentionStrategy(Protocol):
    name: str

    def update(
        self,
        criteria: list[Criterion],
        evaluation: EvaluationResult,
        *,
        threshold: float,
        epsilon: float,
        params: dict[str, Any],
    ) -> None: ...


reattention_registry: Registry[ReattentionStrategy] = Registry("reattention")


def _checkpoint_and_renormalize(
    criteria: list[Criterion],
    evaluation: EvaluationResult,
    threshold: float,
    epsilon: float,
) -> list[int]:
    """Apply checkpoint locking. Returns indices of criteria still unlocked."""
    unlocked: list[int] = []
    for i, c in enumerate(criteria):
        if c.locked:
            continue
        score = evaluation.scores[i]
        if c.best_score >= threshold and score < c.best_score - epsilon:
            c.locked = True
            continue
        c.best_score = max(c.best_score, score)
        unlocked.append(i)
    return unlocked


def _renormalize(criteria: list[Criterion]) -> None:
    locked_total = sum(c.weight for c in criteria if c.locked)
    unlocked_total = sum(c.weight for c in criteria if not c.locked)
    if unlocked_total <= 0:
        return
    remaining = max(0.0, 1.0 - locked_total)
    for c in criteria:
        if not c.locked:
            c.weight = c.weight / unlocked_total * remaining


@dataclass
class FocalReattention:
    """Paper FWRL: w_i <- w_i * (1 + alpha * max(0, tau - s_i))."""

    alpha: float = 2.0
    name: str = "focal"

    def update(
        self,
        criteria: list[Criterion],
        evaluation: EvaluationResult,
        *,
        threshold: float,
        epsilon: float,
        params: dict[str, Any],
    ) -> None:
        unlocked = _checkpoint_and_renormalize(criteria, evaluation, threshold, epsilon)
        for i in unlocked:
            c = criteria[i]
            failure_gap = max(0.0, threshold - evaluation.scores[i])
            c.weight = c.weight * (1.0 + self.alpha * failure_gap)
        _renormalize(criteria)


@dataclass
class UniformReattention:
    """Ablation: keep weights equal across unlocked criteria. Tests FWRL's value."""

    name: str = "uniform"

    def update(
        self,
        criteria: list[Criterion],
        evaluation: EvaluationResult,
        *,
        threshold: float,
        epsilon: float,
        params: dict[str, Any],
    ) -> None:
        _checkpoint_and_renormalize(criteria, evaluation, threshold, epsilon)
        n_unlocked = sum(1 for c in criteria if not c.locked)
        if n_unlocked > 0:
            locked_total = sum(c.weight for c in criteria if c.locked)
            share = max(0.0, 1.0 - locked_total) / n_unlocked
            for c in criteria:
                if not c.locked:
                    c.weight = share


@dataclass
class SoftmaxReattention:
    """Temperature-scaled softmax over (threshold - score). Smooth alternative to focal."""

    temperature: float = 1.0
    name: str = "softmax"

    def update(
        self,
        criteria: list[Criterion],
        evaluation: EvaluationResult,
        *,
        threshold: float,
        epsilon: float,
        params: dict[str, Any],
    ) -> None:
        unlocked = _checkpoint_and_renormalize(criteria, evaluation, threshold, epsilon)
        if not unlocked:
            return
        gaps = [max(0.0, threshold - evaluation.scores[i]) for i in unlocked]
        exps = [exp(g / max(self.temperature, 1e-6)) for g in gaps]
        s = sum(exps) or 1.0
        locked_total = sum(c.weight for c in criteria if c.locked)
        budget = max(0.0, 1.0 - locked_total)
        for idx, e in zip(unlocked, exps):
            criteria[idx].weight = budget * (e / s)


reattention_registry.add("focal", lambda **p: FocalReattention(alpha=p.get("alpha", 2.0)))
reattention_registry.add("uniform", lambda **p: UniformReattention())
reattention_registry.add("softmax", lambda **p: SoftmaxReattention(temperature=p.get("temperature", 1.0)))


# ---------------- Convergence ----------------

@runtime_checkable
class ConvergencePolicy(Protocol):
    name: str

    def converged(
        self,
        evaluation: EvaluationResult,
        criteria: list[Criterion],
        *,
        threshold: float,
        history: list[EvaluationResult],
    ) -> bool: ...


convergence_registry: Registry[ConvergencePolicy] = Registry("convergence")


@dataclass
class AllPass:
    name: str = "all_pass"

    def converged(
        self,
        evaluation: EvaluationResult,
        criteria: list[Criterion],
        *,
        threshold: float,
        history: list[EvaluationResult],
    ) -> bool:
        for i, c in enumerate(criteria):
            score = c.best_score if c.locked else evaluation.scores[i]
            if score < threshold:
                return False
        return True


@dataclass
class MeanThreshold:
    name: str = "mean_threshold"

    def converged(
        self,
        evaluation: EvaluationResult,
        criteria: list[Criterion],
        *,
        threshold: float,
        history: list[EvaluationResult],
    ) -> bool:
        return evaluation.mean_score >= threshold


@dataclass
class NoImprovement:
    """Stop when mean score hasn't improved by ``min_delta`` over the last ``patience`` rounds."""

    patience: int = 2
    min_delta: float = 0.01
    name: str = "no_improvement"

    def converged(
        self,
        evaluation: EvaluationResult,
        criteria: list[Criterion],
        *,
        threshold: float,
        history: list[EvaluationResult],
    ) -> bool:
        if len(history) <= self.patience:
            return False
        baseline = history[-(self.patience + 1)].mean_score
        recent = [h.mean_score for h in history[-self.patience:]]
        return all((s - baseline) < self.min_delta for s in recent)


@dataclass
class CompositePolicy:
    """``mode='any'`` short-circuits on first hit; ``'all'`` requires every member."""

    members: list[ConvergencePolicy]
    mode: str = "any"
    name: str = "composite"

    def converged(self, *args: Any, **kwargs: Any) -> bool:
        results = [m.converged(*args, **kwargs) for m in self.members]
        return any(results) if self.mode == "any" else all(results)


convergence_registry.add("all_pass", lambda **p: AllPass())
convergence_registry.add("mean_threshold", lambda **p: MeanThreshold())
convergence_registry.add(
    "no_improvement",
    lambda **p: NoImprovement(patience=p.get("patience", 2), min_delta=p.get("min_delta", 0.01)),
)
