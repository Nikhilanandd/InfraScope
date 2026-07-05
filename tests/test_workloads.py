from __future__ import annotations

import pytest
from infrascope.analyzers.workloads import WorkloadAnalyzer


class TestWorkloadAnalyzer:
    def setup_method(self):
        self.results = {
            "cpu": {"data": {"physical_cores": 8, "logical_cores": 16, "class": "High"}},
            "memory": {"data": {"total": 34359738368}},
            "gpu": {"data": {"gpus": [{"model": "RTX 4080", "vram_total_mb": 16384}],
                            "count": 1, "has_nvidia": True}},
            "storage": {"data": {"disks": [{"disk_type": "NVMe Gen4"}, {"disk_type": "NVMe Gen4"}]}},
        }
        self.analyzer = WorkloadAnalyzer(self.results)

    def test_general(self):
        rating = self.analyzer._general()
        assert rating in ("Excellent", "Good", "Acceptable", "Limited", "Not Recommended")

    def test_programming(self):
        rating = self.analyzer._programming()
        assert rating in ("Excellent", "Good", "Acceptable", "Limited", "Not Recommended")

    def test_docker(self):
        rating = self.analyzer._docker()
        assert rating in ("Excellent", "Good", "Acceptable", "Limited", "Not Recommended")

    def test_virtual_machines(self):
        rating = self.analyzer._virtual_machines()
        assert rating in ("Excellent", "Good", "Acceptable", "Limited", "Not Recommended")

    def test_machine_learning(self):
        rating = self.analyzer._machine_learning()
        assert rating in ("Excellent", "Good", "Acceptable", "Limited", "Not Recommended")

    def test_analyze_all(self):
        results = self.analyzer.analyze_all()
        assert isinstance(results, dict)
        assert len(results) > 10
        for name, rating in results.items():
            assert rating in ("Excellent", "Good", "Acceptable", "Limited", "Not Recommended"), f"{name}: {rating}"
