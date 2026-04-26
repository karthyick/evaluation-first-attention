"""Rubricon CLI.

Subcommands:
- ``rubricon run "prompt" [--config x.yaml]`` — single prompt
- ``rubricon eval --prompts file [--config x.yaml]`` — batch
- ``rubricon config show [--config x.yaml]`` — print effective config
- ``rubricon plugins`` — list everything registered

Uses Typer when installed; falls back to argparse so the CLI is always available.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from rubricon import (
    RubriconConfig,
    RubriconPipeline,
    backend_registry,
    callback_registry,
    convergence_registry,
    evaluator_registry,
    reattention_registry,
)


def _load_config(path: str | None, **overrides: Any) -> RubriconConfig:
    if path:
        return RubriconConfig.load(path, **overrides)
    return RubriconConfig.load(**overrides)


def _read_prompts(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if isinstance(data, list):
            return [str(p) for p in data]
        if isinstance(data, dict) and "prompts" in data:
            return [str(p) for p in data["prompts"]]
        raise ValueError(f"Cannot parse prompts from {path}")
    return [line for line in text.splitlines() if line.strip()]


def _cmd_run(args: Any) -> int:
    cfg = _load_config(args.config)
    if args.model:
        cfg = cfg.override(generator=cfg.generator.model_copy(update={"model": args.model}))
    pipe = RubriconPipeline(cfg)
    result = pipe.run(args.prompt)
    payload = {
        "method": result.method,
        "all_pass": result.all_pass,
        "rubric_adherence_score": result.rubric_adherence_score,
        "n_iterations": result.n_iterations,
        "total_tokens": result.total_tokens,
        "wall_seconds": result.wall_seconds,
        "stopped_reason": result.stopped_reason,
        "criteria": [c.name for c in result.criteria],
        "final_scores": result.final_scores,
        "response": result.response,
    }
    print(json.dumps(payload, indent=2, default=str))
    return 0


def _cmd_eval(args: Any) -> int:
    cfg = _load_config(args.config)
    pipe = RubriconPipeline(cfg)
    prompts = _read_prompts(Path(args.prompts))
    out_path = Path(args.output) if args.output else None
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    f = out_path.open("w", encoding="utf-8") if out_path else None
    try:
        for i, prompt in enumerate(prompts, 1):
            result = pipe.run(prompt)
            rec = {
                "idx": i,
                "prompt": prompt,
                "method": result.method,
                "ras": result.rubric_adherence_score,
                "all_pass": result.all_pass,
                "iters": result.n_iterations,
                "tokens": result.total_tokens,
                "stopped_reason": result.stopped_reason,
            }
            line = json.dumps(rec, default=str)
            if f:
                f.write(line + "\n")
            print(line)
    finally:
        if f:
            f.close()
    return 0


def _cmd_config_show(args: Any) -> int:
    cfg = _load_config(args.config)
    print(json.dumps(cfg.model_dump(mode="json"), indent=2, default=str))
    return 0


def _cmd_plugins(args: Any) -> int:
    print(json.dumps({
        "backends": backend_registry.names(),
        "evaluators": evaluator_registry.names(),
        "reattention": reattention_registry.names(),
        "convergence": convergence_registry.names(),
        "callbacks": callback_registry.names(),
    }, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="rubricon", description="Rubricon CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run a single prompt")
    p_run.add_argument("prompt")
    p_run.add_argument("--config", "-c", default=None)
    p_run.add_argument("--model", default=None)
    p_run.set_defaults(func=_cmd_run)

    p_eval = sub.add_parser("eval", help="Run a batch of prompts")
    p_eval.add_argument("--prompts", "-p", required=True, help="Path to .txt or .json prompts file")
    p_eval.add_argument("--config", "-c", default=None)
    p_eval.add_argument("--output", "-o", default=None, help="Path to write JSONL results")
    p_eval.set_defaults(func=_cmd_eval)

    p_cfg = sub.add_parser("config", help="Inspect effective configuration")
    cfg_sub = p_cfg.add_subparsers(dest="cfg_cmd", required=True)
    p_cfg_show = cfg_sub.add_parser("show")
    p_cfg_show.add_argument("--config", "-c", default=None)
    p_cfg_show.set_defaults(func=_cmd_config_show)

    p_plugins = sub.add_parser("plugins", help="List registered plugins")
    p_plugins.set_defaults(func=_cmd_plugins)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
