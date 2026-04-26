"""Hard guardrails on tokens, cost, wall time, and iteration count.

The pipeline asks ``BudgetTracker.exhausted()`` between phases. When triggered,
the run exits gracefully with ``stopped_reason`` set on the result (or raises if
``on_exceed='raise'``).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from rubricon.config import BudgetConfig


class BudgetExceeded(RuntimeError):
    """Raised when ``on_exceed='raise'`` and any limit is hit."""


@dataclass
class BudgetTracker:
    config: BudgetConfig
    start_time: float = field(default_factory=time.time)
    tokens_used: int = 0
    cost_usd: float = 0.0
    iterations: int = 0

    def add_tokens(self, n: int) -> None:
        self.tokens_used += n

    def add_cost(self, c: float) -> None:
        self.cost_usd += c

    def tick_iteration(self) -> None:
        self.iterations += 1

    @property
    def wall_seconds(self) -> float:
        return time.time() - self.start_time

    def exhausted(self) -> str | None:
        c = self.config
        if c.max_tokens is not None and self.tokens_used >= c.max_tokens:
            return f"max_tokens({c.max_tokens}) reached"
        if c.max_cost_usd is not None and self.cost_usd >= c.max_cost_usd:
            return f"max_cost_usd({c.max_cost_usd}) reached"
        if c.max_wall_seconds is not None and self.wall_seconds >= c.max_wall_seconds:
            return f"max_wall_seconds({c.max_wall_seconds}) reached"
        if c.max_iterations is not None and self.iterations >= c.max_iterations:
            return f"max_iterations({c.max_iterations}) reached"
        return None

    def enforce(self) -> str | None:
        reason = self.exhausted()
        if reason and self.config.on_exceed == "raise":
            raise BudgetExceeded(reason)
        return reason
