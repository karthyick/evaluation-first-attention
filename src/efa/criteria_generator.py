"""Component 1: Criteria Generator (Section 3.2) — Karthick Raja M, 2026."""

from __future__ import annotations

from efa.llm_client import LLMClient
from efa.models import Criterion

CRITERIA_SYSTEM_PROMPT = """You are an evaluation criteria designer. Given a user prompt, generate {n} non-overlapping evaluation criteria ordered from most fundamental to least fundamental.

For each criterion, provide:
1. Name (2-4 words)
2. Definition (1 sentence)
3. Scoring rubric:
   - Score 1: [description of lowest quality]
   - Score 2: [description of below-average quality]
   - Score 3: [description of acceptable quality]
   - Score 4: [description of good quality]
   - Score 5: [description of excellent quality]

Requirements:
- Criteria must be measurable and non-overlapping
- Order by fundamentality: correctness before style
- Each criterion must be independently scorable
- Criteria must be specific to this prompt, not generic

Respond as a JSON array of objects with keys: "name", "definition", "rubric" (object with keys "1" through "5")."""

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
        criteria = FIXED_CRITERIA[:n_criteria]
        for c in criteria:
            c.weight = 1.0 / len(criteria)
        return criteria

    system = CRITERIA_SYSTEM_PROMPT.format(n=n_criteria)
    raw = client.complete_json(system=system, user=f"User prompt: {prompt}")

    criteria = []
    for item in raw:
        rubric = {int(k): v for k, v in item["rubric"].items()}
        c = Criterion(
            name=item["name"],
            definition=item["definition"],
            rubric=rubric,
            weight=1.0 / n_criteria,
        )
        criteria.append(c)

    return criteria[:n_criteria]
