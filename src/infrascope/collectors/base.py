from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from rich.console import Console

console = Console()


class CollectorResult:
    def __init__(self, name: str, data: dict[str, Any], success: bool = True, error: str | None = None):
        self.name = name
        self.data = data
        self.success = success
        self.error = error
        self.timestamp = time.time()
        self.duration: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "data": self.data,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp,
            "duration": self.duration,
        }


class BaseCollector(ABC):
    name: ClassVar[str] = "base"
    description: ClassVar[str] = "Base collector"

    def __init__(self) -> None:
        self.deps_checked = False
        self.deps_available: list[str] = []

    @abstractmethod
    def collect(self) -> CollectorResult:
        ...

    def run(self) -> CollectorResult:
        start = time.time()
        try:
            result = self.collect()
            result.duration = time.time() - start
            return result
        except Exception as e:
            result = CollectorResult(self.name, {}, success=False, error=str(e))
            result.duration = time.time() - start
            return result


class CollectorRegistry:
    def __init__(self) -> None:
        self._collectors: dict[str, BaseCollector] = {}

    def register(self, collector: BaseCollector) -> None:
        self._collectors[collector.name] = collector

    def get(self, name: str) -> BaseCollector | None:
        return self._collectors.get(name)

    def run_all(self) -> dict[str, CollectorResult]:
        results: dict[str, CollectorResult] = {}
        for name, collector in self._collectors.items():
            try:
                results[name] = collector.run()
            except Exception as e:
                results[name] = CollectorResult(name, {}, success=False, error=str(e))
        return results

    def run_selected(self, names: list[str]) -> dict[str, CollectorResult]:
        results: dict[str, CollectorResult] = {}
        for name in names:
            collector = self._collectors.get(name)
            if collector:
                results[name] = collector.run()
            else:
                results[name] = CollectorResult(name, {}, success=False, error=f"Unknown collector: {name}")
        return results

    @property
    def available(self) -> list[str]:
        return list(self._collectors.keys())
