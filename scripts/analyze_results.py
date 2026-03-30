"""Statistical analysis of EFA experiment results - Karthick Raja M, 2026.

Computes per-method aggregate statistics, pairwise Wilcoxon signed-rank tests
(EFA vs each other method), Friedman test across all methods, and outputs a
Rich table plus a JSON summary file.

Usage:
    python scripts/analyze_results.py --results experiments/results/results_XXXXX.json
    python scripts/analyze_results.py --results experiments/results/results_XXXXX.json --out analysis_out.json
    python scripts/analyze_results.py --results experiments/results/results_XXXXX.json --bootstrap-iters 10000
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from numpy.random import default_rng
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from scipy import stats as scipy_stats

console = Console()

# Canonical method display order (EFA first, baselines, then ablations)
_METHOD_ORDER = [
    "efa",
    "single-pass",
    "self-refine",
    "rubric-then-score",
    "all-criteria-at-once",
    "uniform-reattention",
    "best-of-n",
    "fusion",
    "efa-no-dyncriteria",
    "efa-no-cmpg",
    "efa-no-fwrl",
    "efa-no-iteration",
]

_METHOD_DISPLAY = {
    "efa": "EFA (full pipeline)",
    "single-pass": "Single-Pass",
    "self-refine": "Self-Refine",
    "rubric-then-score": "Rubric-then-Score",
    "all-criteria-at-once": "All-Criteria-at-Once",
    "uniform-reattention": "Uniform Reattention",
    "best-of-n": "Best-of-N",
    "fusion": "FusioN",
    "efa-no-dyncriteria": "EFA -DynCriteria",
    "efa-no-cmpg": "EFA -CMPG",
    "efa-no-fwrl": "EFA -FWRL",
    "efa-no-iteration": "EFA -Iteration",
}

# Minimum number of *non-zero differences* required for a valid Wilcoxon test.
# scipy.stats.wilcoxon needs at least 1 non-zero difference to avoid degenerate
# output; we require 4 for the p-value to be meaningful at all.
_MIN_N_WILCOXON = 4
_MIN_N_FRIEDMAN = 3


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_records(path: Path) -> list[dict[str, Any]]:
    """Load experiment records from a JSON results file.

    Args:
        path: Path to the JSON results file produced by run_experiment.py.

    Returns:
        List of record dicts, each representing one ExperimentRecord.

    Raises:
        SystemExit: If the file does not exist or is not valid JSON.
    """
    if not path.exists():
        console.print(f"[red]Results file not found: {path}[/red]")
        sys.exit(1)

    try:
        with open(path, encoding="utf-8") as fh:
            records = json.load(fh)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Failed to parse JSON: {exc}[/red]")
        sys.exit(1)

    if not isinstance(records, list) or len(records) == 0:
        console.print("[red]Results file is empty or not a list.[/red]")
        sys.exit(1)

    return records


# ---------------------------------------------------------------------------
# Bootstrap confidence interval
# ---------------------------------------------------------------------------


def bootstrap_ci_mean(
    values: list[float],
    n_iter: int = 10_000,
    ci: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """Compute a bootstrap confidence interval for the mean.

    Args:
        values: Observed sample values.
        n_iter: Number of bootstrap resamples.
        ci: Desired coverage (e.g., 0.95 for 95% CI).
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (lower_bound, upper_bound).
    """
    arr = np.asarray(values, dtype=float)
    rng = default_rng(seed)
    boot_means = np.empty(n_iter, dtype=float)
    n = len(arr)

    for i in range(n_iter):
        sample = rng.choice(arr, size=n, replace=True)
        boot_means[i] = sample.mean()

    alpha = 1.0 - ci
    lo = float(np.percentile(boot_means, 100 * alpha / 2))
    hi = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))
    return lo, hi


# ---------------------------------------------------------------------------
# Wilson score CI for a proportion
# ---------------------------------------------------------------------------


def wilson_score_ci(
    successes: int,
    n: int,
    ci: float = 0.95,
) -> tuple[float, float]:
    """Compute the Wilson score confidence interval for a proportion.

    Args:
        successes: Number of successes (APR = True).
        n: Total trials.
        ci: Desired coverage.

    Returns:
        Tuple of (lower_percent, upper_percent) as percentages [0, 100].
    """
    if n == 0:
        return 0.0, 0.0

    z = scipy_stats.norm.ppf(1 - (1 - ci) / 2)
    p_hat = successes / n
    denom = 1 + z**2 / n
    centre = (p_hat + z**2 / (2 * n)) / denom
    half_width = (z * np.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))) / denom
    lo = max(0.0, centre - half_width)
    hi = min(1.0, centre + half_width)
    return lo * 100, hi * 100


# ---------------------------------------------------------------------------
# Per-method statistics
# ---------------------------------------------------------------------------


def compute_method_stats(
    records: list[dict[str, Any]],
    n_bootstrap: int = 10_000,
) -> dict[str, dict[str, Any]]:
    """Aggregate per-method statistics over all records.

    Args:
        records: Raw experiment records loaded from JSON.
        n_bootstrap: Bootstrap iterations for RAS CI.

    Returns:
        Dict mapping method name to a statistics dict with keys:
            ras_mean, ras_std, ras_ci_lo, ras_ci_hi,
            apr_pct, apr_ci_lo, apr_ci_hi,
            itc_mean, itc_std,
            ttc_mean, ttc_std,
            n, ras_values (raw list).
    """
    buckets: dict[str, dict[str, list[Any]]] = defaultdict(
        lambda: {"ras": [], "apr": [], "itc": [], "ttc": []}
    )

    for rec in records:
        m = rec["method"]
        buckets[m]["ras"].append(float(rec["ras"]))
        buckets[m]["apr"].append(bool(rec["apr"]))
        buckets[m]["itc"].append(int(rec["itc"]))
        buckets[m]["ttc"].append(int(rec["ttc"]))

    result: dict[str, dict[str, Any]] = {}
    for method, data in buckets.items():
        ras_vals = data["ras"]
        apr_vals = data["apr"]
        itc_vals = data["itc"]
        ttc_vals = data["ttc"]
        n = len(ras_vals)

        ras_arr = np.asarray(ras_vals, dtype=float)
        itc_arr = np.asarray(itc_vals, dtype=float)
        ttc_arr = np.asarray(ttc_vals, dtype=float)

        apr_count = sum(apr_vals)
        apr_pct = apr_count / n * 100

        ci_lo, ci_hi = bootstrap_ci_mean(ras_vals, n_iter=n_bootstrap)
        apr_ci_lo, apr_ci_hi = wilson_score_ci(apr_count, n)

        result[method] = {
            "ras_mean": float(ras_arr.mean()),
            "ras_std": float(ras_arr.std(ddof=1)) if n > 1 else 0.0,
            "ras_ci_lo": ci_lo,
            "ras_ci_hi": ci_hi,
            "apr_pct": apr_pct,
            "apr_ci_lo": apr_ci_lo,
            "apr_ci_hi": apr_ci_hi,
            "itc_mean": float(itc_arr.mean()),
            "itc_std": float(itc_arr.std(ddof=1)) if n > 1 else 0.0,
            "ttc_mean": float(ttc_arr.mean()),
            "ttc_std": float(ttc_arr.std(ddof=1)) if n > 1 else 0.0,
            "n": n,
            "ras_values": ras_vals,
        }

    return result


# ---------------------------------------------------------------------------
# Paired RAS values (prompt-aligned)
# ---------------------------------------------------------------------------


def build_paired_ras(
    records: list[dict[str, Any]],
) -> dict[str, dict[str, float]]:
    """Build a dict of {method: {prompt_id: ras}} for paired tests.

    Args:
        records: Raw experiment records.

    Returns:
        Nested dict mapping method -> prompt_id -> ras float.
    """
    paired: dict[str, dict[str, float]] = defaultdict(dict)
    for rec in records:
        paired[rec["method"]][rec["prompt_id"]] = float(rec["ras"])
    return dict(paired)


def get_aligned_pairs(
    efa_map: dict[str, float],
    other_map: dict[str, float],
) -> tuple[np.ndarray, np.ndarray]:
    """Return aligned RAS arrays for prompts present in both methods.

    Args:
        efa_map: prompt_id -> ras for EFA.
        other_map: prompt_id -> ras for the comparison method.

    Returns:
        Tuple (efa_arr, other_arr) of the same length, prompt-aligned.
    """
    shared_ids = sorted(set(efa_map) & set(other_map))
    efa_arr = np.asarray([efa_map[pid] for pid in shared_ids], dtype=float)
    other_arr = np.asarray([other_map[pid] for pid in shared_ids], dtype=float)
    return efa_arr, other_arr


# ---------------------------------------------------------------------------
# Effect size: rank-biserial correlation
# ---------------------------------------------------------------------------


def rank_biserial_correlation(x: np.ndarray, y: np.ndarray) -> float:
    """Compute rank-biserial correlation r for a Wilcoxon signed-rank test.

    Uses the formula r = (W+ - W-) / (n*(n+1)/2) where W+/W- are the sums of
    positive/negative ranks of non-zero differences. Values in [-1, 1];
    positive means x > y on average (EFA scores higher than comparison method).

    Args:
        x: First sample (EFA).
        y: Second sample (comparison method), paired with x.

    Returns:
        Rank-biserial correlation coefficient.
    """
    diff = x - y
    nonzero = diff[diff != 0]
    n = len(nonzero)
    if n == 0:
        return 0.0

    abs_diff = np.abs(nonzero)
    # Ranks of absolute differences (average-rank tie handling)
    ranks = scipy_stats.rankdata(abs_diff)
    positive_rank_sum = float(ranks[nonzero > 0].sum())
    negative_rank_sum = float(ranks[nonzero < 0].sum())
    max_rank_sum = n * (n + 1) / 2
    return (positive_rank_sum - negative_rank_sum) / max_rank_sum


# ---------------------------------------------------------------------------
# Pairwise tests: EFA vs every other method
# ---------------------------------------------------------------------------


def pairwise_wilcoxon(
    records: list[dict[str, Any]],
    alpha: float = 0.05,
) -> dict[str, dict[str, Any]]:
    """Run pairwise Wilcoxon signed-rank tests: EFA vs each other method.

    Applies Bonferroni correction for the number of comparisons.

    Args:
        records: Raw experiment records.
        alpha: Family-wise significance level (default 0.05).

    Returns:
        Dict mapping method_name -> test result dict with keys:
            n_pairs, statistic, p_raw, p_corrected, significant,
            effect_size_r, warning (str or None).
    """
    paired = build_paired_ras(records)

    if "efa" not in paired:
        console.print(
            "[yellow]Warning: No 'efa' records found - skipping pairwise tests.[/yellow]"
        )
        return {}

    efa_map = paired["efa"]
    other_methods = [m for m in paired if m != "efa"]
    n_comparisons = len(other_methods)

    results: dict[str, dict[str, Any]] = {}

    for method in other_methods:
        other_map = paired[method]
        efa_arr, other_arr = get_aligned_pairs(efa_map, other_map)
        n = len(efa_arr)

        entry: dict[str, Any] = {
            "n_pairs": n,
            "statistic": None,
            "p_raw": None,
            "p_corrected": None,
            "significant": False,
            "effect_size_r": None,
            "warning": None,
        }

        if n < _MIN_N_WILCOXON:
            entry["warning"] = (
                f"N={n} < {_MIN_N_WILCOXON}: too few paired observations "
                "for a valid Wilcoxon test."
            )
            results[method] = entry
            continue

        # Check for zero variance (all differences are zero)
        diff = efa_arr - other_arr
        n_nonzero = int(np.sum(diff != 0))
        if n_nonzero == 0:
            entry["warning"] = "All paired differences are zero - no test possible."
            results[method] = entry
            continue

        if n_nonzero < _MIN_N_WILCOXON:
            entry["warning"] = (
                f"Only {n_nonzero} non-zero differences (need >={_MIN_N_WILCOXON}) - "
                "test result has very limited reliability."
            )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            stat, p_raw = scipy_stats.wilcoxon(efa_arr, other_arr, alternative="two-sided")

        p_corrected = min(1.0, p_raw * n_comparisons)  # Bonferroni
        r = rank_biserial_correlation(efa_arr, other_arr)

        entry["statistic"] = float(stat)
        entry["p_raw"] = float(p_raw)
        entry["p_corrected"] = float(p_corrected)
        entry["significant"] = bool(p_corrected < alpha)
        entry["effect_size_r"] = float(r)
        results[method] = entry

    return results


# ---------------------------------------------------------------------------
# Friedman test across all methods
# ---------------------------------------------------------------------------


def friedman_test(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Run Friedman test across all methods on RAS.

    Requires that all methods share the same set of prompts (blocks).

    Args:
        records: Raw experiment records.

    Returns:
        Dict with keys: statistic, p_value, significant, n_methods,
        n_blocks, warning (str or None).
    """
    paired = build_paired_ras(records)
    methods = list(paired.keys())

    result: dict[str, Any] = {
        "statistic": None,
        "p_value": None,
        "significant": False,
        "n_methods": len(methods),
        "n_blocks": 0,
        "warning": None,
    }

    if len(methods) < _MIN_N_FRIEDMAN:
        result["warning"] = (
            f"Only {len(methods)} method(s) found - "
            f"Friedman test requires >= {_MIN_N_FRIEDMAN}."
        )
        return result

    # Find prompt IDs present in ALL methods
    all_prompt_sets = [set(paired[m].keys()) for m in methods]
    shared_prompts = sorted(set.intersection(*all_prompt_sets))

    if len(shared_prompts) < 2:
        result["warning"] = (
            f"Only {len(shared_prompts)} shared prompt(s) across all methods - "
            "Friedman test requires >= 2."
        )
        return result

    result["n_blocks"] = len(shared_prompts)

    # Build block x treatment matrix (rows = prompts, cols = methods)
    matrix = np.array(
        [[paired[m][pid] for m in methods] for pid in shared_prompts],
        dtype=float,
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        stat, p_value = scipy_stats.friedmanchisquare(*matrix.T)

    result["statistic"] = float(stat)
    result["p_value"] = float(p_value)
    result["significant"] = bool(p_value < 0.05)
    return result


# ---------------------------------------------------------------------------
# Rich output: aggregate stats table
# ---------------------------------------------------------------------------


def _sort_key(method: str) -> int:
    try:
        return _METHOD_ORDER.index(method)
    except ValueError:
        # Handle dynamic names like "best-of-5" matching "best-of-n"
        for i, m in enumerate(_METHOD_ORDER):
            if method.startswith(m.rstrip("n")) and m.endswith("-n"):
                return i
        return 999


def print_aggregate_table(
    method_stats: dict[str, dict[str, Any]],
    n_bootstrap: int,
) -> None:
    """Print per-method aggregate statistics as a Rich table.

    Args:
        method_stats: Output of compute_method_stats().
        n_bootstrap: Bootstrap iterations used (shown in title).
    """
    table = Table(
        title=f"Per-Method Aggregate Statistics  (bootstrap CI: {n_bootstrap:,} iterations)",
        show_lines=True,
        header_style="bold cyan",
    )
    table.add_column("Method", style="bold", min_width=22)
    table.add_column("RAS mean +/- std", justify="center", min_width=16)
    table.add_column("RAS 95% CI", justify="center", min_width=18)
    table.add_column("APR %", justify="center", min_width=8)
    table.add_column("APR 95% CI", justify="center", min_width=16)
    table.add_column("ITC mean +/- std", justify="center", min_width=16)
    table.add_column("TTC mean +/- std", justify="center", min_width=18)
    table.add_column("N", justify="center", min_width=4)

    for method in sorted(method_stats.keys(), key=_sort_key):
        s = method_stats[method]
        display = _METHOD_DISPLAY.get(method, method)
        is_efa = method == "efa"
        row_style = "bold blue" if is_efa else ""

        ras_cell = f"{s['ras_mean']:.4f} +/- {s['ras_std']:.4f}"
        ci_cell = f"[{s['ras_ci_lo']:.4f}, {s['ras_ci_hi']:.4f}]"
        apr_cell = f"{s['apr_pct']:.1f}%"
        apr_ci_cell = f"[{s['apr_ci_lo']:.1f}%, {s['apr_ci_hi']:.1f}%]"
        itc_cell = f"{s['itc_mean']:.2f} +/- {s['itc_std']:.2f}"
        ttc_cell = f"{s['ttc_mean']:,.0f} +/- {s['ttc_std']:,.0f}"

        if is_efa:
            ras_cell = f"[bold]{ras_cell}[/bold]"
            apr_cell = f"[bold]{apr_cell}[/bold]"

        table.add_row(
            display,
            ras_cell,
            ci_cell,
            apr_cell,
            apr_ci_cell,
            itc_cell,
            ttc_cell,
            str(s["n"]),
            style=row_style,
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Rich output: pairwise test table
# ---------------------------------------------------------------------------


def print_pairwise_table(
    pairwise_results: dict[str, dict[str, Any]],
    alpha: float = 0.05,
) -> None:
    """Print pairwise Wilcoxon test results as a Rich table.

    Args:
        pairwise_results: Output of pairwise_wilcoxon().
        alpha: Significance threshold used.
    """
    n_comparisons = len(pairwise_results)
    table = Table(
        title=(
            "Pairwise Wilcoxon Signed-Rank Tests: EFA vs Each Method  "
            f"(Bonferroni-corrected x{n_comparisons}, two-sided, on RAS)"
        ),
        show_lines=True,
        header_style="bold magenta",
    )
    table.add_column("vs Method", style="bold", min_width=22)
    table.add_column("N pairs", justify="center")
    table.add_column("W stat", justify="center")
    table.add_column("p (raw)", justify="center")
    table.add_column(f"p (Bonferroni x{n_comparisons})", justify="center")
    table.add_column("Significant?", justify="center")
    table.add_column("Effect r", justify="center")
    table.add_column("Notes", min_width=30)

    for method in sorted(pairwise_results.keys(), key=_sort_key):
        res = pairwise_results[method]
        display = _METHOD_DISPLAY.get(method, method)
        warn = res.get("warning") or ""

        if res["p_raw"] is None:
            table.add_row(
                display,
                str(res["n_pairs"]),
                "n/a",
                "n/a",
                "n/a",
                "[yellow]n/a[/yellow]",
                "n/a",
                f"[yellow]{warn}[/yellow]",
            )
            continue

        sig = res["significant"]
        sig_text = Text("YES", style="bold red") if sig else Text("no", style="dim green")
        p_corr = res["p_corrected"]
        p_corr_str = f"{p_corr:.4f}" if p_corr >= 0.0001 else f"{p_corr:.2e}"
        p_raw_str = (
            f"{res['p_raw']:.4f}" if res["p_raw"] >= 0.0001 else f"{res['p_raw']:.2e}"
        )
        r = res["effect_size_r"]
        r_sign = "+" if r >= 0 else ""
        r_str = f"{r_sign}{r:.3f}"

        table.add_row(
            display,
            str(res["n_pairs"]),
            f"{res['statistic']:.1f}",
            p_raw_str,
            p_corr_str,
            sig_text,
            r_str,
            warn,
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Rich output: Friedman test panel
# ---------------------------------------------------------------------------


def print_friedman_result(friedman: dict[str, Any]) -> None:
    """Print Friedman test result as a Rich panel.

    Args:
        friedman: Output of friedman_test().
    """
    warn = friedman.get("warning")
    if warn:
        console.print(
            Panel(
                f"[yellow]Friedman test skipped:[/yellow] {warn}",
                title="Friedman Test (all methods)",
                border_style="yellow",
            )
        )
        return

    sig = friedman["significant"]
    verdict = (
        "[bold red]SIGNIFICANT[/bold red] - at least one method differs"
        if sig
        else "[green]Not significant[/green] - no detectable difference across methods"
    )
    body = (
        f"chi2 = {friedman['statistic']:.4f}   "
        f"p = {friedman['p_value']:.4f}   "
        f"({friedman['n_methods']} methods x {friedman['n_blocks']} prompts)\n\n"
        f"{verdict}"
    )
    console.print(
        Panel(body, title="Friedman Test (all methods, RAS)", border_style="cyan")
    )


# ---------------------------------------------------------------------------
# Verdict summary
# ---------------------------------------------------------------------------


def print_verdict(
    pairwise_results: dict[str, dict[str, Any]],
    friedman: dict[str, Any],
) -> None:
    """Print a plain-language verdict summarising the key findings.

    Args:
        pairwise_results: Output of pairwise_wilcoxon().
        friedman: Output of friedman_test().
    """
    sig_methods = [m for m, r in pairwise_results.items() if r.get("significant")]
    skipped = [m for m, r in pairwise_results.items() if r["p_raw"] is None]

    lines: list[str] = ["[bold underline]Verdict[/bold underline]", ""]

    if sig_methods:
        lines.append(
            "[bold red]Methods statistically different from EFA "
            "(p_Bonferroni < 0.05):[/bold red]"
        )
        for m in sorted(sig_methods, key=_sort_key):
            r = pairwise_results[m]
            eff = r["effect_size_r"]
            direction = (
                "EFA > " if eff > 0 else "EFA < "
            ) + _METHOD_DISPLAY.get(m, m)
            r_sign = "+" if eff >= 0 else ""
            lines.append(
                f"  * {_METHOD_DISPLAY.get(m, m)}: "
                f"p_corr={r['p_corrected']:.4f}, "
                f"r={r_sign}{eff:.3f}  ({direction})"
            )
    else:
        lines.append(
            "[green]No method is statistically significantly different from EFA "
            "at the Bonferroni-corrected alpha=0.05 level.[/green]"
        )

    if skipped:
        lines.append("")
        lines.append(
            "[yellow]Insufficient data for valid test (N too small):[/yellow] "
            + ", ".join(_METHOD_DISPLAY.get(m, m) for m in sorted(skipped, key=_sort_key))
        )

    if friedman["p_value"] is not None:
        lines.append("")
        f_sig_label = "significant" if friedman["significant"] else "not significant"
        f_verdict = (
            f"Friedman test is {f_sig_label} "
            f"(chi2={friedman['statistic']:.4f}, p={friedman['p_value']:.4f}) - "
            "methods differ overall."
            if friedman["significant"]
            else (
                f"Friedman test is {f_sig_label} "
                f"(chi2={friedman['statistic']:.4f}, p={friedman['p_value']:.4f})."
            )
        )
        if friedman["significant"]:
            lines.append(f"[bold]{f_verdict}[/bold]")
        else:
            lines.append(f_verdict)

    console.print(Panel("\n".join(lines), border_style="bold white"))


# ---------------------------------------------------------------------------
# Save output JSON
# ---------------------------------------------------------------------------


def save_output(
    output_path: Path,
    records_path: Path,
    method_stats: dict[str, dict[str, Any]],
    pairwise_results: dict[str, dict[str, Any]],
    friedman: dict[str, Any],
    n_bootstrap: int,
) -> None:
    """Save all analysis results to a JSON file.

    Args:
        output_path: Destination path for the output JSON.
        records_path: Path to the source results file (recorded for provenance).
        method_stats: Per-method aggregate stats.
        pairwise_results: Pairwise test results.
        friedman: Friedman test result.
        n_bootstrap: Bootstrap iterations used.
    """
    # Strip raw ras_values from serialised output to keep file small
    serialisable_stats = {
        method: {k: v for k, v in s.items() if k != "ras_values"}
        for method, s in method_stats.items()
    }

    payload: dict[str, Any] = {
        "source_file": str(records_path),
        "bootstrap_iterations": n_bootstrap,
        "method_stats": serialisable_stats,
        "pairwise_wilcoxon_efa_vs_others": pairwise_results,
        "friedman_test": friedman,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)

    console.print(f"[green]Analysis saved to: {output_path}[/green]")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(
        description="Statistical analysis of EFA experiment results - Karthick Raja M",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--results",
        type=Path,
        required=True,
        metavar="PATH",
        help="Path to the JSON results file (e.g. experiments/results/results_XXXXX.json)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Path to save analysis JSON. "
            "Defaults to <results_stem>_analysis.json in the same directory."
        ),
    )
    parser.add_argument(
        "--bootstrap-iters",
        type=int,
        default=10_000,
        metavar="N",
        help="Number of bootstrap iterations for RAS CI.",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        metavar="A",
        help="Family-wise significance level for Bonferroni correction.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Main entry point for the analysis script.

    Args:
        argv: CLI argument list (defaults to sys.argv[1:]).
    """
    args = parse_args(argv)

    results_path: Path = args.results.resolve()
    n_bootstrap: int = args.bootstrap_iters
    alpha: float = args.alpha

    # Resolve output path
    if args.out is not None:
        out_path = args.out.resolve()
    else:
        out_path = results_path.with_name(
            results_path.stem + "_analysis.json"
        )

    console.rule("[bold cyan]EFA Statistical Analysis[/bold cyan]")
    console.print(f"  Source  : {results_path}")
    console.print(f"  Output  : {out_path}")
    console.print(f"  Bootstrap iterations : {n_bootstrap:,}")
    console.print(f"  alpha (family-wise)  : {alpha}")
    console.print()

    # --- Load ---
    records = load_records(results_path)
    n_total = len(records)
    methods_present = sorted({r["method"] for r in records})
    console.print(
        f"[dim]Loaded {n_total} records across {len(methods_present)} method(s): "
        f"{', '.join(methods_present)}[/dim]"
    )
    console.print()

    # --- Per-method stats ---
    console.print("[bold]Computing per-method aggregate statistics...[/bold]")
    method_stats = compute_method_stats(records, n_bootstrap=n_bootstrap)
    print_aggregate_table(method_stats, n_bootstrap)
    console.print()

    # --- Pairwise Wilcoxon ---
    console.print(
        "[bold]Running pairwise Wilcoxon signed-rank tests (EFA vs others)...[/bold]"
    )
    pairwise_results = pairwise_wilcoxon(records, alpha=alpha)
    if pairwise_results:
        print_pairwise_table(pairwise_results, alpha=alpha)
    else:
        console.print("[yellow]No pairwise tests to display.[/yellow]")
    console.print()

    # --- Friedman ---
    console.print("[bold]Running Friedman test across all methods...[/bold]")
    friedman = friedman_test(records)
    print_friedman_result(friedman)
    console.print()

    # --- Verdict ---
    if pairwise_results:
        print_verdict(pairwise_results, friedman)
        console.print()

    # --- Save ---
    save_output(out_path, results_path, method_stats, pairwise_results, friedman, n_bootstrap)

    console.rule("[bold cyan]Done[/bold cyan]")


if __name__ == "__main__":
    main()
