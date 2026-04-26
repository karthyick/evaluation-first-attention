"""Public data models. Re-exported from rubricon top level."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Criterion:
    name: str
    definition: str
    rubric: dict[int, str]
    weight: float = 0.2
    locked: bool = False
    best_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def priority_label(self, n_criteria: int, scale: tuple[float, float, float] = (2.0, 1.5, 0.5)) -> str:
        """Map normalized weight to a priority directive used in the generation prompt."""
        uniform = 1.0 / max(n_criteria, 1)
        crit, high, std = scale
        if self.weight > crit * uniform:
            return "[CRITICAL — highest priority]"
        if self.weight > high * uniform:
            return "[HIGH — elevated priority]"
        if self.weight >= std * uniform:
            return "[STANDARD — normal priority]"
        return "[SECONDARY — lower priority]"


@dataclass
class EvaluationResult:
    scores: list[float]
    raw_scores: list[int]
    reasoning: list[str]
    threshold: float = 0.6

    @property
    def min_score(self) -> float:
        return min(self.scores) if self.scores else 0.0

    @property
    def mean_score(self) -> float:
        return sum(self.scores) / max(len(self.scores), 1)

    @property
    def all_pass(self) -> bool:
        return all(s >= self.threshold for s in self.scores)


@dataclass
class IterationTrace:
    iteration: int
    drafts: list[str]
    response: str
    evaluation: EvaluationResult
    weights_before: list[float]
    weights_after: list[float]
    tokens_used: int = 0
    wall_seconds: float = 0.0


@dataclass
class PipelineResult:
    prompt: str
    response: str
    criteria: list[Criterion]
    iterations: list[IterationTrace]
    converged: bool
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    wall_seconds: float = 0.0
    method: str = "rubricon"
    stopped_reason: str | None = None  # populated when budget cuts the run short

    @property
    def n_iterations(self) -> int:
        return len(self.iterations)

    @property
    def final_scores(self) -> list[float]:
        return self.iterations[-1].evaluation.scores if self.iterations else []

    @property
    def rubric_adherence_score(self) -> float:
        scores = self.final_scores
        return sum(scores) / max(len(scores), 1) if scores else 0.0

    @property
    def all_pass(self) -> bool:
        return self.iterations[-1].evaluation.all_pass if self.iterations else False
