"""Component 2: Criteria-Masked Progressive Generation / CMPG (Section 3.3) — Karthick Raja M, 2026."""

from __future__ import annotations

from efa.llm_client import LLMClient
from efa.models import Criterion


def _build_progressive_prompt(
    user_prompt: str,
    draft: str | None,
    visible_criteria: list[Criterion],
    n_total: int,
) -> tuple[str, str]:
    """Build the generation prompt for sub-step j (Eq. 4 from paper).

    Returns (system_prompt, user_prompt) tuple.
    """
    system = "You are a helpful assistant. Generate a high-quality response to the user's prompt."

    criteria_block = []
    for c in visible_criteria:
        label = c.priority_label(n_total)
        criteria_block.append(
            f"{label} {c.name}:\n  {c.definition}"
        )

    criteria_text = "\n\n".join(criteria_block)

    if draft:
        user = (
            f"Improve the following draft to better satisfy the criteria below.\n\n"
            f"CURRENT DRAFT:\n{draft}\n\n"
            f"Your response MUST satisfy the following criteria, listed in priority order:\n\n"
            f"{criteria_text}\n\n"
            f"User prompt: {user_prompt}"
        )
    else:
        user = (
            f"Your response MUST satisfy the following criteria, listed in priority order:\n\n"
            f"{criteria_text}\n\n"
            f"User prompt: {user_prompt}"
        )

    return system, user


def progressive_generate(
    client: LLMClient,
    user_prompt: str,
    criteria: list[Criterion],
    previous_response: str | None = None,
    use_progressive_masking: bool = True,
) -> tuple[str, list[str]]:
    """Run CMPG: progressive criteria unmasking over n sub-steps.

    Args:
        client: LLM client for generation.
        user_prompt: Original user prompt.
        criteria: Ordered list of criteria with current weights.
        previous_response: Output from previous iteration (None for first).
        use_progressive_masking: If False, show all criteria at once (ablation -CMPG).

    Returns:
        (final_response, list_of_intermediate_drafts)
    """
    n = len(criteria)
    drafts: list[str] = []

    if not use_progressive_masking:
        # Ablation: All-Criteria-at-Once — single generation with all criteria visible
        system, user = _build_progressive_prompt(
            user_prompt=user_prompt,
            draft=previous_response,
            visible_criteria=criteria,
            n_total=n,
        )
        response = client.complete(system, user)
        return response, [response]

    # Full CMPG: progressive unmasking in groups
    # Instead of n individual sub-steps, batch into ceil(n/2) groups
    # to reduce LLM calls while preserving the curriculum effect.
    current_draft = previous_response
    group_size = max(1, (n + 1) // 2)  # ~2-3 groups instead of n

    for j in range(group_size, n + 1, group_size):
        # Reveal criteria up to position j (batched)
        visible_end = min(j, n)
        visible = criteria[:visible_end]

        system, user = _build_progressive_prompt(
            user_prompt=user_prompt,
            draft=current_draft,
            visible_criteria=visible,
            n_total=n,
        )

        current_draft = client.complete(system, user)
        drafts.append(current_draft)

    # Final pass with ALL criteria (if not already included)
    if len(drafts) == 0 or visible_end < n:
        system, user = _build_progressive_prompt(
            user_prompt=user_prompt,
            draft=current_draft,
            visible_criteria=criteria,
            n_total=n,
        )
        current_draft = client.complete(system, user)
        drafts.append(current_draft)

    return current_draft or "", drafts
