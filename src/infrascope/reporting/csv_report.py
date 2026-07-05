from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Any


class CSVReport:
    def __init__(self, results: dict[str, Any], output_dir: str = "reports"):
        self.results = results
        self.output_dir = output_dir

    def generate(self, filename: str | None = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"infrascope_report_{timestamp}.csv"

        os.makedirs(self.output_dir, exist_ok=True)
        filepath = os.path.join(self.output_dir, filename)

        data = self._build_csv_data()
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            for row in data:
                writer.writerow(row)

        return filepath

    def _build_csv_data(self) -> list[list[str]]:
        rows: list[list[str]] = []
        rows.append(["InfraScope Hardware Report"])
        rows.append(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        rows.append([])

        scores = self.results.get("scores", {})
        rows.append(["Scores"])
        rows.append(["Component", "Score"])
        for component, score in scores.items():
            rows.append([component.title(), str(score)])
        rows.append([])

        cpu = self.results.get("cpu", {}).get("data", {})
        if cpu:
            rows.append(["CPU"])
            rows.append(["Property", "Value"])
            for key in ["vendor", "brand", "arch", "class", "physical_cores",
                         "logical_cores", "smt_enabled"]:
                rows.append([key.replace("_", " ").title(), str(cpu.get(key, ""))])
            freq = cpu.get("max_freq", 0) / 1_000_000
            rows.append(["Max Frequency (GHz)", f"{freq:.2f}"])
            rows.append([])

        mem = self.results.get("memory", {}).get("data", {})
        if mem:
            rows.append(["Memory"])
            rows.append(["Property", "Value"])
            rows.append(["Total (GB)", f"{mem.get('total', 0) / (1024**3):.1f}"])
            rows.append(["Type", mem.get("ddr_generation", "N/A")])
            rows.append(["Frequency (MHz)", str(mem.get("frequency_mts", 0))])
            rows.append(["ECC", "Yes" if mem.get("ecc") else "No"])
            rows.append([])

        gpu_data = self.results.get("gpu", {}).get("data", {})
        gpus = gpu_data.get("gpus", [])
        if gpus:
            rows.append(["GPU"])
            rows.append(["Property", "Value"])
            for g in gpus:
                rows.append(["Model", g.get("model", "N/A")])
                rows.append(["VRAM (GB)", f"{g.get('vram_total_mb', 0) / 1024:.1f}"])
            rows.append([])

        storage = self.results.get("storage", {}).get("data", {})
        disks = storage.get("disks", [])
        if disks:
            rows.append(["Storage"])
            rows.append(["Device", "Type", "Size (GB)"])
            for d in disks:
                size_gb = d.get("size", 0) / (1024**3)
                rows.append([d.get("name", ""), d.get("disk_type", ""), f"{size_gb:.1f}"])
            rows.append([])

        bottlenecks = self.results.get("bottlenecks", {})
        critical = bottlenecks.get("critical", [])
        if critical:
            rows.append(["Bottlenecks"])
            rows.append(["Component", "Details"])
            for comp in critical:
                info = bottlenecks.get(comp, {})
                for detail in info.get("details", []):
                    rows.append([comp.title(), detail])
            rows.append([])

        workloads = self.results.get("workloads", {})
        if workloads:
            rows.append(["Workload Capability"])
            rows.append(["Workload", "Rating"])
            for name, rating in sorted(workloads.items()):
                rows.append([name.replace("_", " ").title(), rating])

        return rows
