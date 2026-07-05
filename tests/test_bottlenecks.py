from __future__ import annotations

import pytest
from infrascope.analyzers.bottlenecks import BottleneckDetector


class TestBottleneckDetector:
    def setup_method(self):
        self.results = {
            "cpu": {"data": {"physical_cores": 2, "logical_cores": 4, "max_freq": 2500000000,
                            "smt_enabled": True, "class": "Entry"}},
            "memory": {"data": {"total": 4294967296, "percent_used": 85, "frequency_mts": 2400,
                               "channels": {"mode": "Single"}, "dimms": [{"size_mb": 4096}],
                               "slot_population": "1/2"}},
            "gpu": {"data": {"gpus": [{"model": "GT 710", "vram_total_mb": 2048, "pcie_info": {"width": "x4"}}],
                            "count": 1}},
            "storage": {"data": {"disks": [{"name": "sda", "disk_type": "HDD", "size": 500107862016,
                                           "smart_status": "PASSED", "remaining_life_pct": 45}]}},
            "cooling": {"data": {"throttling_risk": "High", "cooling_efficiency": "Poor"}},
            "network": {"data": {"interfaces": [{"name": "eth0", "speed": 100, "is_loopback": False}]}},
            "power": {"data": {"governors": {"current": "powersave"}, "batteries": [{"capacity_pct": 45}]}},
        }
        self.detector = BottleneckDetector(self.results)

    def test_cpu_bottleneck(self):
        result = self.detector._detect_cpu_bottleneck()
        assert result["bottleneck"]
        assert result["severity"] in ("high", "medium", "low")

    def test_memory_bottleneck(self):
        result = self.detector._detect_memory_bottleneck()
        assert result["bottleneck"]

    def test_gpu_bottleneck(self):
        result = self.detector._detect_gpu_bottleneck()
        assert result["bottleneck"]

    def test_storage_bottleneck(self):
        result = self.detector._detect_storage_bottleneck()
        assert result["bottleneck"]

    def test_thermal_bottleneck(self):
        result = self.detector._detect_thermal_bottleneck()
        assert result["bottleneck"]

    def test_network_bottleneck(self):
        result = self.detector._detect_network_bottleneck()
        assert result["bottleneck"]

    def test_detect_all(self):
        results = self.detector.detect_all()
        assert "critical" in results
        assert len(results["critical"]) > 0

    def test_no_bottleneck_good_system(self):
        good_results = {
            "cpu": {"data": {"physical_cores": 16, "logical_cores": 32, "max_freq": 5000000000,
                            "smt_enabled": True, "class": "Enterprise"}},
            "memory": {"data": {"total": 137438953472, "percent_used": 30, "frequency_mts": 5600,
                               "channels": {"mode": "Quad"}, "dimms": [{"size_mb": 32768}, {"size_mb": 32768}],
                               "slot_population": "4/4"}},
            "gpu": {"data": {"gpus": [{"model": "RTX 4090", "vram_total_mb": 24576, "pcie_info": {"width": "x16"}}],
                            "count": 1}},
            "storage": {"data": {"disks": [{"name": "nvme0n1", "disk_type": "NVMe Gen4", "size": 2000398934016,
                                           "smart_status": "PASSED", "remaining_life_pct": 99}]}},
            "cooling": {"data": {"throttling_risk": "None", "cooling_efficiency": "Excellent"}},
            "network": {"data": {"interfaces": [{"name": "eth0", "speed": 10000, "is_loopback": False}]}},
            "power": {"data": {"governors": {"current": "performance"}, "batteries": []}},
        }
        detector = BottleneckDetector(good_results)
        results = detector.detect_all()
        assert len(results["critical"]) == 0
