# Research README Patterns — Quick Visual Summary

## The Universal Structure (Used by All 8 Repos)

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER                                                       │
│ [Title] | [One-liner] | [Badges] | [Links]                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ HERO SECTION (30-60 seconds to understand)                  │
│ [Logo] + [Key metrics] + [Problem summary]                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ MAIN CONTENT (2-5 minutes to understand)                    │
│ [Problem] → [Solution] → [Mechanisms] → [Results]          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ GETTING STARTED (5 minutes to run)                          │
│ [Setup] → [Quick Start Code] → [Running Experiments]       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ REFERENCE (For deep dives)                                  │
│ [Project Structure] | [Hyperparams] | [Citation] | [Tests] │
└─────────────────────────────────────────────────────────────┘
```

---

## Pattern 1: The One-Liner (Your Most Important Line)

### Gold Standard Examples

| Repo | One-Liner |
|------|-----------|
| **Self-Refine** | LLMs can generate feedback on their work, use it to improve the output, and repeat this process iteratively. |
| **Reflexion** | Language Agents with Verbal Reinforcement Learning |
| **Tree of Thoughts** | Deliberate Problem Solving with Large Language Models |
| **vLLM** | Easy, fast, and cheap LLM serving for everyone. |
| **DSPy** | The framework for programming—not prompting—language models |
| **Your EFA** | Specification-Driven Generation via Dynamic Rubric Conditioning and Failure-Weighted Reattention |

### What Makes a Great One-Liner

✓ **Active voice** (verb-first when possible)
✓ **Concrete** (what it does, not "an approach to")
✓ **Comparative** (vs implied baseline)
✓ **Concise** (10-20 words max)
✓ **Memorable** (metaphor or contrast)

✗ **Avoid**: "An approach to improving LLM outputs" (too generic)
✗ **Avoid**: Technical jargon without context
✗ **Avoid**: "Machine learning for X" (says nothing)

---

## Pattern 2: Problem Statement (The "Why Should You Care" Section)

### Universal Structure

```
## The Problem

Current [approach/systems] treat [challenge] as [incorrect sequence]:

1. **Problem A**: [What breaks] → [Consequence]
   Example: "Models generate without knowing quality dimensions"

2. **Problem B**: [What fails] → [Consequence]
   Example: "Refinement feedback is holistic rather than per-dimension"

3. **Problem C**: [What's expensive/brittle] → [Consequence]
   Example: "All dimensions get equal emphasis regardless of failures"
```

### Why This Works

- Numbers create urgency (1, 2, 3)
- Bold text creates scanability
- Concrete examples > abstract claims
- Each problem ends with consequence, not just description

### Counter-Example (What NOT to Do)

```
## Background

Large language models have become popular in recent years due to
advances in transformer architectures. Many researchers have explored
ways to improve their outputs through feedback mechanisms...
```

✗ **Problem**: Too generic, no urgency, no specific gap identified

---

## Pattern 3: Solution Section (Architecture & Mechanism Breakdown)

### Universal Structure

```
## The Solution

[1-2 sentence high-level summary]

[Metaphor or analogy for quick understanding]

![Diagram showing core approach]

### Mechanism 1: [Name]
[Explanation] + [Visual] + [Why it matters]

### Mechanism 2: [Name]
[Explanation] + [Visual] + [Why it matters]

### Mechanism 3: [Name]
[Explanation] + [Visual] + [Why it matters]
```

### Checklist for Each Mechanism

- [ ] **Conceptual**: What does it do?
- [ ] **Visual**: Diagram, flowchart, or pseudocode
- [ ] **Mathematical**: Equation (if relevant) with explanation
- [ ] **Intuitive**: Analogy or plain-language summary
- [ ] **Comparative**: How is this different from prior work?
- [ ] **Impact**: What would happen if we removed it?

### Real Example: Your EFA README

```markdown
### 2. Failure-Weighted Reattention Loop (FWRL)

After generation, each criterion is scored independently.
Failed criteria receive mathematically boosted emphasis weights:

w_i^(k+1) = w_i^(k) * (1 + α * max(0, τ - s_i^(k)))

- Passed criteria (score >= τ): weights unchanged
- Failed criteria: weight boost proportional to failure severity
- Analogous to **focal loss** but applied to evaluation dimensions at inference time
```

✓ **Has**: Equation + plain explanation + analogy → **Excellent**

---

## Pattern 4: Results Section (Proof of Concept)

### The Three-Layer Presentation

#### Layer 1: Quantitative Snapshot (1-3 metrics, hero section)

```
Key results: [Exact %improvement] over [specific baseline]

Examples:
- "~20% improvement on average across 7 diverse tasks" (Self-Refine)
- "91% pass@1 on HumanEval (vs 80% GPT-4)" (Reflexion)
- "74% on Game of 24 (vs 4% GPT-4 CoT)" (Tree of Thoughts)
- "24× higher throughput than HuggingFace Transformers" (vLLM)
```

#### Layer 2: Results Visualization (Middle section)

```
[Large screenshot or image of results table]

### Key Findings (Bulleted)
- Finding 1: [Specific ablation insight]
- Finding 2: [Cross-model discovery]
- Finding 3: [Surprising or novel result]
```

#### Layer 3: Detailed Breakdown (Reference tables)

```
### Metrics Explained
| Metric | Description | Range |
|--------|-------------|-------|

### Baselines
| # | Baseline | What it tests |
|---|----------|---------------|

### Ablations
| Ablation | Removed | Impact |
|----------|---------|--------|
```

### Critical Rule: Show Your Work

Every claimed improvement must be backed by:
- [ ] Baseline comparison
- [ ] Statistical significance (if possible)
- [ ] Ablation showing the component matters
- [ ] Cross-model or cross-dataset validation

---

## Pattern 5: Getting Started (The Fast Path)

### The 5-Step Quick Start

```python
# Step 1: Import
from project_name import MainClass

# Step 2: Initialize with key params
obj = MainClass(
    param1=value1,     # What this controls
    param2=value2,     # What this controls
)

# Step 3: Run
result = obj.run(example_input)

# Step 4: Access results
print(result.output)
print(result.metric)

# Step 5: (Optional) Advanced usage
```

### Checklist

- [ ] Code runs without modification (copy-paste ready)
- [ ] All imports work (no missing packages)
- [ ] Comments explain what each param does
- [ ] Output is shown (what should user see?)
- [ ] Takes < 30 seconds to run
- [ ] All keys/credentials optional or explained

### Real Example: Your EFA README

```python
from efa import EFAPipeline

pipeline = EFAPipeline(
    model="gpt-4o",                      # Generator
    evaluator_model="claude-sonnet-4",   # Cross-model for unbiased eval
    n_criteria=5,                        # Number of quality dimensions
    threshold=0.6,                       # Pass threshold
    max_iterations=3,                    # Max refinement loops
    alpha=2.0,                           # Reattention strength
)

result = pipeline.run("Explain quantum entanglement...")
print(result.response)              # Final output
print(result.rubric_adherence_score) # Quality score
```

✓ **Excellent**: Shows cross-model choice, explains each param, clear output

---

## Pattern 6: Badges (Visual Credibility)

### Standard Badge Types (in order of importance)

```markdown
[![PyPI version](badge.svg)](link)        # Shows package is distributed
[![License: MIT](badge.svg)](link)        # Shows it's open source
[![Downloads](badge.svg)](link)           # Shows adoption
[![CI Status](badge.svg)](link)           # Shows code quality
[![Stars](badge.svg)](link)               # Shows community interest
```

### Where to Place Badges

- **Option 1** (Top-right): Clean look, visible to all
- **Option 2** (Below title): Natural reading flow
- **Option 3** (In navigation bar): Professional appearance

### Examples of Well-Badged READMEs

- vLLM: Shows PyPI, downloads, license, stars
- Tree of Thoughts: Shows PyPI, Python version, license, Zenodo DOI
- DSPy: Shows PyPI downloads badge prominently

---

## Pattern 7: Hyperparameter Reference (Configuration)

### Standard Table Format

```markdown
| Parameter | Default | Description | Range | Notes |
|-----------|---------|-------------|-------|-------|
| `n_criteria` | 5 | Number of quality dimensions | 3-10 | Higher = slower, possibly more rigorous |
| `threshold` | 0.6 | Pass score (0-1) | 0.4-0.8 | Adjust based on task difficulty |
| `max_iterations` | 3 | Max refinement loops | 1-5 | Cost-quality tradeoff |
| `alpha` | 2.0 | Reattention strength | 0.5-5.0 | Higher = more aggressive reweighting |
```

### What Users Need

✓ **Current value**: So they know defaults
✓ **Description**: What this parameter controls
✓ **Range**: What values make sense
✓ **When to adjust**: Guidance on tuning

✗ **Avoid**: Just listing parameter names with no guidance

---

## Pattern 8: Citation Format (Academic Credibility)

### Standard BibTeX Template

```bibtex
@article{lastname2024projectname,
  title={Descriptive Title: With Colon and Subtitle},
  author={First Author and Second Author and Third Author},
  journal={Conference/Journal Name},
  year={2024},
  pages={page_numbers},
  doi={doi_if_available}
}
```

### Venue-Specific Formats

**NeurIPS**:
```bibtex
@inproceedings{lastname2023project,
  title={...},
  author={...},
  booktitle={Advances in Neural Information Processing Systems},
  year={2023}
}
```

**ICLR/ICML/ACL/EMNLP**: Similar pattern, just change booktitle

### Best Practice

Always provide:
1. BibTeX (for LaTeX users)
2. APA (for social sciences)
3. Chicago (for general use)

But minimum acceptable = BibTeX only

---

## Pattern 9: Project Structure (Navigation Aid)

### Good Format

```
project-name/
├── src/project/                  # Core implementation
│   ├── pipeline.py               # Main algorithm
│   ├── component1.py             # First mechanism
│   ├── component2.py             # Second mechanism
│   └── models.py                 # Data models
├── experiments/
│   ├── prompts/                  # Test data
│   ├── results/                  # Outputs
│   └── run_experiment.py         # Runner
├── configs/                      # Config files (YAML)
├── tests/                        # Unit tests
├── docs/                         # Documentation
└── paper/                        # LaTeX source
```

### What to Include

✓ Key directories (src, experiments, tests, docs, paper)
✓ Brief description of what each does
✓ Hierarchy showing relationships
✓ Highlights main entry points

✗ **Avoid**: 100-line tree (too much detail)
✗ **Avoid**: No descriptions (what is each folder?)
✗ **Avoid**: Hidden files/caches

---

## Pattern 10: Baseline Comparison (Context)

### Comparison Table Format

```markdown
| Work | Venue | Year | Key Advantage | Limitation |
|------|-------|------|---------------|-----------|
| [Citation A] | NeurIPS | 2022 | No training needed | Holistic feedback only |
| [Citation B] | ICLR | 2023 | Supports refinement | Requires RL fine-tuning |
| [Citation C] | ACL | 2023 | Cross-model eval | Smaller scale experiments |
| **This Work** | - | 2024 | **All three + failure weighting** | **Requires multiple models** |
```

### Why This Matters

- Shows you understand related work
- Positions your contribution clearly
- Avoids strawman comparisons
- Demonstrates intellectual honesty

---

## Pattern 11: Ablations (Proof Each Part Matters)

### Standard Ablation Design

```markdown
### Ablations

| Ablation | Removed Component | Impact on [Primary Metric] | Interpretation |
|----------|-------------------|------------------------|------------|
| -Mechanism1 | Mechanism 1 | Drops 15% → 85% | **Critical** |
| -Mechanism2 | Mechanism 2 | Drops 8% → 92% | **Important** |
| -Both | Mechanisms 1+2 | Drops 22% → 78% | Cumulative effect |
| -Iteration | Refinement loop | Drops 20% → 80% | Critical to approach |

**Conclusion**: FWRL (failure weighting) is the only ablation that produces < 100% APR,
confirming its importance to preventing quality failures.
```

### What This Shows

✓ **Impact quantified**: Each component's contribution measured
✓ **Trade-offs visible**: What you lose when removing each part
✓ **Design justified**: Why the architecture is the way it is
✓ **Reproducibility**: Others can verify these claims

---

## Pattern 12: Tests (Quality Assurance)

### Standard Test Output

```bash
$ python -m pytest tests/ -v

tests/test_models.py::test_param1_validation       PASSED
tests/test_models.py::test_param2_validation       PASSED
tests/test_pipeline.py::test_end_to_end            PASSED
tests/test_component1.py::test_mechanism1          PASSED
tests/test_component2.py::test_mechanism2          PASSED
tests/test_integration.py::test_full_pipeline      PASSED

========================= 6 passed in 0.45s =========================
```

### What to Test

- [ ] Data model validation (correctness of inputs)
- [ ] Individual components (each mechanism works)
- [ ] End-to-end pipeline (whole system works)
- [ ] Edge cases (handles errors gracefully)
- [ ] Cross-model evaluation (different models work together)

### Best Practice

- **Minimum**: 5 tests covering main code paths
- **Good**: 20+ tests with decent coverage
- **Excellent**: 50+ tests including edge cases + property-based tests

---

## Hierarchy of Information Density

### 30-Second Read (Hero Section)
- One-liner
- Key metric (1-2 results)
- Problem summary (3 bullets)
- Logo + architecture diagram

### 2-Minute Read (Skimming)
- Problem statement (full)
- Solution summary
- Mechanism names + brief explanations
- Results snapshot (table screenshot)

### 5-Minute Read (Understanding)
- All of above plus:
- Detailed mechanism explanations
- Quick Start code
- Key ablation insights
- Baseline comparisons

### 20-Minute Read (Deep Dive)
- All of above plus:
- Complete experimental details
- Hyperparameter analysis
- Full project structure
- Contributing guidelines
- Citation format

### 1-Hour Read (Implementation)
- Everything, including:
- Line-by-line code walkthroughs
- Full test suite
- Design decisions & trade-offs
- Troubleshooting guide
- Deployment instructions

---

## Red Flags (What NOT to Do)

### ❌ Structure Red Flags
- No clear one-liner or problem statement
- Architecture diagram missing or incomprehensible
- Results buried on page 5, not in first 2 pages
- No Quick Start code (or requires 50 lines of setup)

### ❌ Content Red Flags
- Metrics not clearly defined (what does "score" mean?)
- No ablations (how do we know which parts matter?)
- No baseline comparisons (context for results?)
- Same model for generation AND evaluation (self-preference bias)
- Results seem too good to be true (no confidence intervals)

### ❌ Technical Red Flags
- Quick Start code doesn't run as written
- Links are broken (test them!)
- API key documentation missing
- Tests don't pass (`pytest tests/` fails)
- No way to reproduce paper results

### ❌ Metadata Red Flags
- Missing BibTeX citation
- No license specified
- Author contact missing
- Paper link is broken

---

## Scoring Your README (Self-Checklist)

Rate yourself 0-10 on each dimension:

| Dimension | 0-2 | 3-5 | 6-8 | 9-10 |
|-----------|-----|-----|-----|------|
| **One-liner clarity** | Confusing | Generic | Clear | Memorable |
| **Problem statement** | Missing | Generic | Specific | Compelling |
| **Solution explanation** | Unclear | Vague | Clear | Intuitive + diagrams |
| **Mechanisms** | Missing | Listed | Explained | Explained + visual + analogy |
| **Results credibility** | No results | Weak | Quantified | Quantified + baselines + ablations |
| **Quick Start** | Missing | Complex | Works | Copy-paste ready |
| **Project structure** | Missing | Unclear | Clear | Clear + brief |
| **Hyperparameters** | Missing | Listed | Explained | Explained + tuning guidance |
| **Tests** | Missing | Incomplete | Working | >80% coverage |
| **Citation** | Missing | Incomplete | Complete | Multiple formats |
| **Overall readability** | Walls of text | Paragraph-heavy | Good structure | Highly scannable |

**Scoring**:
- **80-110**: Excellent (exemplary research README)
- **60-79**: Good (clear, usable, but missing polish)
- **40-59**: Acceptable (works, but unclear in places)
- **<40**: Needs revision (usability issues)

---

## Final Recommendations for Your EFA README

Your current README is already **very strong** (estimated 85-90/110).

### Quick Wins (5-10 minute additions)

1. **Add comparison table** to "Related Work" section
   - Shows Self-Refine, Reflexion, etc.
   - Your unique components vs theirs

2. **Add visual architecture diagram**
   - Shows: Query → Criteria Gen → CMPG → FWRL → Response
   - One clear image > 100 words

3. **Expand "Key Findings"** section
   - Add interpretation of each ablation
   - Explain why FWRL matters most

### Optional Enhancements (15-30 minutes)

4. **Add "Lessons Learned"** subsection under Results
   - What surprised you?
   - What would you try next?
   - What's still an open problem?

5. **Add "Related Work" comparison table**
   - Positions EFA vs Self-Refine, Reflexion, etc.

6. **Add Troubleshooting/FAQ section**
   - Common questions from users

7. **Add Roadmap**
   - Planned features
   - Known limitations

---

## References & Sources

- [Self-Refine GitHub](https://github.com/madaan/self-refine)
- [Reflexion GitHub](https://github.com/noahshinn/reflexion)
- [Tree of Thoughts GitHub](https://github.com/princeton-nlp/tree-of-thought-llm)
- [LLM-Blender GitHub](https://github.com/yuchenlin/LLM-Blender)
- [G-Eval GitHub](https://github.com/nlpyang/geval)
- [vLLM GitHub](https://github.com/vllm-project/vllm)
- [SGLang GitHub](https://github.com/sgl-project/sglang)
- [DSPy GitHub](https://github.com/stanfordnlp/dspy)

For full analysis: See `README_TEMPLATE_ANALYSIS.md`
For ready-to-use template: See `README_QUICK_TEMPLATE.md`
