from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime

import pytest
from infrascope.reporting.markdown import MarkdownReport
from infrascope.reporting.json_report import JSONReport
from infrascope.reporting.csv_report import CSVReport


class TestReports:
    def setup_method(self):
        self.results = {
            "cpu": {"data": {"brand": "Test CPU", "physical_cores": 4, "logical_cores": 8,
                            "vendor": "Test", "arch": "x86_64", "class": "Mid",
                            "base_freq": 3000000000, "max_freq": 4000000000,
                            "smt_enabled": True, "l3_cache": "8 MB"}},
            "memory": {"data": {"total": 17179869184, "ddr_generation": "DDR4",
                               "frequency_mts": 3200, "ecc": False,
                               "channels": {"mode": "Dual"}, "slot_population": "2/2"}},
            "gpu": {"data": {"gpus": [{"model": "Test GPU", "vram_total_mb": 8192,
                                      "vendor": "NVIDIA", "cuda_cores": 4096}],
                            "count": 1}},
            "storage": {"data": {"disks": [{"name": "nvme0n1", "disk_type": "NVMe Gen3",
                                           "size": 512110190592, "smart_status": "PASSED"}],
                                "disk_usage": {"/": {"total": 1000000000, "used": 500000000,
                                                     "free": 500000000, "percent": 50.0}}}},
            "scores": {"cpu": 70, "memory": 65, "gpu": 60, "storage": 55,
                      "networking": 50, "thermals": 80, "overall": 63.3, "rating": "Good"},
            "bottlenecks": {"critical": ["cpu"]},
            "workloads": {"general": "Excellent", "programming": "Good"},
        }
        self.temp_dir = tempfile.mkdtemp()

    def test_markdown_report(self):
        report = MarkdownReport(self.results, self.temp_dir)
        path = report.generate()
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert "# InfraScope Hardware Report" in content
        assert "Good" in content
        assert "Test CPU" in content

    def test_json_report(self):
        report = JSONReport(self.results, self.temp_dir)
        path = report.generate()
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert "metadata" in data
        assert "hardware" in data
        assert "scores" in data
        assert data["metadata"]["tool"] == "InfraScope"

    def test_csv_report(self):
        report = CSVReport(self.results, self.temp_dir)
        path = report.generate()
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert "InfraScope" in content
        assert "Test CPU" in content

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
