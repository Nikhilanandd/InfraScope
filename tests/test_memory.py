from __future__ import annotations

import pytest
from infrascope.collectors.memory import MemoryCollector


class TestMemoryCollector:
    def setup_method(self):
        self.collector = MemoryCollector()

    def test_collector_name(self):
        assert self.collector.name == "memory"

    def test_collector_returns_result(self):
        result = self.collector.run()
        assert result.name == "memory"
        assert result.success

    def test_memory_total(self):
        result = self.collector.run()
        assert result.data.get("total", 0) > 0

    def test_memory_available(self):
        result = self.collector.run()
        assert result.data.get("available", 0) > 0

    def test_memory_swap(self):
        result = self.collector.run()
        assert "swap_total" in result.data
        assert "swap_used" in result.data

    def test_memory_channels(self):
        result = self.collector.run()
        channels = result.data.get("channels", {})
        assert "mode" in channels
        assert channels["mode"] in ("Single", "Dual", "Triple", "Quad", "unknown")

    def test_hugepages(self):
        result = self.collector.run()
        hp = result.data.get("hugepages", {})
        assert "enabled" in hp
        assert "total" in hp

    def test_numa_memory(self):
        result = self.collector.run()
        numa = result.data.get("numa_info", [])
        assert isinstance(numa, list)
