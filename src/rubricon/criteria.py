"""Criteria generation. Templates + JSON parsing + dynamic/fixed switching."""

from __future__ import annotations

import copy
from typing import Any

from rubricon.backends import LLMBackend, complete_json
from rubricon.config import CriteriaConfig
from rubricon.models import Criterion
from rubricon.templates import TemplateLoader

# Default fallback criteria — used when ``dynamic=False`` or generation fails.
DEFAULT_FIXED_CRITERIA: list[dict[str, Any]] = [
    {
        "name": "Factual Accuracy",
        "definition": "The response contains factually correct information with no errors.",
        "rubric": {
            1: "Multiple factual errors or fabrications",
            2: "Several inaccuracies that undermine trust",
            3: "Mostly accurate with minor errors",
            4: "Accurate with negligible issues",
            5: "Completely accurate and verifiable",
        },
    },
    {
        "name": "Relevance",
        "definition": "The response directly addresses the user's question or request.",
        "rubric": {
            1: "Completely off-topic or irrelevant",
            2: "Partially relevant but misses the core request",
            3: "Addresses the main point but with tangents",
            4: "Focused and relevant throughout",
            5: "Precisely targeted with no wasted content",
        },
    },
    {
        "name": "Completeness",
        "definition": "The response covers all necessary aspects of the topic.",
        "rubric": {
            1: "Major gaps or missing critical information",
            2: "Covers basics but misses important aspects",
            3: "Adequate coverage of main points",
            4: "Thorough coverage with good depth",
            5: "Comprehensive and exhaustive treatment",
        },
    },
    {
        "name": "Clarity",
        "definition": "The response is well-organized and easy to understand.",
        "rubric": {
            1: "Confusing, disorganized, or incoherent",
            2: "Understandable but poorly structured",
            3: "Clear with reasonable organization",
            4: "Well-structured and easy to follow",
            5: "Exceptionally clear with logical flow",
        },
    },
    {
        "name": "Conciseness",
        "definition": "The response is appropriately concise without unnecessary verbosity.",
        "rubric": {
            1: "Extremely verbose or padded",
            2: "Noticeably wordy with redundancy",
            3: "Reasonable length with some excess",
            4: "Concise with minimal waste",
            5: "Optimally concise — every word earns its place",
        },
    },
]


def _from_dict(item: dict[str, Any], n: int) -> Criterion:
    rubric_raw = item.get("rubric", {})
    rubric = (
        {int(k): str(v) for k, v in rubric_raw.items()}
        if isinstance(rubric_raw, dict)
        else {1: "Very poor", 2: "Below average", 3: "Acceptable", 4: "Good", 5: "Excellent"}
    )
    return Criterion(
        name=item.get("name", "Unnamed"),
        definition=item.get("definition", item.get("name", "")),
        rubric=rubric,
        weight=1.0 / max(n, 1),
        metadata=item.get("metadata", {}),
    )


def _fixed(config: CriteriaConfig) -> list[Criterion]:
    source = config.fixed_set or DEFAULT_FIXED_CRITERIA
    n = config.n
    items = copy.deepcopy(source[:n])
    return [_from_dict(it, n) for it in items]


def _parse_response(raw: Any, n: int) -> list[Criterion]:
    if not isinstance(raw, list) or not raw:
        return []
    out: list[Criterion] = []
    for item in raw[:n]:
        if isinstance(item, str):
            out.append(_from_dict(
                {
                    "name": item[:50],
                    "definition": item,
                    "rubric": {1: "Very poor", 2: "Below average", 3: "Acceptable", 4: "Good", 5: "Excellent"},
                },
                n,
            ))
        elif isinstance(item, dict) and "name" in item:
            out.append(_from_dict(item, n))
    return out


def generate(
    backend: LLMBackend,
    templates: TemplateLoader,
    prompt: str,
    config: CriteriaConfig,
) -> list[Criterion]:
    """Produce criteria for a prompt, dynamic by default, falling back to fixed on failure."""
    if not config.dynamic:
        return _fixed(config)

    sys = templates.render("criteria_system", n=config.n)
    user = templates.render("criteria_user", prompt=prompt)

    for _ in range(2):
        try:
            raw = complete_json(backend, sys, user)
            criteria = _parse_response(raw, config.n)
            if criteria:
                return criteria
        except (ValueError, KeyError, TypeError):
            continue
    return _fixed(config)
