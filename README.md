# Rubricon

**Specification-first generation for LLMs. Cross the rubricon — produce evaluation criteria *before* generation and use them as conditioning targets with failure-weighted reattention.**

[![PyPI](https://img.shields.io/pypi/v/rubricon.svg)](https://pypi.org/project/rubricon/)
[![Python](https://img.shields.io/pypi/pyversions/rubricon.svg)](https://pypi.org/project/rubricon/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

```bash
pip install rubricon
```

```python
from rubricon import RubriconPipeline, RubriconConfig

cfg = RubriconConfig.from_dict({
    "generator": {"model": "gpt-4o"},
    "evaluator": {"model": "claude-sonnet-4-20250514"},
    "criteria": {"n": 5},
    "convergence": {"threshold": 0.6},
    "iteration": {"max_iterations": 3},
})
result = RubriconPipeline(cfg).run("Explain quantum entanglement to a high school student.")
print(result.response, result.rubric_adherence_score, result.all_pass)
```

## Highly configurable by design

| Layer | Plugin protocol | Built-ins | Override via |
|-------|----------------|-----------|--------------|
| **Backends** | `LLMBackend` | `litellm`, `mock` | `backend_registry.register("vllm")` |
| **Evaluators** | `Evaluator` | `llm_judge`, `regex`, `function`, `ensemble` | per-criterion mix in config |
| **Reattention** | `ReattentionStrategy` | `focal` (FWRL), `uniform`, `softmax` | `reattention.strategy` |
| **Convergence** | `ConvergencePolicy` | `all_pass`, `mean_threshold`, `no_improvement`, `composite` | `convergence.policy` |
| **Templates** | Jinja2 | bundled defaults | `templates.*` paths in config |
| **Callbacks** | `PipelineCallback` | `console`, `jsonl` | `callbacks: [{type: ...}]` |
| **Budget** | hard limits | tokens, cost, wall, iters | `budget: {...}` |
| **Retry** | `RetryConfig` | constant/linear/exponential | `retry: {...}` |

Every knob lives on a single Pydantic `RubriconConfig`. Layered loading: defaults < YAML < env (`RUBRICON_*`) < kwargs.

```bash
rubricon run "Explain entropy" --config configs/prod.yaml
rubricon eval --prompts mtbench.json --config configs/prod.yaml --output results.jsonl
rubricon plugins
rubricon config show --config configs/prod.yaml
```

The original [`efa`](src/efa) research package (paper code, baselines, ablations) ships in the same wheel for reproducibility — `from efa import EFAPipeline` keeps working.

---

# Evaluation-First Attention (EFA) — research

**What if LLMs knew what "good" looks like before they started writing?**

EFA inverts the generate-then-evaluate paradigm by producing evaluation criteria *before* generation and using them as structured conditioning targets with failure-proportional reweighting — like TDD for text generation.

**Author**: [Karthick Raja M](mailto:karthickrajam18@gmail.com) | **Affiliation**: Independent Researcher, Chennai, India | **Date**: March 2026

[Paper (PDF)](paper/EFA_Paper_Final.pdf) | [LaTeX Source](paper/EFA_Paper_Final.tex)

---

## News

- **[2026-03-30]** Full MT-Bench results: 960 runs (12 methods × 80 prompts) with cross-model evaluation (MiniMax-M2.5 gen + Qwen-3.5-9B eval). EFA achieves **96.2% APR**, +25pp over single-pass. Paper updated with results, figures, honest FWRL analysis.
- **[2026-03-29]** Best-of-N baseline completed (80/80 prompts). All 12 methods now have full MT-Bench coverage.
- **[2026-03-23]** Initial release: full pipeline, 7 baselines, 4 ablations, cross-model evaluation support, 11 unit tests.

---

## The Problem

Current LLM generation pipelines follow a **generate-then-evaluate** pattern. This has three fundamental limitations:

1. **Evaluation is disconnected from generation.** The model has no awareness of quality dimensions during generation. Rubric-based reward models ([CARMO](https://arxiv.org/abs/2310.01798), [OpenRubrics](https://arxiv.org/abs/2510.07743)) generate criteria but use them *only* for post-hoc scoring — never as generation targets.

2. **Refinement feedback is holistic, not dimensional.** Self-Refine ([Madaan et al., 2023](https://arxiv.org/abs/2303.17651)) produces feedback like "the response lacks specificity," requiring the model to self-diagnose which dimensions failed. Diagnosis — not repair — is the bottleneck ([RefineBench, 2025](https://arxiv.org/abs/2411.00548)).

3. **All quality dimensions receive equal emphasis.** Whether a response nails relevance but fails on accuracy, refinement passes treat all dimensions uniformly. No system allocates more generation budget to failing dimensions.

## The Solution

EFA operates in three phases:

1. **Criteria Generation**: A dedicated LLM call analyzes the prompt and produces query-specific evaluation criteria with measurable rubrics.
2. **Criteria-Masked Progressive Generation (CMPG)**: The generator sees criteria one-at-a-time via progressive unmasking — like causal masking over quality dimensions.
3. **Failure-Weighted Reattention (FWRL)**: Per-criterion scores map to emphasis weight adjustments, amplifying focus on failing dimensions in subsequent passes — like focal loss at inference time.

![EFA Architecture](docs/architecture.png)

---

## How EFA Differs from Prior Work

| Method | Criteria-Aware Generation | Per-Criterion Scoring | Failure-Proportional Reweighting | Progressive Masking |
|--------|:------------------------:|:--------------------:|:-------------------------------:|:-------------------:|
| Single-pass | - | - | - | - |
| Self-Refine ([Madaan et al., 2023](https://arxiv.org/abs/2303.17651)) | - | - | - | - |
| Reflexion ([Shinn et al., 2023](https://arxiv.org/abs/2303.11366)) | - | - | - | - |
| CARMO ([Zhang et al., 2025](https://aclanthology.org/2025.findings-acl.114/)) | - | Yes | - | - |
| ReFeed ([2025](https://arxiv.org/abs/2503.21332)) | - | Yes (3 dims) | - | - |
| RSD ([Xu et al., 2025](https://arxiv.org/abs/2501.19324)) | Process reward | Step-level | - | - |
| **EFA (ours)** | **Yes** | **Yes** | **Yes** | **Yes** |

EFA is the first system that combines all four: dynamic rubric generation used as generation-time conditioning with progressive unmasking and failure-proportional reweighting.

---

## Novel Mechanisms

### 1. Criteria-Masked Progressive Generation (CMPG)

Instead of showing all criteria at once, CMPG progressively unmasks them — ensuring foundational criteria are satisfied before the model optimizes for secondary dimensions:

```
Sub-step 1: Generate with {c₁} only          → draft d₁    (e.g., factual accuracy)
Sub-step 2: Refine with {c₁, c₂}             → draft d₂    (+ completeness)
Sub-step 3: Refine with {c₁, c₂, c₃}         → draft d₃    (+ clarity)
...
Sub-step n: Refine with {c₁, c₂, ..., cₙ}    → response R  (all criteria)
```

**Intuition**: Like curriculum learning at inference time — satisfy fundamentals before polish.

### 2. Failure-Weighted Reattention Loop (FWRL)

Failed criteria receive mathematically boosted emphasis weights proportional to how badly they failed:

```
w_i^(k+1) = w_i^(k) * (1 + α * max(0, τ - s_i^(k)))
```

- **Passed criteria** (`s ≥ τ`): weights unchanged — don't fix what isn't broken
- **Failed criteria** (`s < τ`): weight boost proportional to failure gap
- **Checkpoint mechanism**: locks previously-passing criteria to prevent regression

**Intuition**: Like focal loss for inference — focus compute budget where it's needed most.

---

## Experiment Results

960 runs completed: 12 methods × 80 MT-Bench prompts. Cross-model evaluation: MiniMax-M2.5 (generator) + Qwen-3.5-9B via Ollama (evaluator) — eliminates self-preference bias.

![APR Comparison](paper/figures/apr_comparison.png)

### Main Results

| Method | RAS ↑ | APR (%) ↑ | TTC ↓ |
|--------|-------|-----------|-------|
| Single-pass | 0.881 | 71.2 | 9,210 |
| Rubric-then-Score | 0.863 | 72.5 | 9,469 |
| All-Criteria-at-Once | 0.925 | 90.0 | 13,408 |
| Uniform Reattention | 0.935 | 90.0 | 17,814 |
| Best-of-5 | 0.957 | 91.2 | 21,999 |
| Self-Refine | 0.953 | 92.5 | 13,652 |
| FusioN | 0.956 | 92.5 | 15,449 |
| **EFA (Full)** | **0.962** | **96.2** | **16,449** |

### Key Findings

1. **EFA beats all 7 baselines on APR**: 96.2% vs best baseline 92.5% (+3.7pp). +25.0pp over single-pass generation.

2. **Iteration is the biggest driver** (−12.4pp): Removing iterative refinement drops APR from 96.2% to 83.8%. Multi-pass generation with criterion-level feedback is essential.

3. **Dynamic criteria matter** (−7.4pp): Replacing per-query criteria with a fixed universal set drops APR from 96.2% to 88.8%.

4. **CMPG provides measurable gains** (−3.7pp): Progressive masking over quality dimensions outperforms presenting all criteria simultaneously.

5. **FWRL shows no measurable contribution** (0.0pp): Removing failure-weighted reattention yields identical APR (96.2%) and slightly higher RAS (0.967). We attribute this to a ceiling effect with a strong generator — the model fixes failing criteria even with uniform weights. This is honestly reported in the paper.

6. **EFA is more token-efficient than brute-force**: 75% of Best-of-5's token cost with +5.0pp higher APR.

![Ablation Study](paper/figures/ablation_waterfall.png)
![Cost-Quality Tradeoff](paper/figures/cost_quality_scatter.png)

### Metrics

| Metric | Full Name | What It Measures | Range |
|--------|-----------|------------------|-------|
| **RAS** | Rubric Adherence Score | Mean per-criterion score across all criteria | [0, 1] |
| **APR** | All-Pass Rate | % of prompts where every criterion meets threshold τ | [0%, 100%] |
| **ITC** | Iterations to Convergence | Mean iterations before all criteria pass or K_max | [1, K_max] |
| **TTC** | Total Token Cost | Total tokens consumed across the full pipeline | Tokens |

---

## Quick Start

### Installation

```bash
git clone https://github.com/karthyick/evaluation-first-attention.git
cd evaluation-first-attention
pip install -e ".[dev]"
```

### API Keys

EFA works with any [LiteLLM](https://github.com/BerriAI/litellm)-compatible model:

```bash
# Cloud APIs (pick one or more)
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GROQ_API_KEY="gsk_..."

# Local inference (Ollama — free, no API key needed)
# ollama serve && ollama pull qwen3.5:9b
```

### Basic Usage

```python
from efa import EFAPipeline

pipeline = EFAPipeline(
    model="gpt-4o",                              # Generator
    evaluator_model="claude-sonnet-4-20250514",   # Cross-model evaluator
    n_criteria=5,
    threshold=0.6,
    max_iterations=3,
    alpha=2.0,
)

result = pipeline.run("Explain quantum entanglement to a high school student")

print(result.response)                    # Final response
print(result.rubric_adherence_score)      # RAS
print(result.all_pass)                    # APR (bool)
print(result.n_iterations)               # ITC
print(result.total_tokens)               # TTC
print([c.name for c in result.criteria]) # Criterion names
print(result.final_scores)              # Per-criterion scores [0,1]
```

### Local Mode (Ollama — zero cost)

```python
pipeline = EFAPipeline(
    model="ollama/qwen3.5:9b",
    evaluator_model="ollama/qwen3.5:9b",
    n_criteria=3,
    threshold=0.6,
    max_iterations=2,
)
```

---

## Running Experiments

```bash
# Full suite: EFA + 6 baselines + 4 ablations
python experiments/run_experiment.py --config configs/ollama_local.yaml

# Single method
python experiments/run_experiment.py --method efa --prompts sample --max-prompts 10

# Cross-model evaluation
python experiments/run_experiment.py --config configs/groq_gemini.yaml
```

### Baselines (7)

| # | Baseline | What It Isolates |
|---|----------|------------------|
| 1 | **Single-pass** | No criteria, no refinement — pure baseline |
| 2 | **Self-Refine** ([Madaan et al., 2023](https://arxiv.org/abs/2303.17651)) | Holistic feedback loop without criteria structure |
| 3 | **Rubric-then-Score** | Criteria used for eval only, not generation conditioning |
| 4 | **All-Criteria-at-Once** | No progressive masking — tests CMPG's value |
| 5 | **Uniform Reattention** | No failure weighting — tests FWRL's value |
| 6 | **Best-of-N** | Independent sampling — cheapest scaling alternative |
| 7 | **FusioN** ([Agarwal et al., 2025](https://arxiv.org/abs/2510.00931)) | Multi-candidate synthesis — generate N, synthesize one superior response |

### Ablations (4)

| Ablation | Component Removed | Expected Impact |
|----------|-------------------|-----------------|
| **-DynCriteria** | Dynamic per-query criteria → fixed universal set | Tests value of query-specific rubrics |
| **-CMPG** | Progressive masking → all criteria shown at once | Tests curriculum-style unmasking |
| **-FWRL** | Failure weighting → uniform weights on all criteria | Tests targeted vs uniform reattention |
| **-Iteration** | Refinement loop → single pass with criteria | Tests iterative improvement value |

---

## Project Structure

```
evaluation-first-attention/
├── src/efa/                      # Core EFA implementation
│   ├── pipeline.py               # Full pipeline — Algorithm 1 from paper
│   ├── criteria_generator.py     # Component 1: Dynamic criteria generation
│   ├── progressive_generator.py  # Component 2: CMPG progressive masking
│   ├── evaluator.py              # Component 3a: Per-criterion evaluation
│   ├── reattention.py            # Component 3b: FWRL weight updates + checkpointing
│   ├── baselines.py              # All 7 baseline implementations
│   ├── models.py                 # Data models (Criterion, EvaluationResult, etc.)
│   └── llm_client.py             # LiteLLM abstraction with retry + JSON repair
├── experiments/
│   ├── prompts/                  # Benchmark prompt sets (sample, MT-Bench, etc.)
│   ├── results/                  # Experiment outputs (JSON)
│   └── run_experiment.py         # Experiment runner with rich table output
├── configs/                      # Hyperparameter configs (YAML)
│   ├── default.yaml              # GPT-4o + Claude cross-model
│   ├── ollama_local.yaml         # Local Ollama (zero cost)
│   └── groq_gemini.yaml         # Groq + Gemini cross-model
├── scripts/                      # Visualization and analysis scripts
├── tests/                        # Unit tests (11 passing)
├── docs/                         # Diagrams, screenshots, analysis guides
└── paper/                        # LaTeX source + compiled PDF
```

## Hyperparameters

| Parameter | Symbol | Default | Description |
|-----------|--------|---------|-------------|
| `n_criteria` | n | 5 | Number of evaluation criteria per query |
| `threshold` | τ | 0.6 | Passing threshold (rubric score >= 3/5) |
| `max_iterations` | K_max | 3 | Maximum refinement loops |
| `alpha` | α | 2.0 | Reattention strength (higher = more aggressive reweighting) |
| `epsilon` | ε | 0.1 | Regression tolerance for checkpoint locking |

See `configs/alpha_sensitivity.yaml` for alpha sweep configuration (α ∈ {1.0, 2.0, 5.0}).

## Tests

```bash
python -m pytest tests/ -v
```

11 tests covering: priority label mapping, evaluation scoring, FWRL weight updates, checkpoint locking, convergence detection.

## Reproducibility

- All experiment results are saved as JSON in `experiments/results/` with per-prompt, per-method scores.
- Configs capture exact hyperparameters used for each experiment run.
- Local experiments (Ollama) are fully reproducible at zero cost.
- API-based experiments may produce different results due to model versioning and temperature sampling.
- Pre-computed results from our initial run are included in the repo.

---

## Citation

```bibtex
@article{mohan2026efa,
  title={Evaluation-First Generation: Specification-Driven LLM Output Quality
         via Dynamic Rubric Conditioning and Iterative Criteria Refinement},
  author={Mohan, Karthick Raja},
  year={2026},
  month={March}
}
```

## License

MIT License - Karthick Raja M, 2026
