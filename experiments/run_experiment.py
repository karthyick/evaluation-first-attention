"""Experiment runner for EFA evaluation — Karthick Raja M, 2026.

Usage:
    python experiments/run_experiment.py --config configs/default.yaml
    python experiments/run_experiment.py --method efa --prompts sample
    python experiments/run_experiment.py --method single-pass --prompts mt-bench --max-prompts 20
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from efa.baselines import BASELINES
from efa.models import ExperimentRecord, PipelineResult
from efa.pipeline import EFAPipeline

console = Console()

# Method registry
ABLATION_CONFIGS = {
    "efa-no-dyncriteria": {"dynamic_criteria": False},
    "efa-no-cmpg": {"progressive_masking": False},
    "efa-no-fwrl": {"failure_weighting": False},
    "efa-no-iteration": {"iterative": False},
}


def load_prompts(source: str, max_prompts: int = 50) -> list[dict]:
    """Load prompts from a benchmark source."""
    prompts_dir = Path(__file__).parent / "prompts"

    if source == "sample":
        path = prompts_dir / "sample_prompts.json"
    elif source == "mt-bench":
        path = prompts_dir / "mt_bench_prompts.json"
    elif source == "alpaca-eval":
        path = prompts_dir / "alpaca_eval_prompts.json"
    elif source == "arena-hard":
        path = prompts_dir / "arena_hard_prompts.json"
    else:
        path = Path(source)

    if not path.exists():
        console.print(f"[yellow]Prompt file not found: {path}. Using sample prompts.[/yellow]")
        path = prompts_dir / "sample_prompts.json"

    with open(path) as f:
        prompts = json.load(f)

    return prompts[:max_prompts]


def run_efa(
    prompt: str,
    config: dict,
    ablation: str | None = None,
) -> PipelineResult:
    """Run EFA pipeline (full or ablation variant)."""
    kwargs = {
        "model": config.get("generator_model", "gpt-4o"),
        "evaluator_model": config.get("evaluator_model"),
        "n_criteria": config.get("n_criteria", 5),
        "threshold": config.get("threshold", 0.6),
        "max_iterations": config.get("max_iterations", 3),
        "alpha": config.get("alpha", 2.0),
        "epsilon": config.get("epsilon", 0.1),
        "batched_eval": config.get("batched_eval", False),
        "gen_call_delay": config.get("gen_call_delay", 0.0),
        "eval_call_delay": config.get("eval_call_delay", 0.0),
        "gen_api_base": config.get("gen_api_base"),
        "gen_api_key": config.get("gen_api_key"),
        "eval_api_base": config.get("eval_api_base"),
        "eval_api_key": config.get("eval_api_key"),
        "seed": config.get("seed"),
    }

    if ablation and ablation in ABLATION_CONFIGS:
        kwargs.update(ABLATION_CONFIGS[ablation])

    pipeline = EFAPipeline(**kwargs)
    return pipeline.run(prompt)


def run_baseline(
    name: str,
    prompt: str,
    config: dict,
) -> PipelineResult:
    """Run a baseline method."""
    kwargs = {
        "prompt": prompt,
        "model": config.get("generator_model", "gpt-4o"),
        "evaluator_model": config.get("evaluator_model"),
        "n_criteria": config.get("n_criteria", 5),
        "gen_api_base": config.get("gen_api_base"),
        "gen_api_key": config.get("gen_api_key"),
        "eval_api_base": config.get("eval_api_base"),
        "eval_api_key": config.get("eval_api_key"),
    }

    if name == "self-refine":
        kwargs["max_iterations"] = config.get("max_iterations", 3)
    elif name == "best-of-n":
        kwargs["n_samples"] = config.get("best_of_n_samples", 5)

    return BASELINES[name](**kwargs)


def result_to_record(
    prompt_data: dict, result: PipelineResult, config: dict
) -> ExperimentRecord:
    """Convert PipelineResult to ExperimentRecord."""
    return ExperimentRecord(
        prompt_id=prompt_data.get("id", "unknown"),
        prompt=result.prompt,
        method=result.method,
        ras=result.rubric_adherence_score,
        apr=result.all_pass,
        itc=result.n_iterations,
        ttc=result.total_tokens,
        response=result.response,
        generator_model=config.get("generator_model", "unknown"),
        evaluator_model=config.get("evaluator_model", "unknown"),
        criteria_names=[c.name for c in result.criteria],
        per_criterion_scores=result.final_scores,
    )


def print_results_table(records: list[ExperimentRecord]) -> None:
    """Print summary results as a rich table."""
    # Aggregate by method
    from collections import defaultdict
    method_stats: dict[str, dict] = defaultdict(lambda: {
        "ras_sum": 0.0, "apr_count": 0, "itc_sum": 0, "ttc_sum": 0, "count": 0,
    })

    for r in records:
        m = method_stats[r.method]
        m["ras_sum"] += r.ras
        m["apr_count"] += int(r.apr)
        m["itc_sum"] += r.itc
        m["ttc_sum"] += r.ttc
        m["count"] += 1

    table = Table(title="EFA Experiment Results", show_lines=True)
    table.add_column("Method", style="bold cyan")
    table.add_column("RAS (mean)", justify="center")
    table.add_column("APR (%)", justify="center")
    table.add_column("ITC (mean)", justify="center")
    table.add_column("TTC (mean)", justify="center")
    table.add_column("N", justify="center")

    for method, stats in sorted(method_stats.items()):
        n = stats["count"]
        table.add_row(
            method,
            f"{stats['ras_sum'] / n:.3f}",
            f"{stats['apr_count'] / n * 100:.1f}%",
            f"{stats['itc_sum'] / n:.1f}",
            f"{stats['ttc_sum'] / n:,.0f}",
            str(n),
        )

    console.print(table)


def resolve_env_vars(config: dict) -> dict:
    """Resolve ${ENV_VAR} references in config values."""
    import os
    resolved = {}
    for k, v in config.items():
        if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
            env_name = v[2:-1]
            resolved[k] = os.environ.get(env_name, "")
        else:
            resolved[k] = v
    return resolved


def main():
    # Load .env if present
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description="EFA Experiment Runner — Karthick Raja M")
    parser.add_argument("--config", type=str, default="configs/default.yaml")
    parser.add_argument("--method", type=str, help="Run single method (efa, single-pass, etc.)")
    parser.add_argument("--prompts", type=str, help="Prompt source override")
    parser.add_argument("--max-prompts", type=int, help="Max prompts override")
    args = parser.parse_args()

    # Load config
    config_path = Path(args.config)
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        console.print(f"[yellow]Config not found: {config_path}. Using defaults.[/yellow]")
        config = {}

    # Resolve ${ENV_VAR} references in config
    config = resolve_env_vars(config)

    # Overrides
    prompt_source = args.prompts or config.get("prompt_source", "sample")
    max_prompts = args.max_prompts or config.get("max_prompts", 50)

    # Load prompts
    prompts = load_prompts(prompt_source, max_prompts)
    console.print(f"[green]Loaded {len(prompts)} prompts from '{prompt_source}'[/green]")

    # Determine methods to run
    methods: list[str] = []
    if args.method:
        methods = [args.method]
    else:
        methods = ["efa"]
        methods += config.get("baselines", [])
        methods += config.get("ablations", [])

    console.print(f"[green]Methods to run: {methods}[/green]")

    # Run experiments
    all_records: list[ExperimentRecord] = []
    results_dir = Path(config.get("results_dir", "experiments/results"))
    results_dir.mkdir(parents=True, exist_ok=True)
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = results_dir / f"results_{run_timestamp}.json"

    def _save_incremental() -> None:
        """Save results after each method to prevent data loss."""
        with open(results_path, "w") as _f:
            json.dump([vars(r) for r in all_records], _f, indent=2, default=str)

    for method in methods:
        console.print(f"\n[bold blue]--- Running: {method} ---[/bold blue]")

        for i, prompt_data in enumerate(prompts):
            prompt_text = prompt_data["prompt"]
            console.print(f"  [{i+1}/{len(prompts)}] {prompt_text[:60]}...")

            start = time.time()

            try:
                if method == "efa":
                    result = run_efa(prompt_text, config)
                elif method in ABLATION_CONFIGS:
                    result = run_efa(prompt_text, config, ablation=method)
                elif method in BASELINES:
                    result = run_baseline(method, prompt_text, config)
                else:
                    console.print(f"  [red]Unknown method: {method}[/red]")
                    continue

                elapsed = time.time() - start
                record = result_to_record(prompt_data, result, config)
                all_records.append(record)

                console.print(
                    f"    RAS={record.ras:.3f} APR={'PASS' if record.apr else 'FAIL'} "
                    f"ITC={record.itc} TTC={record.ttc:,} ({elapsed:.1f}s)"
                )

            except Exception as e:
                console.print(f"  [red]ERROR: {e}[/red]")
                # Record failure so it appears in results
                all_records.append(ExperimentRecord(
                    prompt_id=prompt_data.get("id", "unknown"),
                    prompt=prompt_text,
                    method=method,
                    ras=0.0,
                    apr=False,
                    itc=0,
                    ttc=0,
                    response=f"ERROR: {e}",
                ))
                continue

        # Save after each method completes (incremental)
        _save_incremental()
        console.print(f"  [dim]Saved {len(all_records)} records to {results_path}[/dim]")

    console.print(f"\n[green]Results saved to: {results_path}[/green]")

    # Print summary table
    print_results_table(all_records)


if __name__ == "__main__":
    main()
