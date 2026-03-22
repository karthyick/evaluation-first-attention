"""LLM client abstraction using LiteLLM — Karthick Raja M, 2026."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import litellm

# Suppress litellm debug noise
litellm.suppress_debug_info = True


@dataclass
class TokenTracker:
    """Track token usage across calls."""

    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def add(self, usage: dict) -> None:
        self.prompt_tokens += usage.get("prompt_tokens", 0)
        self.completion_tokens += usage.get("completion_tokens", 0)

    def reset(self) -> None:
        self.prompt_tokens = 0
        self.completion_tokens = 0


@dataclass
class LLMClient:
    """Unified LLM client supporting any LiteLLM-compatible model."""

    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    tracker: TokenTracker = field(default_factory=TokenTracker)

    def complete(self, system: str, user: str) -> str:
        """Single completion call. Returns text response."""
        response = litellm.completion(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        if response.usage:
            self.tracker.add(response.usage.model_dump())
        return response.choices[0].message.content or ""

    def complete_json(self, system: str, user: str) -> dict | list:
        """Completion expecting JSON output. Parses and returns structured data."""
        response_text = self.complete(
            system=system + "\n\nRespond ONLY with valid JSON. No markdown, no explanation.",
            user=user,
        )
        # Strip markdown code fences if present
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last lines (``` markers)
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        return json.loads(text)

    def get_tokens_used(self) -> int:
        """Return total tokens used since last reset."""
        return self.tracker.total

    def reset_tracker(self) -> None:
        """Reset token counter."""
        self.tracker.reset()
