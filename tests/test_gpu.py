from __future__ import annotations

import pytest
from infrascope.collectors.gpu import GPUCollector


class TestGPUCollector:
    def setup_method(self):
        self.collector = GPUCollector()

    def test_collector_name(self):
        assert self.collector.name == "gpu"

    def test_collector_returns_result(self):
        result = self.collector.run()
        assert result.name == "gpu"
        assert result.success

    def test_gpu_count(self):
        result = self.collector.run()
        assert "count" in result.data
        assert isinstance(result.data.get("count", 0), int)

    def test_gpu_list(self):
        result = self.collector.run()
        assert "gpus" in result.data
        assert isinstance(result.data.get("gpus", []), list)
