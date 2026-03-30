"""Component 3a: Per-Criterion Evaluator (Section 3.4) — Karthick Raja M, 2026."""

from __future__ import annotations

from efa.llm_client import LLMClient
from efa.models import Criterion, EvaluationResult

EVAL_SYSTEM_PROMPT = """You are a strict, objective evaluator. Score the given response against a SINGLE evaluation criterion using its rubric.

You MUST respond with valid JSON containing:
- "score": integer from 1 to 5
- "reasoning": 1-2 sentence justification

Be critical and precise. Do not inflate scores. A score of 3 means "acceptable" — reserve 4-5 for genuinely strong responses."""

EVAL_USER_TEMPLATE = """Criterion: {name}
Definition: {definition}

Scoring rubric:
- Score 1: {r1}
- Score 2: {r2}
- Score 3: {r3}
- Score 4: {r4}
- Score 5: {r5}

Response to evaluate:
{response}

Score this response on the "{name}" criterion ONLY. Respond with JSON: {{"score": <1-5>, "reasoning": "<explanation>"}}"""

BATCH_EVAL_SYSTEM_PROMPT = """You are a strict, objective evaluator. Score the given response against ALL provided evaluation criteria independently.

You MUST respond with valid JSON: an array of objects, each with:
- "criterion": the criterion name
- "score": integer from 1 to 5
- "reasoning": 1-2 sentence justification

Be critical and precise. Do not inflate scores. Evaluate each criterion INDEPENDENTLY."""


def evaluate_per_criterion(
    client: LLMClient,
    response: str,
    criteria: list[Criterion],
    batched: bool = False,
) -> EvaluationResult:
    """Score a response against each criterion independently.

    Args:
        client: LLM client for evaluation.
        response: The response text to evaluate.
        criteria: List of criteria to score against.
        batched: If True, score all criteria in one LLM call (cheaper, less precise).

    Returns:
        EvaluationResult with per-criterion scores.
    """
    if batched:
        return _evaluate_batched(client, response, criteria)
    return _evaluate_individual(client, response, criteria)


def _evaluate_individual(
    client: LLMClient,
    response: str,
    criteria: list[Criterion],
) -> EvaluationResult:
    """Score each criterion with a separate LLM call (more precise)."""
    raw_scores: list[int] = []
    normalized: list[float] = []
    reasonings: list[str] = []

    for c in criteria:
        user = EVAL_USER_TEMPLATE.format(
            name=c.name,
            definition=c.definition,
            r1=c.rubric.get(1, ""),
            r2=c.rubric.get(2, ""),
            r3=c.rubric.get(3, ""),
            r4=c.rubric.get(4, ""),
            r5=c.rubric.get(5, ""),
            response=response,
        )

        # Retry once on parse failure, then default to score 3 (acceptable)
        score = 3
        reasoning = ""
        for _attempt in range(2):
            try:
                result = client.complete_json(system=EVAL_SYSTEM_PROMPT, user=user)
                score = max(1, min(5, int(result["score"])))
                reasoning = result.get("reasoning", "")
                break
            except (ValueError, KeyError, TypeError):
                continue

        raw_scores.append(score)
        normalized.append(score / 5.0)
        reasonings.append(reasoning)

    return EvaluationResult(
        scores=normalized,
        raw_scores=raw_scores,
        reasoning=reasonings,
    )


def _evaluate_batched(
    client: LLMClient,
    response: str,
    criteria: list[Criterion],
) -> EvaluationResult:
    """Score all criteria in one LLM call (cheaper, ~1.5x cost of single eval)."""
    criteria_text = ""
    for i, c in enumerate(criteria, 1):
        criteria_text += (
            f"\n{i}. {c.name}: {c.definition}\n"
            f"   Rubric: 1={c.rubric.get(1, '')}, 3={c.rubric.get(3, '')}, 5={c.rubric.get(5, '')}\n"
        )

    user = (
        f"Evaluate this response against ALL criteria below.\n\n"
        f"Criteria:{criteria_text}\n\n"
        f"Response to evaluate:\n{response}\n\n"
        f"Return a JSON array with one object per criterion."
    )

    # Retry once on parse failure, default to all-3 scores
    try:
        results = client.complete_json(system=BATCH_EVAL_SYSTEM_PROMPT, user=user)
    except (ValueError, KeyError, TypeError):
        try:
            results = client.complete_json(system=BATCH_EVAL_SYSTEM_PROMPT, user=user)
        except (ValueError, KeyError, TypeError):
            results = []

    raw_scores: list[int] = []
    normalized: list[float] = []
    reasonings: list[str] = []

    # Match results to criteria by order
    for i, c in enumerate(criteria):
        if i < len(results):
            score = max(1, min(5, int(results[i]["score"])))
            reasoning = results[i].get("reasoning", "")
        else:
            score = 3  # Default if evaluator missed a criterion
            reasoning = "Not evaluated"

        raw_scores.append(score)
        normalized.append(score / 5.0)
        reasonings.append(reasoning)

    return EvaluationResult(
        scores=normalized,
        raw_scores=raw_scores,
        reasoning=reasonings,
    )
