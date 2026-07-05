from __future__ import annotations

import pytest
from infrascope.analyzers.scoring import ScoringAnalyzer


class TestScoringAnalyzer:
    def setup_method(self):
        self.results = {
            "cpu": {"data": {"physical_cores": 8, "logical_cores": 16, "max_freq": 4500000000,
                            "smt_enabled": True, "numa_nodes": 1, "flags": ["avx2", "sse"]}},
            "memory": {"data": {"total": 34359738368, "frequency_mts": 3200, "ecc": False,
                               "channels": {"mode": "Dual"}}},
            "gpu": {"data": {"gpus": [{"model": "RTX 3080", "vram_total_mb": 10240, "tensor_cores": 272}],
                            "count": 1, "has_nvidia": True}},
            "storage": {"data": {"disks": [{"name": "nvme0n1", "size": 512110190592,
                                           "disk_type": "NVMe Gen4", "smart_status": "PASSED"}]}},
            "network": {"data": {"interfaces": [{"name": "eth0", "speed": 1000, "is_loopback": False}]}},
            "cooling": {"data": {"throttling_risk": "None", "cooling_efficiency": "Excellent"}},
        }
        self.analyzer = ScoringAnalyzer(self.results)

    def test_cpu_score(self):
        score = self.analyzer._score_cpu()
        assert 0 <= score <= 100
        assert score > 50  # 8 cores, 4.5GHz, SMT, AVX2 should score well

    def test_memory_score(self):
        score = self.analyzer._score_memory()
        assert 0 <= score <= 100

    def test_gpu_score(self):
        score = self.analyzer._score_gpu()
        assert 0 <= score <= 100

    def test_storage_score(self):
        score = self.analyzer._score_storage()
        assert 0 <= score <= 100

    def test_network_score(self):
        score = self.analyzer._score_network()
        assert 0 <= score <= 100

    def test_thermals_score(self):
        score = self.analyzer._score_thermals()
        assert 0 <= score <= 100

    def test_overall_score(self):
        scores = self.analyzer.calculate_all()
        assert "scores" in scores
        assert scores["overall"] > 0

    def test_rating(self):
        assert self.analyzer._get_rating(95) == "Outstanding"
        assert self.analyzer._get_rating(85) == "Excellent"
        assert self.analyzer._get_rating(22) == "Poor"
