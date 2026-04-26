# Changelog

All notable changes to Rubricon are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2026-04-26

### Changed
- Discoverability: added classifiers (`Environment :: Console`, `Natural Language :: English`, `Topic :: Scientific/Engineering :: Information Analysis`).
- Discoverability: added keywords (`eval`, `rubric-eval`, `llm-as-judge`, `judge`, `efa`) for PyPI search.

## [0.2.0] - 2026-04-26

First public release on PyPI under the `rubricon` name (formerly `evaluation-first-attention`). Initially published to TestPyPI only.

### Added
- `RubriconPipeline` — the new public, fully configurable pipeline.
- `RubriconConfig` — single Pydantic source of truth for all settings, with layered loading: defaults < YAML/dict < env vars (`RUBRICON_*`) < kwargs.
- `LLMBackend` plugin protocol with `LiteLLMBackend` and `MockBackend` built-ins, plus a registry so users can register custom backends.
- `Evaluator` plugin layer with `LLMJudgeEvaluator`, `RegexEvaluator`, `FunctionEvaluator`, and `EnsembleEvaluator`. Different evaluators can be mixed per-criterion.
- `ReattentionStrategy` plugin layer: `FocalReattention` (paper FWRL), `UniformReattention`, `SoftmaxReattention`.
- `ConvergencePolicy` plugin layer: `AllPass`, `MeanThreshold`, `NoImprovement`, `CompositePolicy`.
- Externalized Jinja2 prompt templates with user override support.
- Callback bus with `ConsoleCallback` and `JSONLCallback` built-ins.
- `BudgetTracker` for hard limits on tokens, cost, wall time, and iteration count.
- `RetryConfig` replaces hardcoded retry constants.
- `rubricon` CLI: `run`, `eval`, `config show`, `plugins`.
- Presets: `quick()`, `local_ollama()`, `production()`.
- Full PyPI metadata: classifiers, keywords, project URLs, console-script entry point, type-hint marker (`py.typed`).
- GitHub Actions release workflow with PyPI Trusted Publishing.

### Preserved
- The original `efa` package ships unchanged for research reproducibility — every existing test, experiment, and paper artifact continues to work via `from efa import EFAPipeline`.
- Backwards-compatible kwargs shim: `RubriconPipeline(model="gpt-4o", n_criteria=5, ...)` works without writing a config file.

## [0.1.0] - 2026-03-23

Initial research release as `evaluation-first-attention`.
