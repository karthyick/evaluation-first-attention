"""Layered configuration for Rubricon.

Resolution order (later wins): defaults < YAML/dict file < env vars (RUBRICON_*) < kwargs.

All knobs in the framework live on a single Pydantic ``RubriconConfig`` object.
Every plugin (backend, evaluator, reattention, convergence, callback) is selected
by ``type`` plus a free-form ``params`` dict, so custom user-registered plugins
work exactly like built-ins.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PluginSpec(BaseModel):
    """Generic plugin reference: ``type`` selects from registry, ``params`` configures it."""

    model_config = ConfigDict(extra="forbid")

    type: str
    params: dict[str, Any] = Field(default_factory=dict)


class BackendConfig(BaseModel):
    """LLM backend configuration for a single role (generator / evaluator / criteria)."""

    model_config = ConfigDict(extra="forbid")

    backend: str = "litellm"
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    seed: int | None = None
    api_base: str | None = None
    api_key: str | None = None
    call_delay: float = 0.0
    extra: dict[str, Any] = Field(default_factory=dict)


class RetryConfig(BaseModel):
    """Retry policy for LLM calls — replaces hardcoded MAX_RETRIES module constants."""

    model_config = ConfigDict(extra="forbid")

    max_attempts: int = 3
    base_delay_seconds: float = 15.0
    backoff: Literal["constant", "linear", "exponential"] = "linear"
    jitter: bool = False
    retry_on: list[str] = Field(default_factory=lambda: ["RateLimitError", "APIConnectionError"])


class BudgetConfig(BaseModel):
    """Hard limits enforced at the pipeline level — stops runaway cost / time."""

    model_config = ConfigDict(extra="forbid")

    max_tokens: int | None = None
    max_cost_usd: float | None = None
    max_wall_seconds: float | None = None
    max_iterations: int | None = None
    on_exceed: Literal["raise", "stop"] = "stop"


class CacheConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    backend: Literal["memory", "disk"] = "memory"
    path: str = ".rubricon-cache"
    ttl_seconds: int | None = None


class TemplatesConfig(BaseModel):
    """Override default Jinja2 prompt templates with user paths."""

    model_config = ConfigDict(extra="forbid")

    criteria_generation: str | None = None
    cmpg_step: str | None = None
    judge_single: str | None = None
    judge_batch: str | None = None
    refine_feedback: str | None = None
    fusion_synthesis: str | None = None


class CriteriaConfig(BaseModel):
    """How criteria are produced for each prompt."""

    model_config = ConfigDict(extra="forbid")

    n: int = 5
    dynamic: bool = True
    fixed_set: list[dict[str, Any]] | None = None
    rubric_scale: int = 5


class ReattentionConfig(BaseModel):
    """How weights are updated between iterations."""

    model_config = ConfigDict(extra="forbid")

    strategy: str = "focal"
    enabled: bool = True
    alpha: float = 2.0
    epsilon: float = 0.1
    params: dict[str, Any] = Field(default_factory=dict)


class ConvergenceConfig(BaseModel):
    """When the iteration loop should stop."""

    model_config = ConfigDict(extra="forbid")

    policy: str = "all_pass"
    threshold: float = 0.6
    params: dict[str, Any] = Field(default_factory=dict)


class CMPGConfig(BaseModel):
    """Criteria-Masked Progressive Generation."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    group_size: int | None = None
    final_pass_with_all: bool = True


class IterationConfig(BaseModel):
    """Iterative refinement loop settings."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    max_iterations: int = 3


class CallbackSpec(PluginSpec):
    """Callback plugin — same shape as PluginSpec but separate type for clarity."""


class RubriconConfig(BaseModel):
    """Single source of truth for all Rubricon settings.

    All other modules read from this object; nothing reads env vars directly.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    # Generator / evaluator / criteria-generator backends. Different roles can
    # use different models entirely — e.g. cheap local model for criteria, big
    # frontier model for generation, neutral cross-model evaluator.
    generator: BackendConfig = Field(default_factory=BackendConfig)
    evaluator: BackendConfig | None = None
    criteria_generator: BackendConfig | None = None

    # Phase configuration
    criteria: CriteriaConfig = Field(default_factory=CriteriaConfig)
    cmpg: CMPGConfig = Field(default_factory=CMPGConfig)
    iteration: IterationConfig = Field(default_factory=IterationConfig)
    reattention: ReattentionConfig = Field(default_factory=ReattentionConfig)
    convergence: ConvergenceConfig = Field(default_factory=ConvergenceConfig)

    # Pluggable evaluators — list lets you mix LLM-judge with regex/function/code-exec
    evaluators: list[PluginSpec] = Field(
        default_factory=lambda: [PluginSpec(type="llm_judge")]
    )

    # Cross-cutting
    templates: TemplatesConfig = Field(default_factory=TemplatesConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    callbacks: list[CallbackSpec] = Field(default_factory=list)

    # Reproducibility / debugging
    deterministic: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("convergence")
    @classmethod
    def _validate_threshold(cls, v: ConvergenceConfig) -> ConvergenceConfig:
        if not 0.0 <= v.threshold <= 1.0:
            raise ValueError(f"convergence.threshold must be in [0,1], got {v.threshold}")
        return v

    @model_validator(mode="after")
    def _propagate_seed_when_deterministic(self) -> RubriconConfig:
        if self.deterministic and self.generator.seed is None:
            self.generator.seed = 42
        if self.deterministic and self.evaluator and self.evaluator.seed is None:
            self.evaluator.seed = 42
        return self

    # ---------- Loaders ----------

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RubriconConfig:
        return cls.model_validate(data)

    @classmethod
    def from_yaml(cls, path: str | Path) -> RubriconConfig:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls.from_dict(data)

    @classmethod
    def from_env(cls, prefix: str = "RUBRICON_") -> dict[str, Any]:
        """Read overrides from env vars. Supports nested keys via double underscore.

        Example: ``RUBRICON_GENERATOR__MODEL=gpt-4o`` -> ``{"generator": {"model": "gpt-4o"}}``.
        """
        out: dict[str, Any] = {}
        for key, val in os.environ.items():
            if not key.startswith(prefix):
                continue
            path = key[len(prefix):].lower().split("__")
            cursor = out
            for part in path[:-1]:
                cursor = cursor.setdefault(part, {})
            cursor[path[-1]] = _coerce_env(val)
        return out

    @classmethod
    def load(
        cls,
        path: str | Path | None = None,
        env_prefix: str = "RUBRICON_",
        **overrides: Any,
    ) -> RubriconConfig:
        """Layered load: defaults < file < env < kwargs."""
        data: dict[str, Any] = {}
        if path is not None:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        env_data = cls.from_env(env_prefix)
        _deep_merge(data, env_data)
        _deep_merge(data, overrides)
        return cls.model_validate(data)

    def override(self, **kwargs: Any) -> RubriconConfig:
        """Return a new config with shallow overrides applied at the top level."""
        return self.model_copy(update=kwargs, deep=True)

    def to_yaml(self, path: str | Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.model_dump(mode="json"), f, sort_keys=False)


def _coerce_env(val: str) -> Any:
    low = val.lower()
    if low in {"true", "false"}:
        return low == "true"
    if low in {"null", "none"}:
        return None
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        return val


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def quick(model: str = "gpt-4o", **overrides: Any) -> RubriconConfig:
    """Minimal config preset for one-liner usage."""
    return RubriconConfig.from_dict({"generator": {"model": model}, **overrides})


def local_ollama(model: str = "ollama/qwen3.5:9b") -> RubriconConfig:
    """Zero-cost local preset."""
    return RubriconConfig.from_dict({
        "generator": {"model": model, "temperature": 0.7},
        "evaluator": {"model": model, "temperature": 0.1},
        "criteria": {"n": 3},
        "iteration": {"max_iterations": 2},
    })


def production(generator_model: str, evaluator_model: str) -> RubriconConfig:
    """Cross-model production preset with budget guardrails."""
    return RubriconConfig.from_dict({
        "generator": {"model": generator_model, "temperature": 0.7},
        "evaluator": {"model": evaluator_model, "temperature": 0.1},
        "criteria": {"n": 5},
        "iteration": {"max_iterations": 3},
        "budget": {"max_cost_usd": 1.0, "max_wall_seconds": 120, "on_exceed": "stop"},
        "cache": {"enabled": True, "backend": "disk"},
    })
