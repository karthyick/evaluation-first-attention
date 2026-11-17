# Significance of the MT-Bench results (80 prompts, 12 methods)

Reproduce: `python scripts/significance.py <results dir>` (10,000 bootstrap draws, seed 0; exact two-sided McNemar on paired All-Pass outcomes).

| Method | APR | 95% CI |
|---|---|---|
| EFA | 96.2 | 91.2 - 100.0 |
| EFA without FWRL | 96.2 | 91.2 - 100.0 |
| EFA without CMPG | 92.5 | 86.2 - 97.5 |
| FusioN | 92.5 | 86.2 - 97.5 |
| Self-Refine | 92.5 | 86.2 - 97.5 |
| Best-of-5 | 91.2 | 85.0 - 97.5 |
| All-criteria-at-once | 90.0 | 83.8 - 96.2 |
| Uniform reattention | 90.0 | 82.5 - 96.2 |
| EFA without dynamic criteria | 88.8 | 81.2 - 95.0 |
| EFA without iteration | 83.8 | 75.0 - 91.2 |
| Rubric-then-score | 72.5 | 62.5 - 82.5 |
| Single-pass | 71.2 | 61.3 - 81.2 |

EFA vs each method (prompts only EFA passes / prompts only the other passes / p):

| Versus | EFA only | Other only | p |
|---|---|---|---|
| Single-pass | 20 | 0 | 1.9e-06 |
| Rubric-then-score | 20 | 1 | 2.1e-05 |
| EFA without iteration | 11 | 1 | 0.006 |
| EFA without dynamic criteria | 8 | 2 | 0.109 |
| All-criteria-at-once | 6 | 1 | 0.125 |
| Uniform reattention | 6 | 1 | 0.125 |
| Best-of-5 | 4 | 0 | 0.125 |
| EFA without CMPG | 3 | 0 | 0.25 |
| FusioN | 3 | 0 | 0.25 |
| Self-Refine | 4 | 1 | 0.375 |
| EFA without FWRL | 1 | 1 | 1.0 |

Reading: the gain over single-pass, rubric-then-score and the no-iteration ablation is significant. The gap to Self-Refine, FusioN and Best-of-5 (3 to 4 prompts) is not significant at 80 prompts.
