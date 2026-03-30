"""Unit tests for CMPG progressive generation — Karthick Raja M, 2026."""

from unittest.mock import MagicMock, call

from efa.models import Criterion
from efa.progressive_generator import progressive_generate


def _make_criteria(n: int) -> list[Criterion]:
    return [
        Criterion(
            name=f"Criterion{i + 1}",
            definition=f"Definition for criterion {i + 1}.",
            rubric={1: "poor", 3: "average", 5: "excellent"},
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Progressive masking — call count and draft count
# ---------------------------------------------------------------------------


def test_progressive_masking_makes_grouped_calls():
    """With 3 criteria (group_size=2), expect 2 calls: group [1:2] + final [1:3]."""
    client = MagicMock()
    client.complete.side_effect = ["draft1", "draft2", "draft3"]

    criteria = _make_criteria(3)
    progressive_generate(client, "user prompt", criteria, use_progressive_masking=True)

    # group_size = max(1, (3+1)//2) = 2 → group at j=2, then final pass at j=3 → 2 calls
    assert client.complete.call_count == 2


def test_progressive_masking_returns_grouped_drafts():
    """With 3 criteria, drafts list should match number of groups."""
    client = MagicMock()
    client.complete.side_effect = ["draft1", "draft2", "draft3"]

    criteria = _make_criteria(3)
    _, drafts = progressive_generate(client, "user prompt", criteria, use_progressive_masking=True)

    assert len(drafts) == 2


# ---------------------------------------------------------------------------
# No-masking ablation — call count and draft count
# ---------------------------------------------------------------------------


def test_no_masking_makes_one_call():
    """use_progressive_masking=False should issue exactly one LLM call."""
    client = MagicMock()
    client.complete.return_value = "single draft"

    criteria = _make_criteria(3)
    progressive_generate(client, "user prompt", criteria, use_progressive_masking=False)

    assert client.complete.call_count == 1


def test_no_masking_returns_one_draft():
    """use_progressive_masking=False should return a list with exactly one draft."""
    client = MagicMock()
    client.complete.return_value = "single draft"

    criteria = _make_criteria(3)
    _, drafts = progressive_generate(client, "user prompt", criteria, use_progressive_masking=False)

    assert len(drafts) == 1


# ---------------------------------------------------------------------------
# Draft content at each sub-step
# ---------------------------------------------------------------------------


def test_first_substep_has_no_draft():
    """The first sub-step (j=1) should NOT include 'Improve the following draft'."""
    client = MagicMock()
    client.complete.side_effect = ["draft1", "draft2", "draft3"]

    criteria = _make_criteria(3)
    progressive_generate(
        client, "user prompt", criteria,
        previous_response=None,
        use_progressive_masking=True,
    )

    # First call: second positional arg is the user prompt string
    first_call_user_prompt = client.complete.call_args_list[0][0][1]
    assert "Improve the following draft" not in first_call_user_prompt


def test_subsequent_substeps_include_draft():
    """Sub-steps after the first should include the previous draft text."""
    client = MagicMock()
    client.complete.side_effect = ["draft1", "draft2", "draft3"]

    criteria = _make_criteria(3)
    progressive_generate(
        client, "user prompt", criteria,
        previous_response=None,
        use_progressive_masking=True,
    )

    calls = client.complete.call_args_list

    # Second call (final group) should reference the output of the first group
    second_user_prompt = calls[1][0][1]
    assert "Improve the following draft" in second_user_prompt
    assert "draft1" in second_user_prompt


# ---------------------------------------------------------------------------
# Criteria visibility per sub-step
# ---------------------------------------------------------------------------


def test_visible_criteria_increase_progressively():
    """Earlier groups show fewer criteria; final group shows all."""
    client = MagicMock()
    client.complete.side_effect = ["draft1", "draft2"]

    criteria = _make_criteria(3)
    progressive_generate(client, "user prompt", criteria, use_progressive_masking=True)

    calls = client.complete.call_args_list

    # First group (2 criteria visible)
    first_prompt = calls[0][0][1]
    assert "Criterion1" in first_prompt
    assert "Criterion2" in first_prompt
    assert "Criterion3" not in first_prompt

    # Final group (all 3 criteria visible)
    last_prompt = calls[-1][0][1]
    assert "Criterion1" in last_prompt
    assert "Criterion2" in last_prompt
    assert "Criterion3" in last_prompt


# ---------------------------------------------------------------------------
# previous_response threading
# ---------------------------------------------------------------------------


def test_previous_response_used_as_initial_draft():
    """When previous_response is provided, sub-step j=1 should include it as a draft."""
    client = MagicMock()
    client.complete.side_effect = ["improved_draft1", "improved_draft2"]

    criteria = _make_criteria(2)
    progressive_generate(
        client, "user prompt", criteria,
        previous_response="prior iteration output",
        use_progressive_masking=True,
    )

    first_call_user_prompt = client.complete.call_args_list[0][0][1]
    assert "Improve the following draft" in first_call_user_prompt
    assert "prior iteration output" in first_call_user_prompt
