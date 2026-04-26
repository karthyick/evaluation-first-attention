"""Rubricon — specification-first generation for LLMs.

Cross the rubricon: generate evaluation criteria *before* generation and use
them as conditioning targets with failure-weighted reattention. Highly
configurable: every phase (backend, evaluator, reattention, convergence,
callbacks, prompts, retry, budget, cache) is a pluggable strategy with a
registry, driven by a single Pydantic ``RubriconConfig``.

Author: Karthick Raja M <karthickrajam18@gmail.com>
"""

from __future__ import annotations

from rubricon.backends import (
    CompletionRequest,
    CompletionResponse,
    LiteLLMBackend,
    LLMBackend,
    MockBackend,
    backend_registry,
)
from rubricon.budget import BudgetExceeded, BudgetTracker
from rubricon.callbacks import (
    BaseCallback,
    ConsoleCallback,
    JSONLCallback,
    PipelineCallback,
    callback_registry,
)
from rubricon.config import (
    BackendConfig,
    BudgetConfig,
    CacheConfig,
    CallbackSpec,
    CMPGConfig,
    ConvergenceConfig,
    CriteriaConfig,
    IterationConfig,
    PluginSpec,
    ReattentionConfig,
    RetryConfig,
    RubriconConfig,
    TemplatesConfig,
    local_ollama,
    production,
    quick,
)
from rubricon.evaluators import (
    EnsembleEvaluator,
    Evaluator,
    FunctionEvaluator,
    LLMJudgeEvaluator,
    RegexEvaluator,
    evaluator_registry,
)
from rubricon.models import Criterion, EvaluationResult, IterationTrace, PipelineResult
from rubricon.pipeline import RubriconPipeline
from rubricon.registry import Registry
from rubricon.strategies import (
    AllPass,
    CompositePolicy,
    ConvergencePolicy,
    FocalReattention,
    MeanThreshold,
    NoImprovement,
    ReattentionStrategy,
    SoftmaxReattention,
    UniformReattention,
    convergence_registry,
    reattention_registry,
)
from rubricon.templates import TemplateLoader

__version__ = "0.2.0"
__author__ = "Karthick Raja M"
__email__ = "karthickrajam18@gmail.com"

__all__ = [
    # Pipeline
    "RubriconPipeline",
    # Config
    "RubriconConfig",
    "BackendConfig",
    "BudgetConfig",
    "CacheConfig",
    "CMPGConfig",
    "ConvergenceConfig",
    "CriteriaConfig",
    "IterationConfig",
    "PluginSpec",
    "CallbackSpec",
    "ReattentionConfig",
    "RetryConfig",
    "TemplatesConfig",
    "quick",
    "local_ollama",
    "production",
    # Models
    "Criterion",
    "EvaluationResult",
    "IterationTrace",
    "PipelineResult",
    # Backends
    "LLMBackend",
    "LiteLLMBackend",
    "MockBackend",
    "CompletionRequest",
    "CompletionResponse",
    "backend_registry",
    # Evaluators
    "Evaluator",
    "LLMJudgeEvaluator",
    "RegexEvaluator",
    "FunctionEvaluator",
    "EnsembleEvaluator",
    "evaluator_registry",
    # Strategies
    "ReattentionStrategy",
    "ConvergencePolicy",
    "FocalReattention",
    "UniformReattention",
    "SoftmaxReattention",
    "AllPass",
    "MeanThreshold",
    "NoImprovement",
    "CompositePolicy",
    "reattention_registry",
    "convergence_registry",
    # Callbacks
    "PipelineCallback",
    "BaseCallback",
    "ConsoleCallback",
    "JSONLCallback",
    "callback_registry",
    # Budget
    "BudgetTracker",
    "BudgetExceeded",
    # Misc
    "Registry",
    "TemplateLoader",
]
