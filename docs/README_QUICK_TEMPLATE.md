# Research README Quick-Reference Template

Use this template as a starting point for your research paper repository README. Fill in each section with your specific content.

---

```markdown
# [PROJECT NAME]

[One-liner pitch in 10-15 words that captures the core contribution]

**Authors**: [Name(s)] | **Venue**: [NeurIPS/ICML/ICLR/ACL/EMNLP 2024] | **Year**: [2024]

[![PyPI version](badge)](link) [![License: MIT](badge)](link) [![Downloads](badge)](link)

[Optional: Center-aligned logo image, 400-600px wide]

## Quick Links
[Paper](arxiv_link) | [Docs](docs_link) | [Website](site_link) | [Discord](chat_link)

---

## The Problem

Current approaches to [task name] suffer from:

1. **Problem 1**: Explanation with concrete example
2. **Problem 2**: Why this is limiting
3. **Problem 3**: Cost/complexity issue

## The Solution

We propose [Project Name], which [core idea in 1-2 sentences].

**Key insight**: [Metaphor or analogy for the approach]

![Architecture diagram showing core approach]

### Mechanism 1: [Name]

[Explanation: what it does + why it matters + how it differs from prior work]

```
[Pseudocode or visual representation]
```

**Intuition**: [Analogy or plain-language explanation]

### Mechanism 2: [Name]

[Similar structure as Mechanism 1]

---

## Experiment Results

We evaluate on [dataset/tasks] with [N] experiments across [X] baselines + [Y] ablations.

**Key finding**: [Most impressive quantitative result] — [% improvement] over baseline.

![Results table screenshot]

### Key Findings

- **Finding 1**: Specific ablation result with implication
- **Finding 2**: Cross-model evaluation insight
- **Finding 3**: Surprising or novel discovery

### Metrics Explained

| Metric | Description | Range |
|--------|-------------|-------|
| **Metric1** | What it measures and why | [0,1] |
| **Metric2** | What it measures and why | [0,100%] |

### Baseline Comparisons

| # | Baseline | What It Tests | Key Result |
|---|----------|-------------|-----------|
| 1 | Baseline A | Component X | Result |
| 2 | Baseline B | Component Y | Result |
| 3 | Baseline C | No components | Baseline |

### Ablations

| Ablation | Removed | Impact | Why It Matters |
|----------|---------|--------|-------------|
| -Mech1 | Mechanism 1 | RAS drops 15% | Proves critical |
| -Mech2 | Mechanism 2 | RAS drops 8% | Contributes |
| -Both | Both | RAS drops 22% | Cumulative effect |

---

## Project Structure

```
project-name/
├── src/project/                  # Core implementation
│   ├── pipeline.py               # Main algorithm (Algorithm 1)
│   ├── mechanism1.py             # First mechanism
│   ├── mechanism2.py             # Second mechanism
│   └── models.py                 # Data models
├── experiments/
│   ├── prompts/                  # Benchmark sets
│   ├── results/                  # Output JSON
│   └── run_experiment.py         # Main runner
├── configs/                      # YAML config files
├── tests/                        # Unit tests
├── docs/                         # Documentation
└── paper/                        # LaTeX source
```

---

## Setup

```bash
git clone https://github.com/username/project-name.git
cd project-name
pip install -e ".[dev]"
```

### Requirements
- Python 3.9+
- PyTorch 2.0+
- See requirements.txt for full list

### API Keys (Optional)

The project works with any LiteLLM-compatible model:

```bash
# Cloud providers (pick one)
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Local (free, no API key needed)
# Just run: ollama serve
```

---

## Quick Start

```python
from project_name import MainPipeline

# Initialize pipeline
pipeline = MainPipeline(
    model="gpt-4o",                      # Generation model
    evaluator_model="claude-sonnet-4",   # Evaluation model (different for unbiased eval)
    param1=value1,                       # [Parameter explanation]
    param2=value2,                       # [Parameter explanation]
    max_iterations=3,                    # Max refinement loops
)

# Run on an example
result = pipeline.run("Your prompt here")

# Inspect results
print(result.response)              # Final output
print(result.metric1)               # Primary metric score
print(result.all_pass)              # All criteria satisfied?
print(result.n_iterations)          # Iterations used
print(result.total_tokens)          # Token consumption
```

### Expected Output

```
Response: [Generated text]
Metric1: 0.87
All Pass: True
Iterations: 2
Tokens: 3,421
```

### With Local Model (No API costs)

```python
pipeline = MainPipeline(
    model="ollama/qwen3.5:9b",
    evaluator_model="ollama/qwen3.5:9b",
    param1=value1,
    max_iterations=2,
)
```

---

## Running Experiments

```bash
# Full suite: your method + all baselines + ablations
python experiments/run_experiment.py --config configs/full_suite.yaml

# Single method on subset of prompts
python experiments/run_experiment.py --method main --max-prompts 5

# Cross-model evaluation (different generator and evaluator)
python experiments/run_experiment.py --config configs/cross_model.yaml
```

### Configuration Files

See `configs/` directory for example YAML configurations. Each config specifies:
- Models to use (generator + evaluator)
- Hyperparameters
- Prompts to test
- Output paths

---

## Hyperparameters

All hyperparameters are configurable. Defaults are optimized for general use.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `param1` | value | What this controls and range |
| `param2` | value | When to increase/decrease |
| `max_iterations` | 3 | Maximum refinement loops (higher = slower but better quality) |
| `alpha` | 2.0 | Strength of [mechanism] adjustment |

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_models.py -v

# Run with coverage
python -m pytest tests/ --cov=src/
```

### Expected Output

```
tests/test_models.py::test_param1_valid        PASSED
tests/test_models.py::test_param2_valid        PASSED
tests/test_pipeline.py::test_end_to_end        PASSED

11 passed in 0.45s
```

---

## Reproducibility

To reproduce paper results exactly:

1. Use config: `configs/paper_results.yaml`
2. Set random seed: `PYTHONHASHSEED=42`
3. Use cross-model evaluation (never same model for generation+evaluation)
4. Run full suite: `python experiments/run_experiment.py --config configs/paper_results.yaml`

**Note**: Results may vary slightly (±1-2%) due to:
- LLM sampling randomness
- Version differences in model APIs
- Hardware differences in timing

See `experiments/results/` for pre-computed logs if you cannot re-run expensive experiments.

---

## Citation

```bibtex
@article{lastname2024projectname,
  title={Project Title: Subtitle Explaining Contribution},
  author={Author, First and Author, Second},
  journal={Venue Name},
  year={2024},
  pages={xx--xx},
  doi={doi_if_available}
}
```

**Also cite**: [Key referenced papers with brief descriptions]

---

## Related Work

How this work compares to closest related methods:

| Work | Approach | Training Required | Key Difference |
|------|----------|------------------|---------------|
| [Citation A](link) | Baseline approach | Yes | We add mechanism X |
| [Citation B](link) | Similar approach | No | We use failure weighting |
| **This work** | **Our approach** | **No** | **All three components** |

---

## Contributing

We welcome community contributions! Please:

1. Fork the repository
2. Create a branch: `git checkout -b feature/your-feature`
3. Make changes and add tests
4. Run tests: `pytest tests/ -v`
5. Submit a pull request with description of changes

### Code Style
- Black for formatting
- Mypy for type checking
- Docstrings: Google style

### Reporting Bugs
Open an issue with:
- Clear title
- Minimal reproducible example
- Python version and OS
- Full error traceback

---

## Troubleshooting

**Q: I get "API key not found" error**
A: Set environment variables (see API Keys section above)

**Q: Results are different from paper**
A: Likely due to model version differences. Try using pre-computed logs in `experiments/results/`

**Q: Running out of memory**
A: Reduce `batch_size` in config, or use smaller model (e.g., `gpt-3.5-turbo`)

**Q: Why is the evaluator model different from the generator?**
A: Cross-model evaluation prevents self-preference bias and improves result validity

For more troubleshooting, see [docs/](docs/) or open a GitHub issue.

---

## License

MIT License - [Author Name], 2024

See LICENSE file for full text.

---

## Contact & Acknowledgments

- **Author**: [Name] ([email](mailto:email))
- **Questions**: Open a GitHub issue or email above
- **Acknowledgments**: This work builds on [Citation], [Citation], and [Citation]

---

## Changelog

### v1.0 (2024-03-XX)
- Initial release
- Core pipeline implementation
- [N] baselines + ablations
- Full test coverage

### v1.1 (2024-04-XX) [planned]
- Fine-tuning support
- Multi-turn evaluation
- JAX backend option
```

---

## How to Use This Template

1. **Copy the template** into your README.md
2. **Replace all bracketed sections** `[like this]` with your specific details
3. **Fill in metrics** based on your actual results
4. **Add images** for architecture and results
5. **Keep the structure** — it's proven across top research repos
6. **Run through checklist** before publishing:

- [ ] One-liner is clear and non-obvious
- [ ] Problem section is specific to your work (not generic)
- [ ] Architecture diagram exists and is labeled
- [ ] Quick Start code is copy-paste ready and runs
- [ ] All links work (test with curl or browser)
- [ ] Key results are in first 2 pages (not buried)
- [ ] Citation format matches your venue (check ACL, NeurIPS, etc.)
- [ ] Baseline/ablation tables exist and show impact
- [ ] No typos or inconsistent terminology
- [ ] Cross-model evaluation is noted (if applicable)

---

## Real-World Examples

To see this template in action, refer to:
- **Self-Refine** (clear problem → solution → mechanisms)
- **Reflexion** (excellent ablation section)
- **Tree of Thoughts** (great Quick Start code)
- **vLLM** (strong results presentation)
- **DSPy** (good citations + roadmap)

Full analysis document: `README_TEMPLATE_ANALYSIS.md`
