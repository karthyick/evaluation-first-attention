"""LLM client abstraction using LiteLLM — Karthick Raja M, 2026."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

import litellm

# Suppress litellm debug noise
litellm.suppress_debug_info = True

import re

MAX_RETRIES = 3
RETRY_BASE_DELAY = 15  # seconds


def _repair_json(raw: str) -> str:
    """Fix common LLM JSON issues: trailing commas, single quotes, control chars."""
    # Remove control characters except newline/tab
    raw = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", raw)
    # Fix trailing commas before } or ]
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    # Fix single quotes used as string delimiters (naive but covers common cases)
    # Only if no double quotes are present (avoids breaking valid JSON)
    if '"' not in raw and "'" in raw:
        raw = raw.replace("'", '"')
    return raw


def _extract_json(text: str) -> dict | list:
    """Robustly extract JSON from LLM output. Handles thinking tags, code fences, preamble."""
    raw = text.strip()

    # Strip <think>...</think> blocks (Qwen, DeepSeek)
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    # Strip markdown code fences
    if "```" in raw:
        lines = raw.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw = "\n".join(lines).strip()

    # Apply repairs
    raw = _repair_json(raw)

    # Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Find first [ or { and last matching ] or }
    first_bracket = -1
    bracket_char = None
    for i, ch in enumerate(raw):
        if ch in "[{":
            first_bracket = i
            bracket_char = ch
            break

    if first_bracket < 0:
        raise ValueError(f"No JSON found in LLM output: {raw[:200]}...")

    close_char = "]" if bracket_char == "[" else "}"

    # Try from the outermost brackets
    last_bracket = raw.rfind(close_char)
    if last_bracket > first_bracket:
        candidate = _repair_json(raw[first_bracket : last_bracket + 1])
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # For arrays: find all complete objects and build a valid array
    if bracket_char == "[":
        objects = []
        # Find each {...} in the text
        depth = 0
        obj_start = -1
        for i in range(first_bracket + 1, len(raw)):
            if raw[i] == "{" and depth == 0:
                obj_start = i
                depth = 1
            elif raw[i] == "{":
                depth += 1
            elif raw[i] == "}" and depth > 0:
                depth -= 1
                if depth == 0 and obj_start >= 0:
                    obj_str = _repair_json(raw[obj_start : i + 1])
                    try:
                        obj = json.loads(obj_str)
                        objects.append(obj)
                    except json.JSONDecodeError:
                        pass
                    obj_start = -1

        if objects:
            return objects

    raise ValueError(f"Could not extract JSON from LLM output: {raw[:200]}...")


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
    seed: int | None = None  # Reproducibility seed (passed to litellm.completion)
    call_delay: float = 0.0  # Seconds to wait between calls (for rate-limited APIs)
    api_base: str | None = None  # Custom API base URL (for OpenAI-compatible providers)
    api_key: str | None = None  # Custom API key (for OpenAI-compatible providers)
    tracker: TokenTracker = field(default_factory=TokenTracker)
    _call_count: int = field(default=0, init=False, repr=False)

    @property
    def _is_ollama(self) -> bool:
        return self.model.startswith("ollama/")

    def complete(self, system: str, user: str) -> str:
        """Single completion call with retry on rate limits."""
        # Rate limit pacing
        if self.call_delay > 0 and self._call_count > 0:
            time.sleep(self.call_delay)
        self._call_count += 1

        extra_kwargs: dict = {}
        if self._is_ollama:
            extra_kwargs["think"] = False  # Disable thinking for local models
        if self.api_base:
            extra_kwargs["api_base"] = self.api_base
        if self.api_key:
            extra_kwargs["api_key"] = self.api_key
        if self.seed is not None:
            extra_kwargs["seed"] = self.seed

        for attempt in range(MAX_RETRIES):
            try:
                response = litellm.completion(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    **extra_kwargs,
                )
                if response.usage:
                    self.tracker.add(response.usage.model_dump())
                return response.choices[0].message.content or ""
            except litellm.RateLimitError:
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (attempt + 1)
                    print(f"  [rate limit] Retrying in {delay}s... ({attempt + 1}/{MAX_RETRIES})")
                    time.sleep(delay)
                else:
                    raise

    def complete_json(self, system: str, user: str) -> dict | list:
        """Completion expecting JSON output. Handles local model quirks."""
        response_text = self.complete(
            system=system + "\n\nRespond ONLY with valid JSON. No markdown, no explanation, no thinking.",
            user=user,
        )
        return _extract_json(response_text)

    def get_tokens_used(self) -> int:
        """Return total tokens used since last reset."""
        return self.tracker.total

    def reset_tracker(self) -> None:
        """Reset token counter."""
        self.tracker.reset()
