"""Prompt templates as Jinja2.

Built-in templates ship in ``rubricon._prompts``. Users override any template by
pointing the ``templates`` config block at their own files. Falls back to plain
``str.format``-style if Jinja2 isn't installed.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

from rubricon.config import TemplatesConfig

_BUILTIN_PACKAGE = "rubricon._prompts"
_BUILTIN_NAMES = {
    "criteria_system": "criteria_system.j2",
    "criteria_user": "criteria_user.j2",
    "cmpg_system": "cmpg_system.j2",
    "cmpg_user": "cmpg_user.j2",
    "judge_single_system": "judge_single_system.j2",
    "judge_single_user": "judge_single_user.j2",
    "judge_batch_system": "judge_batch_system.j2",
    "judge_batch_user": "judge_batch_user.j2",
    "refine_feedback": "refine_feedback.j2",
    "fusion_synthesis": "fusion_synthesis.j2",
}


class TemplateLoader:
    """Resolve template name -> rendered string. Reads overrides first."""

    def __init__(self, overrides: TemplatesConfig | None = None) -> None:
        self._overrides: dict[str, str] = {}
        self._cache: dict[str, str] = {}
        self._jinja_env: Any | None = None
        if overrides:
            self._collect_overrides(overrides)
        self._setup_jinja()

    def _collect_overrides(self, overrides: TemplatesConfig) -> None:
        # Each user-facing override key may map to one or more internal names.
        mapping = {
            "criteria_generation": ["criteria_system", "criteria_user"],
            "cmpg_step": ["cmpg_system", "cmpg_user"],
            "judge_single": ["judge_single_system", "judge_single_user"],
            "judge_batch": ["judge_batch_system", "judge_batch_user"],
            "refine_feedback": ["refine_feedback"],
            "fusion_synthesis": ["fusion_synthesis"],
        }
        for user_key, internal_keys in mapping.items():
            path = getattr(overrides, user_key, None)
            if not path:
                continue
            content = Path(path).read_text(encoding="utf-8")
            for k in internal_keys:
                self._overrides[k] = content

    def _setup_jinja(self) -> None:
        try:
            from jinja2 import Environment, StrictUndefined
            self._jinja_env = Environment(
                undefined=StrictUndefined,
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=False,
            )
        except ImportError:
            self._jinja_env = None

    def _read_builtin(self, name: str) -> str:
        if name in self._cache:
            return self._cache[name]
        filename = _BUILTIN_NAMES[name]
        try:
            text = resources.files(_BUILTIN_PACKAGE).joinpath(filename).read_text(encoding="utf-8")
        except (ModuleNotFoundError, FileNotFoundError):
            text = _FALLBACK_TEMPLATES[name]
        self._cache[name] = text
        return text

    def get_source(self, name: str) -> str:
        if name in self._overrides:
            return self._overrides[name]
        return self._read_builtin(name)

    def render(self, name: str, **vars: Any) -> str:
        src = self.get_source(name)
        if self._jinja_env is not None:
            return self._jinja_env.from_string(src).render(**vars)
        # Minimal Python-format fallback when Jinja2 is unavailable
        try:
            return src.format(**vars)
        except (KeyError, IndexError):
            return src


# Hardcoded fallbacks used only if package data is missing AND jinja2 absent.
# Real defaults live in src/rubricon/_prompts/*.j2 and ship as package_data.
_FALLBACK_TEMPLATES: dict[str, str] = {
    "criteria_system": (
        "Generate EXACTLY {n} evaluation criteria as a JSON array. "
        "Format: [{\"name\":\"X\",\"definition\":\"Y\",\"rubric\":{\"1\":\"bad\",\"2\":\"below avg\","
        "\"3\":\"ok\",\"4\":\"good\",\"5\":\"excellent\"}}]"
    ),
    "criteria_user": "User prompt: {prompt}",
    "cmpg_system": "You are a helpful assistant. Generate a high-quality response to the user's prompt.",
    "cmpg_user": "User prompt: {user_prompt}",
    "judge_single_system": (
        "You are a strict, objective evaluator. Score the given response against a SINGLE "
        "evaluation criterion using its rubric. Respond with JSON: "
        "{\"score\": <1-{scale}>, \"reasoning\": \"<text>\"}"
    ),
    "judge_single_user": "Criterion: {criterion} Response: {response}",
    "judge_batch_system": (
        "You are a strict evaluator. Score the response against ALL criteria. "
        "Respond with JSON array of {\"criterion\", \"score\", \"reasoning\"}."
    ),
    "judge_batch_user": "Criteria: {criteria} Response: {response}",
    "refine_feedback": "Provide feedback on what needs improvement.",
    "fusion_synthesis": "Synthesize a single superior response from the candidates above.",
}
