"""Component 1: Criteria Generator (Section 3.2) — Karthick Raja M, 2026."""

from __future__ import annotations

import copy

from efa.llm_client import LLMClient
from efa.models import Criterion

CRITERIA_SYSTEM_PROMPT = """Generate EXACTLY {n} evaluation criteria as a JSON array. Be CONCISE — keep rubric descriptions under 8 words each.

Format: [{{"name":"X","definition":"Y","rubric":{{"1":"bad","2":"below avg","3":"ok","4":"good","5":"excellent"}}}}]

Rules: non-overlapping, ordered by importance (correctness first), specific to the prompt. Generate EXACTLY {n} items, then STOP."""

FIXED_CRITERIA = [
    Criterion(
        name="Factual Accuracy",
        definition="The response contains factually correct information with no errors.",
        rubric={
            1: "Multiple factual errors or fabrications",
            2: "Several inaccuracies that undermine trust",
            3: "Mostly accurate with minor errors",
            4: "Accurate with negligible issues",
            5: "Completely accurate and verifiable",
        },
    ),
    Criterion(
        name="Relevance",
        definition="The response directly addresses the user's question or request.",
        rubric={
            1: "Completely off-topic or irrelevant",
            2: "Partially relevant but misses the core request",
            3: "Addresses the main point but with tangents",
            4: "Focused and relevant throughout",
            5: "Precisely targeted with no wasted content",
        },
    ),
    Criterion(
        name="Completeness",
        definition="The response covers all necessary aspects of the topic.",
        rubric={
            1: "Major gaps or missing critical information",
            2: "Covers basics but misses important aspects",
            3: "Adequate coverage of main points",
            4: "Thorough coverage with good depth",
            5: "Comprehensive and exhaustive treatment",
        },
    ),
    Criterion(
        name="Clarity",
        definition="The response is well-organized and easy to understand.",
        rubric={
            1: "Confusing, disorganized, or incoherent",
            2: "Understandable but poorly structured",
            3: "Clear with reasonable organization",
            4: "Well-structured and easy to follow",
            5: "Exceptionally clear with logical flow",
        },
    ),
    Criterion(
        name="Conciseness",
        definition="The response is appropriately concise without unnecessary verbosity.",
        rubric={
            1: "Extremely verbose or padded",
            2: "Noticeably wordy with redundancy",
            3: "Reasonable length with some excess",
            4: "Concise with minimal waste",
            5: "Optimally concise — every word earns its place",
        },
    ),
]


def generate_criteria(
    client: LLMClient,
    prompt: str,
    n_criteria: int = 5,
    dynamic: bool = True,
) -> list[Criterion]:
    """Generate evaluation criteria for a prompt.

    Args:
        client: LLM client for generation.
        prompt: User prompt to generate criteria for.
        n_criteria: Number of criteria to generate.
        dynamic: If True, generate per-query criteria. If False, use fixed universal set.

    Returns:
        List of Criterion objects with uniform initial weights.
    """
    if not dynamic:
        criteria = copy.deepcopy(FIXED_CRITERIA[:n_criteria])
        for c in criteria:
            c.weight = 1.0 / len(criteria)
        return criteria

    system = CRITERIA_SYSTEM_PROMPT.format(n=n_criteria)

    # Use a constrained client for criteria gen — prevent runaway output
    crit_client = LLMClient(
        model=client.model,
        temperature=client.temperature,
        max_tokens=1500,
        tracker=client.tracker,
        api_base=client.api_base,
        api_key=client.api_key,
        call_delay=client.call_delay,
    )

    # Retry up to 2 times, then fall back to fixed criteria
    for attempt in range(2):
        try:
            raw = crit_client.complete_json(system=system, user=f"User prompt: {prompt}")
            criteria = _parse_criteria_response(raw, n_criteria)
            if criteria:
                return criteria
        except (ValueError, KeyError, TypeError):
            continue

    # Fallback: use fixed criteria if dynamic generation fails
    criteria = copy.deepcopy(FIXED_CRITERIA[:n_criteria])
    for c in criteria:
        c.weight = 1.0 / len(criteria)
    return criteria


def _parse_criteria_response(raw: list | dict, n_criteria: int) -> list[Criterion]:
    """Parse criteria from LLM response, handling multiple formats."""
    if not isinstance(raw, list) or len(raw) == 0:
        return []

    criteria = []
    for item in raw:
        if isinstance(item, str):
            # Model returned simple strings like ["Clarity", "Accuracy"]
            # Convert to Criterion with generic rubric
            c = Criterion(
                name=item[:50],
                definition=item,
                rubric={
                    1: "Very poor", 2: "Below average",
                    3: "Acceptable", 4: "Good", 5: "Excellent",
                },
                weight=1.0 / n_criteria,
            )
            criteria.append(c)
        elif isinstance(item, dict) and "name" in item:
            rubric_raw = item.get("rubric", {})
            if isinstance(rubric_raw, dict):
                rubric = {int(k): str(v) for k, v in rubric_raw.items()}
            else:
                rubric = {1: "Very poor", 2: "Below average", 3: "Acceptable", 4: "Good", 5: "Excellent"}
            c = Criterion(
                name=item["name"],
                definition=item.get("definition", item["name"]),
                rubric=rubric,
                weight=1.0 / n_criteria,
            )
            criteria.append(c)

    return criteria[:n_criteria]
