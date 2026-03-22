# Evaluation-First Attention (EFA)

**Specification-Driven Generation via Dynamic Rubric Conditioning and Failure-Weighted Reattention**

**Author**: Karthick Raja M (karthickrajam18@gmail.com)

## Overview

EFA inverts the traditional generate-then-evaluate paradigm by generating evaluation criteria *before* generation and using them as structured conditioning targets throughout the generation process.

### Novel Mechanisms

1. **Criteria-Masked Progressive Generation (CMPG)**: Progressively unmasks quality dimensions during generation — analogous to causal token masking but over evaluation criteria.
2. **Failure-Weighted Reattention Loop (FWRL)**: Maps per-criterion evaluation scores to emphasis adjustments, amplifying focus on failing dimensions in subsequent passes.

## Project Structure

```
evaluation-first-attention/
├── src/efa/                    # Core EFA implementation
│   ├── criteria_generator.py   # Component 1: Dynamic criteria generation
│   ├── progressive_generator.py # Component 2: CMPG
│   ├── evaluator.py            # Component 3: Per-criterion evaluation
│   ├── reattention.py          # Component 3: FWRL weight updates
│   ├── pipeline.py             # Full EFA pipeline (Algorithm 1)
│   ├── baselines.py            # All 7 baseline implementations
│   ├── ablations.py            # 4 ablation conditions
│   └── llm_client.py           # LiteLLM abstraction layer
├── experiments/
│   ├── prompts/                # Benchmark prompt sets
│   ├── results/                # Experiment outputs
│   └── run_experiment.py       # Main experiment runner
├── configs/                    # Hyperparameter configs
├── scripts/                    # Utility scripts
├── tests/                      # Unit + integration tests
└── paper/                      # LaTeX source
```

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env  # Add your API keys
```

## Quick Start

```python
from efa import EFAPipeline

pipeline = EFAPipeline(
    model="gpt-4o",
    evaluator_model="claude-sonnet-4-20250514",  # Cross-model evaluation
    n_criteria=5,
    threshold=0.6,
    max_iterations=3,
    alpha=2.0,
)

result = pipeline.run("Explain quantum entanglement to a high school student")
print(result.response)
print(result.scores)       # Per-criterion scores
print(result.iterations)   # How many loops
print(result.token_cost)   # Total tokens used
```

## Running Experiments

```bash
# Full experiment suite
python experiments/run_experiment.py --config configs/default.yaml

# Single method
python experiments/run_experiment.py --method efa --prompts mt-bench

# Ablation study
python experiments/run_experiment.py --method efa-no-cmpg --prompts alpaca-eval
```

## License

MIT License - Karthick Raja M, 2026
