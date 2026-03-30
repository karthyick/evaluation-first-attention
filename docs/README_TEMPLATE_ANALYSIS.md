# Research Paper Repository README Template Analysis

**Research Methodology**: Analyzed 8 premier AI/ML research repositories from top-tier venues (NeurIPS, ICML, ICLR, ACL, EMNLP) to extract standard README patterns and best practices.

**Repositories Analyzed**:
1. **Self-Refine** (Madaan et al., 2023) — ICLR
2. **Reflexion** (Shinn et al., 2023) — NeurIPS
3. **Tree of Thoughts** (Yao et al., 2023) — NeurIPS
4. **LLM-Blender** (Jiang et al., 2023) — ACL
5. **G-Eval** (Liu et al., 2023) — EMNLP
6. **vLLM** (UC Berkeley, 2023) — SOSP
7. **SGLang** (2024) — NeurIPS
8. **DSPy** (Stanford, 2023) — ICLR

---

## Section 1: Overall Structure & Flow

### Universal Header Pattern
All research repos start with:
```
# [Project Name]
[One-line pitch / tagline]
[Authors (optional)]
---
```

**Key insight**: The one-line pitch is **crucial** — it's the elevator pitch that makes researchers understand the contribution in 10 seconds.

Examples:
- **Self-Refine**: "LLMs can generate feedback on their work, use it to improve the output, and repeat this process iteratively."
- **Reflexion**: "Language Agents with Verbal Reinforcement Learning"
- **Tree of Thoughts**: "Deliberate Problem Solving with Large Language Models"
- **vLLM**: "Easy, fast, and cheap LLM serving for everyone."
- **DSPy**: "The framework for programming—not prompting—language models"

---

## Section 2: Detailed Section Breakdown

### A. Hero Section (Top-to-Middle)

**Elements (in order)**:

1. **Logo/Badge Row** (Optional but common)
   - GitHub stars badge
   - PyPI version badge
   - License badge
   - Downloads badge
   - Build status badge

   Examples:
   - vLLM: Shows PyPI availability, documentation links
   - SGLang: PyPI version, download metrics, license status, issue resolution
   - Tree of Thoughts: PyPI, Python 3.7+, MIT license, Zenodo DOI
   - DSPy: PyPI downloads badge

2. **Centered Project Logo** (If available)
   - Typical size: 400-600px wide
   - Positioned before main description
   - Often includes tagline overlay

3. **Navigation Quick Links** (In research-heavy repos)
   - Paper link (ArXiv or conference proceedings)
   - Documentation
   - Blog post or website
   - GitHub discussion / Discord / Slack
   - Quick start guide

   Format: Usually `[Paper](link) | [Docs](link) | [Blog](link)`

4. **Brief Problem Statement** (100-200 words)
   - What problem does the paper solve?
   - Why is it important?
   - What makes this different from prior work?

   Example from Self-Refine:
   > "LLMs generate feedback on their work, use it to improve, and repeat iteratively. No supervised training, additional training, or RL needed—just a single LLM as generator, refiner, and feedback provider."

5. **Key Results Snapshot** (Quantitative)
   - Single most impressive metric
   - Keep it to 1-3 bullet points
   - Use clear comparisons to baselines

   Examples:
   - **Self-Refine**: "~20% improvement on average across 7 diverse tasks"
   - **Reflexion**: "91% pass@1 on HumanEval (vs 80% GPT-4)"
   - **Tree of Thoughts**: "74% on Game of 24 (vs 4% GPT-4 CoT)"
   - **vLLM**: "24x higher throughput than HuggingFace Transformers"
   - **SGLang**: "6.4× higher throughput on multi-agent tasks"

### B. Core Problem Section

**Title**: "The Problem" or "Motivation" or "Overview"

**Content pattern**:
- Start with current state of the field
- Explain limitations of existing approaches
- Use numbered bullet points for clarity
- Keep to 3-4 core pain points
- Optional: ASCII diagram or small visual

Example from your current README:
```markdown
## The Problem

Current LLM generation pipelines treat evaluation as a post-hoc step:

1. Models generate **without knowing** what quality dimensions they must satisfy
2. Refinement feedback is **holistic** ("lacks specificity") rather than per-dimension
3. All quality dimensions receive **equal emphasis**, regardless of which are failing
```

### C. Solution Section

**Title**: "The Solution" or "Our Approach" or "Key Contribution"

**Content pattern**:
- 1-2 sentence high-level summary
- Metaphor or analogy for quick understanding
- Visual diagram of core approach
- 2-3 sub-mechanisms with brief explanations
- Pseudocode or algorithm box for clarity

Example from Self-Refine:
```markdown
## Solution

LLMs can generate feedback on their work, use it to improve the output, and repeat iteratively.

[Framework diagram showing: Init Prompt → Generate → Feedback → Refine → ...loop]
```

Your EFA README does this excellently:
```markdown
## The Solution

EFA inverts this paradigm: **generate evaluation criteria before generation**,
then use them as structured conditioning targets with failure-proportional reweighting.

Think of it as **TDD for text generation** — write the tests (criteria) before
the code (response), then build to pass them.
```

### D. Technical Mechanisms / Algorithms

**Title**: "Novel Mechanisms" or "Core Algorithm" or "Technical Details"

**Pattern**:
- Each mechanism gets its own subsection with H3 or H4
- Start with conceptual explanation
- Include mathematical notation if relevant (with explanation)
- Show visual representation (diagram, flowchart, or code)
- Give intuitive analogy
- Explain why it matters

Example from your README:
```markdown
### 1. Criteria-Masked Progressive Generation (CMPG)

Instead of showing all criteria at once, CMPG progressively unmasks them...

[Visual representation]

Sub-step 1: Generate with {c₁} only          → draft d₁
Sub-step 2: Refine with {c₁, c₂}             → draft d₂
...

This ensures foundational criteria (e.g., factual accuracy) are satisfied
before optimizing for secondary ones (e.g., style).
```

---

## Section 3: Experimental Results & Metrics

### A. Results Overview Section

**Title**: "Experiment Results" or "Evaluation" or "Performance"

**Content pattern**:

1. **High-level summary** (2-3 sentences)
   - What was tested
   - How many experiments
   - Scale of evaluation

   Example from your README:
   > "55/55 runs completed across 11 methods (EFA + 6 baselines + 4 ablations) on 5 diverse prompts."

2. **Key findings** (Bullet format, 3-5 points)
   - Most important discoveries
   - Surprising results or ablation insights
   - Cross-model or edge case findings

   Example from Self-Refine:
   > "~20% improvement on average across 7 diverse tasks using state-of-the-art LLMs (GPT-3.5, ChatGPT, GPT-4)"

3. **Results visualization**
   - Primary: Screenshot of results table
   - Secondary: Line graph of iterations-to-success
   - Tertiary: Bar chart comparing baselines

   All should be placed as **images** (not ASCII tables) for visual impact

4. **Metrics explanation table**
   - Define each metric you use
   - 3-5 metrics maximum
   - Include units and range

   Example from your README:
   ```markdown
   | Metric | Description |
   |--------|-------------|
   | **RAS** | Rubric Adherence Score — mean per-criterion score [0, 1] |
   | **APR** | All-Pass Rate — % of prompts where all criteria meet threshold |
   | **ITC** | Iterations to Convergence — mean iterations before all pass |
   | **TTC** | Total Token Cost — tokens consumed across full pipeline |
   ```

### B. Baseline Comparison

**Pattern**:
- Create table of baselines with brief descriptions
- Include numbering for easy reference
- Mark which baselines are your own implementations vs prior work
- Explain what each baseline tests

Example from your README:
```markdown
### Baselines (7)

| # | Baseline | What it tests |
|---|----------|---------------|
| 1 | Single-pass | No criteria, no refinement |
| 2 | Self-Refine | Holistic feedback loop (Madaan et al., 2023) |
| 3 | Rubric-then-Score | Criteria for eval only, not generation |
...
```

### C. Ablation Studies

**Pattern**:
- Explain why ablations matter
- One row per ablated component
- Show impact on primary metric
- Frame as "What happens if we remove X"

Example from your README:
```markdown
### Ablations (4)

| Ablation | What is removed |
|----------|-----------------|
| -DynCriteria | Dynamic criteria → fixed universal set |
| -CMPG | Progressive masking → all criteria at once |
| -FWRL | Failure weighting → uniform weights |
| -Iteration | Refinement loop → single pass |
```

---

## Section 4: Getting Started & Installation

### A. Setup Section

**Title**: "Setup" or "Installation" or "Getting Started"

**Pattern**:
1. **Git clone** with optional branch note
2. **Python version requirement** (if any)
3. **pip install command** (prefer `pip install -e ".[dev]"` for research repos)
4. **Optional**: Virtual environment setup
5. **Optional**: Docker setup

Standard example:
```bash
git clone https://github.com/user/project.git
cd project
pip install -e ".[dev]"
```

### B. API Keys / Credentials

**Pattern** (if applicable):
- List all supported providers
- Show environment variable names
- Provide example exports
- If local-only option exists, explain it prominently

Example from your README:
```bash
# Cloud APIs
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Local (Ollama — free, no key needed)
# Just have Ollama running: ollama serve
```

### C. Quick Start Code

**Title**: "Quick Start" or "Usage"

**Pattern**:
1. **Import statement**
2. **Minimal working example** (10-20 lines of code)
3. **Explanation of key parameters**
4. **Example output** (what the user should see)
5. **Link to full documentation**

Example from your README:
```python
from efa import EFAPipeline

pipeline = EFAPipeline(
    model="gpt-4o",
    evaluator_model="claude-sonnet-4-20250514",
    n_criteria=5,
    threshold=0.6,
    max_iterations=3,
    alpha=2.0,
)

result = pipeline.run("Explain quantum entanglement to a high school student")
print(result.response)                    # Final generated response
print(result.rubric_adherence_score)      # RAS: mean criterion score
```

### D. Running Experiments

**Pattern**:
- Provide full end-to-end command
- Show single-method variant
- Show config file variant
- Explain major flags

Example from your README:
```bash
# Full suite: EFA + 6 baselines + 4 ablations
python experiments/run_experiment.py --config configs/ollama_local.yaml

# Single method on specific prompts
python experiments/run_experiment.py --method efa --prompts sample --max-prompts 10
```

---

## Section 5: Project Organization

### A. Directory Structure

**Title**: "Project Structure" or "Repository Layout"

**Pattern**:
- Tree view with brief descriptions
- Key files/directories only (not exhaustive)
- Highlight main module paths
- Note test, config, and docs locations

Example from your README:
```
evaluation-first-attention/
├── src/efa/                      # Core implementation
│   ├── pipeline.py               # Full EFA pipeline (Algorithm 1)
│   ├── criteria_generator.py     # Dynamic criteria generation
│   ├── progressive_generator.py  # CMPG progressive masking
│   ...
├── experiments/
│   ├── prompts/                  # Benchmark prompt sets
│   ├── results/                  # Experiment outputs (JSON)
│   └── run_experiment.py         # Main experiment runner
├── configs/                      # Hyperparameter configs (YAML)
└── paper/                        # LaTeX source + PDF
```

### B. Hyperparameters / Configuration

**Title**: "Hyperparameters" or "Configuration"

**Pattern**:
- Table with: Parameter | Default | Description
- Explain effect of each parameter
- Provide guidance on tuning
- Note interdependencies

Example from your README:
```markdown
| Parameter | Default | Description |
|-----------|---------|-------------|
| `n_criteria` | 5 | Number of criteria per query |
| `threshold` (τ) | 0.6 | Passing threshold (rubric score >= 3/5) |
| `max_iterations` (K_max) | 3 | Maximum refinement loops |
| `alpha` (α) | 2.0 | Reattention strength |
```

---

## Section 6: Testing & Validation

### A. Tests Section

**Title**: "Tests" or "Testing"

**Pattern**:
1. **Command to run all tests**
   ```bash
   python -m pytest tests/ -v
   ```
2. **Test output** showing all passing tests
3. **Optional**: Link to CI/CD pipeline
4. **Optional**: Coverage percentage

Example from your README:
```bash
python -m pytest tests/ -v

tests/test_models.py::test_criterion_priority_label_critical     PASSED
tests/test_models.py::test_criterion_priority_label_standard     PASSED
...
11 passed
```

### B. Reproduction

**Pattern** (if applicable):
- Explain how to reproduce paper results exactly
- Note any random seeds
- Explain variance across runs
- Provide pre-computed logs if results are expensive

Example from Reflexion README:
> "It may not be feasible for individual developers to rerun the results as GPT-4 has limited access and significant API charges. Pre-computed logs are provided across all three domains for reproducibility."

---

## Section 7: Citation & Attribution

### A. Citation Section

**Title**: "Citation" or "How to Cite"

**Pattern**:
```bibtex
@article{lastname2024paper,
  title={Full Paper Title},
  author={Author, A and Author, B},
  journal={Conference/Journal Name},
  year={2024},
  pages={pages},
  doi={doi_if_available}
}
```

**Additional citation formats**:
- Often also provide Chicago style
- Provide APA if interdisciplinary
- Provide plain text version for copy-paste

Example from your README:
```bibtex
@article{mohan2026efa,
  title={Evaluation-First Attention: Specification-Driven Generation via Dynamic Rubric Conditioning and Failure-Weighted Reattention},
  author={Mohan, Karthick Raja},
  year={2026},
  month={March}
}
```

### B. License Section

**Title**: "License"

**Pattern**:
- State license clearly (MIT, Apache 2.0, CC-BY, etc.)
- Include copyright holder
- Link to full license text if not included

Example:
```markdown
## License

MIT License - Karthick Raja M, 2026
```

### C. Contact / Communication

**Pattern** (varies by repo):
- GitHub Issues for bug reports
- Email for sensitive questions
- Discord/Slack for community chat
- Twitter/LinkedIn for announcements

Example from vLLM:
> "Contact methods: GitHub Issues, forums, Slack, security advisories, collaboration@vllm.ai"

---

## Section 8: Advanced Sections (Optional, High-Impact Repos)

### A. Comparisons to Related Work

**Pattern**:
- Table comparing this work to closest prior work
- Dimensions: Performance, ease of use, training required, etc.
- Use checkmarks/crosses or Yes/No
- Cite related papers with links

Example pattern:
| Feature | Self-Refine | Reflexion | EFA | Notes |
|---------|------------|-----------|-----|-------|
| Requires training | ✗ | ✗ | ✗ | All inference-only |
| Cross-model evaluation | ✗ | ✗ | ✓ | Helps avoid self-preference bias |

### B. Architecture / Algorithm Diagram

**Pattern**:
- Place large visual diagram
- Label all key components
- Show data flow with arrows
- Include example or annotated walkthrough

### C. Roadmap

**Pattern**:
- Bullet list of planned features
- Mark completed items ✓
- Estimate timelines if reasonable
- Invite community contributions

Example:
```markdown
## Roadmap

- [x] Core pipeline implementation
- [x] Self-Refine baseline
- [ ] Fine-tuning support
- [ ] Multi-turn conversation experiments
```

### D. Troubleshooting / FAQ

**Pattern**:
- Common errors and solutions
- Installation issues
- API key problems
- Performance tuning

### E. Contributing / Development

**Pattern**:
- How to report bugs
- How to suggest features
- Development setup (different from usage setup)
- PR guidelines
- Code style guidelines

---

## Section 9: Visual & Formatting Best Practices

### A. Badges
**Industry standard badges** (top-right or top-center):
```
[![PyPI version](https://badge.fury.io/py/project.svg)](https://badge.fury.io/py/project)
[![Downloads](https://pepy.tech/badge/project)](https://pepy.tech/project/project)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI Status](https://github.com/user/repo/workflows/CI/badge.svg)](https://github.com/user/repo/actions)
```

### B. Images
**Placement strategy**:
1. **Logo** — Top, before main text
2. **Architecture diagram** — After "Solution" section
3. **Results table screenshot** — In results section
4. **Flowchart** — Explaining key mechanism

**Size guidelines**:
- Hero images: 400-600px wide
- Inline diagrams: 300-400px
- Results table: Width of content

### C. Tables
**When to use**:
- Metrics definitions
- Baseline comparisons
- Hyperparameter reference
- Feature matrix vs related work

**When not to use**:
- For small lists (use bullets)
- For prose-heavy content (use sections)

### D. Code Blocks
**Practices**:
- Always include syntax highlighting language (```python, ```bash)
- Keep examples < 20 lines for quick start
- Full examples in linked scripts, not inline
- Use comments for clarity

### E. Emphasis
**Hierarchical emphasis** (in order of importance):
1. **Bold for critical concepts** (e.g., `**RAS**`)
2. `Code formatting for parameters/variables`
3. [Links](#) for navigation
4. > Blockquotes for important quotes/findings

---

## Section 10: Content Density & Readability

### A. Rule of Three
Most research READMEs organize key content into **3 main sections**:
1. **What is the problem?** (The Problem)
2. **What is the solution?** (The Solution + Mechanisms)
3. **Does it work?** (Experiments)

### B. Scannability
Readers should be able to:
- Understand contribution in 30 seconds (reading abstract + logo)
- Understand approach in 2 minutes (skimming mechanisms)
- Understand results in 1 minute (looking at table/graph)
- Get started in 5 minutes (Quick Start code)

### C. Word Count Guidelines
- **One-liner tagline**: 10-15 words
- **Problem statement**: 150-250 words
- **Solution summary**: 100-200 words
- **Per-mechanism explanation**: 50-100 words
- **Results summary**: 100-150 words
- **Total README**: 1,500-3,000 words (excluding code blocks)

---

## Section 11: Common Mistakes to Avoid

1. **Missing the core contribution in the first paragraph**
   - Readers should know the main idea in 30 seconds
   - Not buried in the "how" — start with the "what"

2. **Too much mathematical notation without explanation**
   - Always provide intuitive explanation before/after formulas
   - Include verbal descriptions (not just equations)

3. **Results buried in 5 pages of setup instructions**
   - Show proof of concept early
   - Put detailed setup instructions later or in docs/

4. **Generic or borrowed problem statement**
   - Customize the "Problem" section to your actual contribution
   - Avoid "LLMs are useful..." type openers

5. **Missing reproducibility details**
   - Exact versions of major dependencies
   - Random seeds used
   - Full hyperparameter values
   - Pre-computed results for expensive experiments

6. **No cross-model or ablation results**
   - Show that your contribution works across conditions
   - Isolate the impact of each component
   - Avoid cherry-picked results

7. **Links that go to private repos or 404s**
   - Test all links before publishing
   - Use official, stable URLs

8. **Inconsistent terminology**
   - Define all acronyms on first use
   - Use consistent naming throughout

---

## Section 12: Template for Your README

Based on all analysis, here's the **recommended structure** for research paper READMEs:

```markdown
# [Project Name]

[One-line pitch]

[Optional: Author/Date]

---

## The Problem

[2-3 numbered pain points of current approaches]

## The Solution

[1-2 sentence summary + metaphor + diagram]

## Novel Mechanisms

### 1. [Mechanism Name]
[Explanation + visual + intuitive analogy]

### 2. [Mechanism Name]
[Explanation + visual + intuitive analogy]

## Experiment Results

[Quantitative summary: "X% improvement over baseline"]

### Key Findings
[3-5 bullet points from ablations and cross-model tests]

### Metrics
[Table defining RAS, APR, ITC, TTC]

### Baselines
[Table of 6-8 baselines with descriptions]

### Ablations
[Table showing impact of each component]

## Project Structure

[Tree view of key directories]

## Setup

```bash
git clone ...
pip install -e ".[dev]"
```

### API Keys
[Environment variables for cloud providers + note about local option]

## Quick Start

[10-20 line Python example]

## Running Experiments

```bash
python experiments/run_experiment.py --config configs/...
```

## Hyperparameters

[Table: Parameter | Default | Description]

## Tests

```bash
python -m pytest tests/ -v
```

[Output showing passing tests]

## Citation

[BibTeX]

## License

[MIT License - Author, Year]
```

---

## Analysis Summary

### Most Impactful README Elements (Ranked)

1. **Clear, testable one-liner** (e.g., "Generate criteria before generating text, then evaluate progressively")
2. **Quantitative results in hero section** (e.g., "24× faster than Transformers")
3. **5-10 minute Quick Start code** (copy-paste and works)
4. **Visual architecture diagram** (single image explains core approach)
5. **Ablation study results** (proves each component matters)
6. **Cross-model evaluation note** (shows awareness of eval pitfalls)
7. **Hyperparameter table** (enables reproducibility)
8. **Baseline comparison** (contextualizes performance)

### Critical Success Factors

| Factor | Why it matters | Example |
|--------|---------------|---------|
| **Problem clarity** | If readers don't understand the gap, they won't care about the solution | Self-Refine: "Models generate without knowing what quality dimensions they must satisfy" |
| **Quantitative proof early** | Abstract numbers don't convince; concrete comparisons do | vLLM: "24× higher throughput than HuggingFace" |
| **Runnable example** | Users judge a project by "Can I try this in 5 minutes?" | Your EFA Quick Start is exemplary |
| **Ablation results** | Shows which components actually matter (not just nice-to-haves) | Your -FWRL ablation proving 80% vs 100% APR |
| **Cross-model evaluation** | Demonstrates awareness of self-preference bias | Your use of different eval model than generator |

---

## Conclusion

The **ideal research README** is a convergence of:
- **Academic rigor** (proper citations, ablations, metrics)
- **Pragmatism** (Quick Start code that runs)
- **Clarity** (problem → solution → proof in ~2000 words)
- **Visual impact** (diagrams, results tables, no walls of text)

Your current EFA README already hits most of these marks. The structure is solid, the mechanisms are well-explained, and the Quick Start code is copy-paste ready. With minor tweaks (adding comparison table to related work, possibly a visual architecture diagram), it will be exemplary.

---

## References

- [Self-Refine GitHub](https://github.com/madaan/self-refine)
- [Reflexion GitHub](https://github.com/noahshinn/reflexion)
- [Tree of Thoughts GitHub](https://github.com/princeton-nlp/tree-of-thought-llm)
- [LLM-Blender GitHub](https://github.com/yuchenlin/LLM-Blender)
- [G-Eval GitHub](https://github.com/nlpyang/geval)
- [vLLM GitHub](https://github.com/vllm-project/vllm)
- [SGLang GitHub](https://github.com/sgl-project/sglang)
- [DSPy GitHub](https://github.com/stanfordnlp/dspy)
