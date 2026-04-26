"""Generic plugin registry. Used by backends, evaluators, strategies, callbacks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    """Name -> factory map. Anyone can ``@registry.register("foo")`` a class.

    Used as the lookup mechanism for every plugin layer in Rubricon. Lets
    user code add custom backends/evaluators/strategies without touching
    the package.
    """

    def __init__(self, kind: str) -> None:
        self.kind = kind
        self._items: dict[str, Callable[..., T]] = {}

    def register(self, name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
        def decorate(factory: Callable[..., T]) -> Callable[..., T]:
            if name in self._items:
                raise ValueError(f"{self.kind} '{name}' already registered")
            self._items[name] = factory
            return factory
        return decorate

    def add(self, name: str, factory: Callable[..., T]) -> None:
        self._items[name] = factory

    def get(self, name: str) -> Callable[..., T]:
        if name not in self._items:
            available = ", ".join(sorted(self._items)) or "<none>"
            raise KeyError(
                f"{self.kind} '{name}' not registered. Available: {available}"
            )
        return self._items[name]

    def create(self, name: str, **params: Any) -> T:
        return self.get(name)(**params)

    def names(self) -> list[str]:
        return sorted(self._items)
