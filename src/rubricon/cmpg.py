"""Criteria-Masked Progressive Generation (CMPG)."""

from __future__ import annotations

from rubricon.backends import CompletionRequest, LLMBackend
from rubricon.config import CMPGConfig
from rubricon.models import Criterion
from rubricon.templates import TemplateLoader


def _render_step(
    templates: TemplateLoader,
    user_prompt: str,
    draft: str | None,
    visible: list[Criterion],
    n_total: int,
) -> tuple[str, str]:
    sys = templates.render("cmpg_system")
    user = templates.render(
        "cmpg_user",
        user_prompt=user_prompt,
        draft=draft,
        visible_criteria=visible,
        n_total=n_total,
    )
    return sys, user


def progressive_generate(
    backend: LLMBackend,
    templates: TemplateLoader,
    user_prompt: str,
    criteria: list[Criterion],
    previous_response: str | None,
    cmpg_config: CMPGConfig,
) -> tuple[str, list[str]]:
    n = len(criteria)
    drafts: list[str] = []

    if not cmpg_config.enabled or n == 0:
        sys, user = _render_step(templates, user_prompt, previous_response, criteria, n)
        resp = backend.complete(CompletionRequest(system=sys, user=user))
        return resp.text, [resp.text]

    group_size = cmpg_config.group_size or max(1, (n + 1) // 2)
    current = previous_response
    visible_end = 0
    for j in range(group_size, n + 1, group_size):
        visible_end = min(j, n)
        sys, user = _render_step(templates, user_prompt, current, criteria[:visible_end], n)
        current = backend.complete(CompletionRequest(system=sys, user=user)).text
        drafts.append(current)

    if cmpg_config.final_pass_with_all and (not drafts or visible_end < n):
        sys, user = _render_step(templates, user_prompt, current, criteria, n)
        current = backend.complete(CompletionRequest(system=sys, user=user)).text
        drafts.append(current)

    return current or "", drafts
