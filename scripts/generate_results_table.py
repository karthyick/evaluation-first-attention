"""Generate results visualization for README — Karthick Raja M, 2026."""

import json
import sys
from collections import defaultdict
from pathlib import Path


def load_results(path: str) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def aggregate(records: list[dict]) -> dict:
    stats = defaultdict(lambda: {"ras_sum": 0, "apr_count": 0, "itc_sum": 0, "ttc_sum": 0, "count": 0})
    for r in records:
        m = stats[r["method"]]
        m["ras_sum"] += r["ras"]
        m["apr_count"] += int(r["apr"])
        m["itc_sum"] += r["itc"]
        m["ttc_sum"] += r["ttc"]
        m["count"] += 1
    return dict(stats)


def print_markdown_table(stats: dict) -> str:
    lines = []
    lines.append("| Method | RAS (mean) | APR (%) | ITC (mean) | TTC (mean) | N |")
    lines.append("|--------|:----------:|:-------:|:----------:|:----------:|:-:|")

    # Sort: EFA first, then baselines, then ablations
    order = ["efa", "single-pass", "self-refine", "rubric-then-score",
             "all-criteria-at-once", "uniform-reattention", "best-of-3",
             "efa-no-dyncriteria", "efa-no-cmpg", "efa-no-fwrl", "efa-no-iteration"]

    sorted_methods = sorted(stats.keys(), key=lambda x: order.index(x) if x in order else 99)

    for method in sorted_methods:
        s = stats[method]
        n = s["count"]
        ras = s["ras_sum"] / n
        apr = s["apr_count"] / n * 100
        itc = s["itc_sum"] / n
        ttc = s["ttc_sum"] / n

        # Highlight EFA and the FWRL ablation
        name = method
        if method == "efa":
            name = "**EFA (full)**"
        elif method == "efa-no-fwrl":
            name = "**EFA -FWRL**"

        apr_str = f"{apr:.0f}%"
        if apr < 100:
            apr_str = f"**{apr_str}**"

        lines.append(f"| {name} | {ras:.3f} | {apr_str} | {itc:.1f} | {ttc:,.0f} | {n} |")

    return "\n".join(lines)


if __name__ == "__main__":
    results_dir = Path("experiments/results")
    # Find latest results file
    files = sorted(results_dir.glob("results_*.json"))
    if not files:
        print("No results files found")
        sys.exit(1)

    latest = files[-1]
    print(f"Using: {latest}")
    records = load_results(str(latest))
    stats = aggregate(records)
    table = print_markdown_table(stats)
    print()
    print(table)
