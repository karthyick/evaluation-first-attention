"""Callback bus for pipeline observability.

Multiple callbacks compose. Built-ins: console (rich), jsonl logging, no-op.
Users register their own with ``callback_registry.register("wandb")(MyCb)``.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from rubricon.models import Criterion, EvaluationResult, IterationTrace, PipelineResult
from rubricon.registry import Registry


@runtime_checkable
class PipelineCallback(Protocol):
    """All hooks default to no-op via the base class below; override what you need."""

    def on_run_start(self, *, prompt: str, config: Any) -> None: ...
    def on_criteria_generated(self, *, criteria: list[Criterion]) -> None: ...
    def on_iteration_start(self, *, iteration: int) -> None: ...
    def on_draft(self, *, iteration: int, sub_step: int, draft: str) -> None: ...
    def on_evaluation(self, *, iteration: int, evaluation: EvaluationResult) -> None: ...
    def on_iteration_end(self, *, trace: IterationTrace) -> None: ...
    def on_run_end(self, *, result: PipelineResult) -> None: ...


class BaseCallback:
    """Convenience base — all hooks no-op so subclasses override only what they need."""

    def on_run_start(self, **_: Any) -> None: ...
    def on_criteria_generated(self, **_: Any) -> None: ...
    def on_iteration_start(self, **_: Any) -> None: ...
    def on_draft(self, **_: Any) -> None: ...
    def on_evaluation(self, **_: Any) -> None: ...
    def on_iteration_end(self, **_: Any) -> None: ...
    def on_run_end(self, **_: Any) -> None: ...


callback_registry: Registry[PipelineCallback] = Registry("callback")


@dataclass
class CallbackBus:
    """Fan out events to every registered callback. Errors in one don't stop others."""

    callbacks: list[PipelineCallback] = field(default_factory=list)

    def emit(self, event: str, **kwargs: Any) -> None:
        for cb in self.callbacks:
            handler = getattr(cb, event, None)
            if handler is None:
                continue
            try:
                handler(**kwargs)
            except Exception:
                # Telemetry must never crash the pipeline.
                continue


# ---------------- Built-ins ----------------

class ConsoleCallback(BaseCallback):
    """Pretty-prints iteration progress with rich.

    Falls back to plain ``print`` when ``rich`` isn't installed.
    """

    def __init__(self, verbose: bool = True) -> None:
        self.verbose = verbose
        try:
            from rich.console import Console
            self.console: Any = Console()
            self._rich = True
        except ImportError:
            self.console = None
            self._rich = False
        self._t0: float = 0.0

    def _print(self, msg: str) -> None:
        if self._rich:
            self.console.print(msg)
        else:
            print(msg)

    def on_run_start(self, *, prompt: str, **_: Any) -> None:
        self._t0 = time.time()
        if self.verbose:
            preview = prompt[:80] + ("..." if len(prompt) > 80 else "")
            self._print(f"[bold cyan]rubricon[/bold cyan] start: {preview}" if self._rich else f"rubricon start: {preview}")

    def on_criteria_generated(self, *, criteria: list[Criterion], **_: Any) -> None:
        if not self.verbose:
            return
        names = ", ".join(c.name for c in criteria)
        self._print(f"  criteria ({len(criteria)}): {names}")

    def on_iteration_end(self, *, trace: IterationTrace, **_: Any) -> None:
        if not self.verbose:
            return
        scores = ", ".join(f"{s:.2f}" for s in trace.evaluation.scores)
        self._print(f"  iter {trace.iteration}: scores=[{scores}] tokens={trace.tokens_used}")

    def on_run_end(self, *, result: PipelineResult, **_: Any) -> None:
        if not self.verbose:
            return
        elapsed = time.time() - self._t0
        status = "PASS" if result.all_pass else "FAIL"
        self._print(
            f"  done [{status}] iters={result.n_iterations} tokens={result.total_tokens} "
            f"ras={result.rubric_adherence_score:.3f} elapsed={elapsed:.1f}s"
        )


class JSONLCallback(BaseCallback):
    """Append every event to a JSON-lines file for offline analysis."""

    def __init__(self, path: str | Path = "rubricon.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, event: str, payload: dict[str, Any]) -> None:
        rec = {"event": event, "ts": time.time(), **payload}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")

    def on_run_start(self, *, prompt: str, **_: Any) -> None:
        self._write("run_start", {"prompt": prompt})

    def on_criteria_generated(self, *, criteria: list[Criterion], **_: Any) -> None:
        self._write("criteria", {"criteria": [c.name for c in criteria]})

    def on_iteration_end(self, *, trace: IterationTrace, **_: Any) -> None:
        self._write(
            "iteration",
            {
                "iter": trace.iteration,
                "scores": trace.evaluation.scores,
                "tokens": trace.tokens_used,
            },
        )

    def on_run_end(self, *, result: PipelineResult, **_: Any) -> None:
        self._write(
            "run_end",
            {
                "tokens": result.total_tokens,
                "iters": result.n_iterations,
                "ras": result.rubric_adherence_score,
                "all_pass": result.all_pass,
            },
        )


callback_registry.add("console", lambda **p: ConsoleCallback(verbose=p.get("verbose", True)))
callback_registry.add("jsonl", lambda **p: JSONLCallback(path=p.get("path", "rubricon.jsonl")))
callback_registry.add("none", lambda **_: BaseCallback())
