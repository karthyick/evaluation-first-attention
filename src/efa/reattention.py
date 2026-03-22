"""Component 3b: Failure-Weighted Reattention Loop / FWRL (Section 3.4) — Karthick Raja M, 2026."""

from __future__ import annotations

from efa.models import Criterion, EvaluationResult


def update_weights(
    criteria: list[Criterion],
    evaluation: EvaluationResult,
    alpha: float = 2.0,
    threshold: float = 0.6,
    epsilon: float = 0.1,
) -> list[Criterion]:
    """Apply failure-weighted reattention (Eq. 7 from paper).

    Updates criterion weights in-place and handles checkpoint locking.

    Args:
        criteria: Current criteria with weights and best scores.
        evaluation: Per-criterion evaluation from current iteration.
        alpha: Reattention strength hyperparameter.
        threshold: Passing threshold tau.
        epsilon: Regression tolerance for checkpoint locking.

    Returns:
        Updated criteria list (same objects, modified in-place).
    """
    for i, c in enumerate(criteria):
        score = evaluation.scores[i]

        if c.locked:
            # Locked criteria retain their peak score (checkpoint mechanism)
            continue

        # Checkpoint: detect regression on previously-passing criteria
        if c.best_score >= threshold and score < c.best_score - epsilon:
            c.locked = True
            continue

        # Update best score
        c.best_score = max(c.best_score, score)

        # Failure-weighted reattention (Eq. 7)
        failure_gap = max(0.0, threshold - score)
        c.weight = c.weight * (1.0 + alpha * failure_gap)

    # Renormalize weights to sum to 1
    _normalize_weights(criteria)

    return criteria


def _normalize_weights(criteria: list[Criterion]) -> None:
    """Normalize weights to sum to 1, excluding locked criteria."""
    total = sum(c.weight for c in criteria if not c.locked)
    locked_total = sum(c.weight for c in criteria if c.locked)

    if total > 0:
        # Distribute remaining weight budget among unlocked criteria
        for c in criteria:
            if not c.locked:
                c.weight = c.weight / (total + locked_total)
            else:
                c.weight = c.weight / (total + locked_total)
    else:
        # All locked — keep current weights
        total_all = sum(c.weight for c in criteria)
        if total_all > 0:
            for c in criteria:
                c.weight = c.weight / total_all


def check_convergence(
    evaluation: EvaluationResult,
    criteria: list[Criterion],
    threshold: float = 0.6,
) -> bool:
    """Check if all criteria pass threshold (using locked scores where applicable)."""
    for i, c in enumerate(criteria):
        effective_score = c.best_score if c.locked else evaluation.scores[i]
        if effective_score < threshold:
            return False
    return True
