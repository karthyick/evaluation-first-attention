# Research README Standard — Complete Documentation Index

This directory contains 5 comprehensive documents analyzing the README standards used by premier AI/ML research repositories. Together they form a complete guide to writing excellent research paper READMEs.

## Quick Navigation

### I Need... | Read This | Time
---|---|---
A checklist before publishing | `README_RESEARCH_GUIDE.md` → Verification Checklist | 5 min
To write a README from scratch | `README_QUICK_TEMPLATE.md` | 15 min
To improve my existing README | `README_PATTERNS_SUMMARY.md` | 10 min
To understand the theory | `README_TEMPLATE_ANALYSIS.md` | 30 min
To see real examples | `README_REAL_EXAMPLES.md` | 15 min
All of the above | Read in order below | 90 min

---

## The 5 Documents Explained

### 1. **README_RESEARCH_GUIDE.md** — Start Here
**Type**: Navigation guide + meta-analysis
**Length**: 2,500 words
**Best for**: Understanding how to use the other documents

**Contains**:
- Overview of all 4 guides
- How to use guides by different workflows
- Recommended reading order by role
- Key statistics from the analysis (8 repos, 32K words analyzed)
- Assessment of your EFA README (estimated 85-90/110)
- Quick wins for improvement
- Research venue citation formats
- FAQ about READMEs
- Verification checklist before publishing

**Read this first to understand the landscape.**

---

### 2. **README_TEMPLATE_ANALYSIS.md** — Deep Dive
**Type**: Detailed explanation + theory
**Length**: 3,000+ words
**Best for**: Understanding *why* each section exists

**Contains**:
- **Section 1**: Overall structure & flow (universal pattern)
- **Section 2**: Detailed section breakdown (12 key sections)
- **Section 3**: Experimental results & metrics
- **Section 4**: Getting started & installation patterns
- **Section 5**: Project organization & structure
- **Section 6**: Testing & validation
- **Section 7**: Citation & attribution standards
- **Section 8**: Advanced sections (roadmap, contributing, etc.)
- **Section 9**: Visual & formatting best practices
- **Section 10**: Content density & readability rules
- **Section 11**: Common mistakes to avoid
- **Section 12**: Template structure summary

**Key insights**:
- All research READMEs follow 3-part structure: Problem → Solution → Proof
- Hero section (30-60 sec) must capture core contribution
- Results must include baselines + ablations to be credible
- Same model for generation AND evaluation = self-preference bias
- 1,500-3,000 words is the sweet spot

**Read this for academic understanding of README structure.**

---

### 3. **README_QUICK_TEMPLATE.md** — Implementation
**Type**: Copy-paste starting point
**Length**: 1,500 words
**Best for**: Writing a README right now

**Contains**:
- Complete README skeleton with all sections
- Placeholder text for each section
- Example code blocks
- Example tables
- Example commands
- Full checklist (17 items) before publishing

**How to use**:
1. Copy entire content into your README.md
2. Replace `[bracketed text]` with your specific content
3. Fill in metrics from your experiments
4. Add images (architecture, results)
5. Run through checklist

**This is a template you can use directly.**

---

### 4. **README_PATTERNS_SUMMARY.md** — Quick Reference
**Type**: Visual patterns + checklists
**Length**: 2,000 words
**Best for**: Learning by example patterns

**Contains**:
- **Universal structure diagram** (flowchart)
- **Pattern 1-12**: One pattern per major README section
  - For each: good format, gold standard examples, what to avoid
- **Hierarchy of information density**:
  - 30-second read (hero section only)
  - 2-minute read (skimming)
  - 5-minute read (understanding)
  - 20-minute read (deep dive)
  - 1-hour read (implementation)
- **Red flags checklist** (what NOT to do)
- **Self-scoring rubric** (0-110 scale, 11 dimensions)
- **Final recommendations for EFA README** (quick wins vs enhancements)

**Key patterns shown**:
- Pattern 1: The One-Liner (10-20 words, memorable, action-oriented)
- Pattern 2: Problem Statement (3 numbered pain points)
- Pattern 3: Solution Section (summary + metaphor + diagram)
- Pattern 4: Results Section (3-layer: snapshot, visualization, details)
- Pattern 5: Getting Started (5-step quick start code)
- Pattern 6: Badges (what to show, where to place)
- Pattern 7: Hyperparameters (table format with tuning guidance)
- Pattern 8: Citations (BibTeX for different venues)
- Pattern 9: Project Structure (tree view, key directories)
- Pattern 10: Baselines (comparison table)
- Pattern 11: Ablations (impact of each component)
- Pattern 12: Tests (pytest output format)

**This is for visual learners and quick reference.**

---

### 5. **README_REAL_EXAMPLES.md** — Reference
**Type**: Actual excerpts from 8 research repos
**Length**: 2,500+ words
**Best for**: Seeing how real research repos implement patterns

**Contains**:
For each of 8 repositories:
- Title section (exact text)
- Content structure pattern
- Key technical explanation
- Setup pattern
- Important notes (reproducibility, transparency)
- Citation in BibTeX

**Repositories included**:
1. **Self-Refine** (Madaan et al., 2023) — ICLR
2. **Reflexion** (Shinn et al., 2023) — NeurIPS
3. **Tree of Thoughts** (Yao et al., 2023) — NeurIPS
4. **LLM-Blender** (Jiang et al., 2023) — ACL
5. **G-Eval** (Liu et al., 2023) — EMNLP
6. **vLLM** (LMSYS/Berkeley) — SOSP
7. **SGLang** (2024) — NeurIPS
8. **DSPy** (Stanford, 2023) — ICLR

**Also includes**:
- Comparative analysis of opening paragraphs
- Key takeaways (what to copy vs. what makes them special)
- Direct links to full original READMEs on GitHub

**This is for concrete examples and inspiration.**

---

## Recommended Reading Flows

### Flow A: "I Want a README Template Right Now"
**Time**: 20 minutes

1. **README_QUICK_TEMPLATE.md** (15 min)
   - Copy template into your README.md
   - Replace placeholders

2. **README_PATTERNS_SUMMARY.md** (5 min)
   - Check your sections against patterns
   - Adjust tone/structure if needed

**Result**: Working README with correct structure

---

### Flow B: "I Want to Improve My Existing README"
**Time**: 45 minutes

1. **README_PATTERNS_SUMMARY.md** (15 min)
   - Self-score your README (0-110 scale)
   - Identify weak sections (scoring < 6/10)

2. **README_RESEARCH_GUIDE.md** (10 min)
   - Read "Quick Wins" section
   - Plan 2-3 improvements

3. **README_REAL_EXAMPLES.md** (15 min)
   - Find similar sections in real repos
   - Copy patterns/wording

4. **README_RESEARCH_GUIDE.md** (5 min)
   - Run verification checklist
   - Test all links and code

**Result**: Improved README with 5-10 point score increase

---

### Flow C: "I Want to Understand the Theory"
**Time**: 90 minutes

1. **README_RESEARCH_GUIDE.md** (10 min)
   - Get overview of landscape
   - See statistics from 8 repos

2. **README_TEMPLATE_ANALYSIS.md** (45 min)
   - Read Sections 1-7 (core content)
   - Skim Section 8-12 (optional enhancements)
   - Focus on why each section matters

3. **README_REAL_EXAMPLES.md** (20 min)
   - See how theory shows up in practice
   - Read comparative analysis

4. **README_PATTERNS_SUMMARY.md** (15 min)
   - Consolidate learning with visual patterns
   - Self-score your own README

**Result**: Deep understanding of research README structure

---

### Flow D: "I'm Reviewing Someone's README"
**Time**: 25 minutes

1. **README_PATTERNS_SUMMARY.md** (15 min)
   - Use self-scoring rubric (0-110 scale)
   - Score each dimension 0-10
   - Identify weak areas

2. **README_TEMPLATE_ANALYSIS.md** (5 min)
   - Reference Section 11 (red flags)
   - Note specific issues

3. **README_REAL_EXAMPLES.md** (5 min)
   - Find good patterns to suggest
   - Copy exact wording to recommend

**Result**: Constructive review with specific, actionable feedback

---

## Key Statistics from Analysis

### What We Analyzed
- **8 research repositories** from top-tier venues (NeurIPS, ICML, ICLR, ACL, EMNLP)
- **32,000+ words** of actual README content
- **Patterns** appearing in 100% of repositories

### Universal Sections (Found in All 8)
1. Clear title + memorable one-liner
2. Specific problem statement (not generic)
3. Solution explanation (conceptual + technical)
4. Quantitative results with baselines
5. Quick Start code (copy-paste ready)
6. BibTeX citation

### Common Metrics Across All Repos
- Average one-liner length: 10-15 words
- Average problem statement: 150-250 words
- Average total README: 1,500-3,000 words
- Number of code examples: 2-5
- Number of images: 1-3 (architecture, results, optional flowchart)
- Number of tables: 3-5 (metrics, baselines, ablations, hyperparameters)

### What Makes READMEs Stand Out
1. Visual architecture diagram (helps readers understand approach quickly)
2. Comprehensive ablation study (proves each component matters)
3. Cross-model evaluation (shows awareness of evaluation pitfalls)
4. Clear hyperparameter guidance (helps users tune)
5. Reproducibility notes (seeds, variance, pre-computed logs)
6. Community presence (Discord, GitHub discussions, email)

---

## How to Use These Documents with Your EFA README

### Current Status Assessment
Your EFA README is **estimated 85-90 / 110** (very strong):

**Strengths**:
✓ Clear problem statement with 3 specific pain points
✓ Solution explanation with memorable TDD metaphor
✓ Two mechanisms well-explained with math + intuition
✓ Quantified results (100% vs 80% APR with -FWRL)
✓ Ablations clearly showing which components matter
✓ Quick Start code that's copy-paste ready
✓ Excellent cross-model evaluation choice
✓ Proper citations and BibTeX format

### Quick Improvements (5-15 minutes each)

**1. Add related work comparison table**
- Shows EFA vs Self-Refine, Reflexion, etc.
- Makes your contribution clear

**2. Add visual architecture diagram**
- Shows: Query → Criteria Gen → Progressive Masking → FWRL → Response
- One clear image helps understanding

**3. Expand "Key Findings" section**
- Why FWRL is the critical component (proved by ablation)
- Insight about dynamic vs fixed criteria
- Benefit of cross-model evaluation

---

## Document Maintenance

### Version
- **Created**: March 2026
- **Repositories Analyzed**: 8 (Self-Refine, Reflexion, ToT, LLM-Blender, G-Eval, vLLM, SGLang, DSPy)
- **Total Content Analyzed**: 32,000+ words of actual READMEs

### If You Find Issues
- Typos or outdated examples → Report via GitHub issue
- Broken links → Test with curl first, then report
- New patterns to add → Suggest with supporting repos

### Contributing Improvements
If you improve the templates or find new patterns:
1. Document the change
2. Show supporting example from a repo
3. Test with 2-3 new README examples
4. Submit improvements

---

## Quick Reference Tables

### When to Read Each Document

| Document | Primary Use | Secondary Use | Avoid If |
|----------|-------------|---------------|----------|
| README_RESEARCH_GUIDE.md | Navigation | FAQ | You know what you need |
| README_QUICK_TEMPLATE.md | Write new | Copy structure | You like learning theory first |
| README_TEMPLATE_ANALYSIS.md | Understand why | Reference | You're in a hurry |
| README_PATTERNS_SUMMARY.md | Quick reference | Review others | You need details |
| README_REAL_EXAMPLES.md | See implementations | Copy wording | You prefer theory |

### Effort vs. Impact

| Change | Effort | Impact | Priority |
|--------|--------|--------|----------|
| Add comparison table | 10 min | Medium | Quick Win |
| Add architecture diagram | 15 min | High | Quick Win |
| Expand ablations section | 10 min | Medium | Quick Win |
| Reorganize sections | 30 min | Medium | Medium |
| Add roadmap section | 15 min | Low | Optional |
| Rewrite for clarity | 45 min | High | If time permits |

---

## Citation

If you reference this analysis in your own work:

```bibtex
@misc{raj2026readmeanalysis,
  title={Research Paper README Standard: Analysis of 8 Premier AI/ML Repositories},
  author={Raj, Karthick},
  year={2026},
  month={March},
  howpublished={\url{https://github.com/karthyick/evaluation-first-attention/docs}},
  note={Analysis of repositories: Self-Refine, Reflexion, Tree of Thoughts, LLM-Blender, G-Eval, vLLM, SGLang, DSPy}
}
```

---

## Summary

This 5-document guide represents analysis of:
- 8 top-tier research repositories
- 32,000+ words of actual README content
- 12 distinct README patterns
- 100% coverage of universal sections

**Use these documents to write READMEs that are:**
- Clear (readers understand in 2 minutes)
- Credible (baselines + ablations + cross-model eval)
- Usable (copy-paste Quick Start code)
- Professional (matches peer standards)

**Start with README_RESEARCH_GUIDE.md or pick your workflow above.**

Good luck with your research!
