"""LLM backend protocol + registry.

Anyone can plug in a new backend (vLLM, Bedrock, custom HTTP, mocks for tests)
by registering a factory under a name. The pipeline only ever talks to the
``LLMBackend`` protocol.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from rubricon.config import BackendConfig, RetryConfig
from rubricon.registry import Registry


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def add(self, prompt: int, completion: int) -> None:
        self.prompt_tokens += prompt
        self.completion_tokens += completion


@dataclass
class CompletionRequest:
    system: str
    user: str
    response_format: str = "text"  # "text" | "json"


@dataclass
class CompletionResponse:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw: Any = None


@runtime_checkable
class LLMBackend(Protocol):
    """All backends implement this. Sync-first; async wrapper lives in the pipeline."""

    name: str
    usage: TokenUsage

    def complete(self, req: CompletionRequest) -> CompletionResponse: ...


backend_registry: Registry[LLMBackend] = Registry("backend")


# ---------------- LiteLLM backend ----------------

class LiteLLMBackend:
    """LiteLLM-powered backend. Works with OpenAI, Anthropic, Groq, Ollama, etc."""

    def __init__(
        self,
        config: BackendConfig,
        retry: RetryConfig | None = None,
    ) -> None:
        import litellm  # local import keeps cold-start cost off non-LLM paths

        litellm.suppress_debug_info = True
        self._litellm = litellm
        self.name = "litellm"
        self.config = config
        self.retry = retry or RetryConfig()
        self.usage = TokenUsage()
        self._call_count = 0

    @property
    def _is_ollama(self) -> bool:
        return self.config.model.startswith("ollama/")

    def complete(self, req: CompletionRequest) -> CompletionResponse:
        if self.config.call_delay > 0 and self._call_count > 0:
            time.sleep(self.config.call_delay)
        self._call_count += 1

        kwargs: dict[str, Any] = {**self.config.extra}
        if self._is_ollama:
            kwargs.setdefault("think", False)
        if self.config.api_base:
            kwargs["api_base"] = self.config.api_base
        if self.config.api_key:
            kwargs["api_key"] = self.config.api_key
        if self.config.seed is not None:
            kwargs["seed"] = self.config.seed

        last_err: Exception | None = None
        for attempt in range(self.retry.max_attempts):
            try:
                resp = self._litellm.completion(
                    model=self.config.model,
                    messages=[
                        {"role": "system", "content": req.system},
                        {"role": "user", "content": req.user},
                    ],
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    **kwargs,
                )
                text = resp.choices[0].message.content or ""
                usage = resp.usage.model_dump() if resp.usage else {}
                p = int(usage.get("prompt_tokens", 0))
                c = int(usage.get("completion_tokens", 0))
                self.usage.add(p, c)
                return CompletionResponse(text=text, prompt_tokens=p, completion_tokens=c, raw=resp)
            except Exception as exc:
                last_err = exc
                if not self._should_retry(exc) or attempt == self.retry.max_attempts - 1:
                    raise
                time.sleep(self._delay(attempt))
        assert last_err is not None
        raise last_err

    def _should_retry(self, exc: Exception) -> bool:
        return type(exc).__name__ in set(self.retry.retry_on)

    def _delay(self, attempt: int) -> float:
        base = self.retry.base_delay_seconds
        if self.retry.backoff == "constant":
            return base
        if self.retry.backoff == "linear":
            return base * (attempt + 1)
        return base * (2 ** attempt)


@backend_registry.register("litellm")
def _make_litellm(**params: Any) -> LiteLLMBackend:
    cfg = params.pop("config", None) or BackendConfig(**params)
    retry = params.pop("retry", None)
    return LiteLLMBackend(cfg, retry)


# ---------------- Mock backend (for tests) ----------------

@dataclass
class MockBackend:
    """Deterministic backend for tests. Pre-program responses by request signature."""

    name: str = "mock"
    usage: TokenUsage = field(default_factory=TokenUsage)
    responses: list[str] = field(default_factory=list)
    _idx: int = 0

    def complete(self, req: CompletionRequest) -> CompletionResponse:
        if not self.responses:
            text = json.dumps([{"name": "Default", "definition": "x", "rubric": {str(i): "ok" for i in range(1, 6)}}])
        else:
            text = self.responses[self._idx % len(self.responses)]
            self._idx += 1
        # Approximate token cost from string length so budget tests are meaningful
        p = max(1, len(req.system + req.user) // 4)
        c = max(1, len(text) // 4)
        self.usage.add(p, c)
        return CompletionResponse(text=text, prompt_tokens=p, completion_tokens=c)


@backend_registry.register("mock")
def _make_mock(**params: Any) -> MockBackend:
    return MockBackend(responses=list(params.get("responses", [])))


# ---------------- JSON helpers ----------------

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _repair_json(raw: str) -> str:
    raw = _CONTROL.sub("", raw)
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    if '"' not in raw and "'" in raw:
        raw = raw.replace("'", '"')
    return raw


def extract_json(text: str) -> Any:
    """Pull JSON out of an LLM response that may contain prose / fences / <think>."""
    raw = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    if "```" in raw:
        raw = "\n".join(line for line in raw.split("\n") if not line.strip().startswith("```")).strip()
    raw = _repair_json(raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Locate outermost bracket pair and try again.
    first = next((i for i, ch in enumerate(raw) if ch in "[{"), -1)
    if first < 0:
        raise ValueError(f"No JSON found in model output: {raw[:200]}...")
    close = "]" if raw[first] == "[" else "}"
    last = raw.rfind(close)
    if last > first:
        try:
            return json.loads(_repair_json(raw[first:last + 1]))
        except json.JSONDecodeError:
            pass

    # Last resort: collect every well-formed object inside an array.
    if raw[first] == "[":
        objects: list[Any] = []
        depth = 0
        start = -1
        for i in range(first + 1, len(raw)):
            ch = raw[i]
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}" and depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    try:
                        objects.append(json.loads(_repair_json(raw[start:i + 1])))
                    except json.JSONDecodeError:
                        pass
                    start = -1
        if objects:
            return objects
    raise ValueError(f"Could not parse JSON: {raw[:200]}...")


def complete_json(backend: LLMBackend, system: str, user: str) -> Any:
    """Wrapper that nudges JSON-only output and parses defensively."""
    sys_msg = system + "\n\nRespond ONLY with valid JSON. No markdown, no explanation, no thinking."
    resp = backend.complete(CompletionRequest(system=sys_msg, user=user, response_format="json"))
    return extract_json(resp.text)


def make_backend(config: BackendConfig, retry: RetryConfig | None = None) -> LLMBackend:
    """Resolve a backend by name from the registry."""
    return backend_registry.create(config.backend, config=config, retry=retry)
