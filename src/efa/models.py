"""Data models for EFA pipeline — Karthick Raja M, 2026."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Criterion:
    """Single evaluation criterion with rubric."""

    name: str
    definition: str
    rubric: dict[int, str]  # {1: "lowest", 2: "below avg", ..., 5: "excellent"}
    weight: float = 0.2
    locked: bool = False
    best_score: float = 0.0

    def priority_label(self, n_criteria: int) -> str:
        """Map normalized weight to priority directive (Eq. 6 from paper)."""
        uniform = 1.0 / max(n_criteria, 1)
        if self.weight > 2 * uniform:
            return "[CRITICAL — highest priority]"
        elif self.weight > 1.5 * uniform:
            return "[HIGH — elevated priority]"
        elif self.weight >= 0.5 * uniform:
            return "[STANDARD — normal priority]"
        else:
            return "[SECONDARY — lower priority]"


@dataclass
class EvaluationResult:
    """Per-criterion evaluation scores for one iteration."""

    scores: list[float]  # Normalized [0, 1] per criterion
    raw_scores: list[int]  # Raw rubric scores [1-5]
    reasoning: list[str]  # Judge reasoning per criterion

    @property
    def min_score(self) -> float:
        return min(self.scores) if self.scores else 0.0

    @property
    def mean_score(self) -> float:
        return sum(self.scores) / max(len(self.scores), 1)

    @property
    def all_pass(self) -> bool:
        return all(s >= 0.6 for s in self.scores)


@dataclass
class IterationTrace:
    """Record of one EFA iteration."""

    iteration: int
    drafts: list[str]  # Sub-step drafts d_1 ... d_n
    response: str  # Final R^(k)
    evaluation: EvaluationResult
    weights_before: list[float]
    weights_after: list[float]
    tokens_used: int = 0


@dataclass
class PipelineResult:
    """Complete EFA pipeline output."""

    prompt: str
    response: str
    criteria: list[Criterion]
    iterations: list[IterationTrace]
    converged: bool
    total_tokens: int = 0
    method: str = "efa"

    @property
    def n_iterations(self) -> int:
        return len(self.iterations)

    @property
    def final_scores(self) -> list[float]:
        if self.iterations:
            return self.iterations[-1].evaluation.scores
        return []

    @property
    def rubric_adherence_score(self) -> float:
        """RAS: Mean per-criterion score."""
        scores = self.final_scores
        return sum(scores) / max(len(scores), 1) if scores else 0.0

    @property
    def all_pass(self) -> bool:
        """APR: All criteria >= threshold."""
        return self.iterations[-1].evaluation.all_pass if self.iterations else False


@dataclass
class ExperimentRecord:
    """One row in experiment results."""

    prompt_id: str
    prompt: str
    method: str
    ras: float  # Rubric Adherence Score
    apr: bool  # All-Pass Rate
    itc: int  # Iterations to Convergence
    ttc: int  # Total Token Cost
    response: str
    generator_model: str = ""  # Model used for generation (reproducibility)
    evaluator_model: str = ""  # Model used for evaluation (reproducibility)
    criteria_names: list[str] = field(default_factory=list)
    per_criterion_scores: list[float] = field(default_factory=list)
