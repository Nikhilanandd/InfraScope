from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any


class JSONReport:
    def __init__(self, results: dict[str, Any], output_dir: str = "reports"):
        self.results = results
        self.output_dir = output_dir

    def generate(self, filename: str | None = None, pretty: bool = True) -> str:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"infrascope_report_{timestamp}.json"

        os.makedirs(self.output_dir, exist_ok=True)
        filepath = os.path.join(self.output_dir, filename)

        report = self._build_report()
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2 if pretty else None, default=str)

        return filepath

    def _build_report(self) -> dict[str, Any]:
        report: dict[str, Any] = {
            "metadata": {
                "tool": "InfraScope",
                "version": "1.0.0",
                "generated_at": datetime.now().isoformat(),
            },
            "scores": self.results.get("scores", {}),
            "hardware": {},
            "analysis": {},
        }

        for collector_name in ["cpu", "memory", "gpu", "storage", "network",
                               "motherboard", "cooling", "power", "usb",
                               "pci", "monitors", "audio", "virtualization",
                               "filesystem"]:
            data = self.results.get(collector_name, {}).get("data", {})
            if data:
                report["hardware"][collector_name] = data

        for analyzer_name in ["bottlenecks", "upgrades", "workloads", "comparisons", "benchmarks"]:
            data = self.results.get(analyzer_name, {})
            if data:
                report["analysis"][analyzer_name] = data

        return report
