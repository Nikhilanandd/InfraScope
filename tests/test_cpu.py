from __future__ import annotations

import pytest
from infrascope.collectors.cpu import CPUCollector


class TestCPUCollector:
    def setup_method(self):
        self.collector = CPUCollector()

    def test_collector_name(self):
        assert self.collector.name == "cpu"

    def test_collector_returns_result(self):
        result = self.collector.run()
        assert result.name == "cpu"
        assert result.success
        assert result.data is not None

    def test_cpu_has_cores(self):
        result = self.collector.run()
        assert result.data.get("physical_cores", 0) > 0
        assert result.data.get("logical_cores", 0) > 0

    def test_cpu_has_frequency(self):
        result = self.collector.run()
        assert result.data.get("max_freq", 0) >= 0

    def test_cpu_has_vendor(self):
        result = self.collector.run()
        assert result.data.get("vendor", "") != ""

    def test_cpu_classification(self):
        result = self.collector.run()
        cpu_class = result.data.get("class", "")
        assert cpu_class in ("Entry", "Mid", "High", "Workstation", "Enterprise", "Server", "HPC")

    def test_cpu_instruction_sets(self):
        result = self.collector.run()
        isa = result.data.get("instruction_sets", {})
        assert isinstance(isa, dict)
        assert "SSE" in isa or "AVX" in isa

    def test_cpu_smt_detection(self):
        result = self.collector.run()
        cores = result.data.get("physical_cores", 0)
        threads = result.data.get("logical_cores", 0)
        smt = result.data.get("smt_enabled", False)
        assert isinstance(smt, bool)
        if threads > cores:
            assert smt, f"SMT should be enabled when threads ({threads}) > cores ({cores})"
