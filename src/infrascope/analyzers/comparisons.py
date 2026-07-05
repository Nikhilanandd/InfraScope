from __future__ import annotations

from typing import Any


class ComparisonAnalyzer:
    def __init__(self, collector_results: dict[str, Any]):
        self.results = collector_results

    def compare_all(self) -> dict[str, Any]:
        return {
            "cpu": self._compare_cpu(),
            "memory": self._compare_memory(),
            "storage": self._compare_storage(),
            "gpu": self._compare_gpu(),
        }

    def _compare_cpu(self) -> dict[str, Any]:
        cpu = self.results.get("cpu", {}).get("data", {})
        cores = cpu.get("physical_cores", 0)
        threads = cpu.get("logical_cores", 0)
        freq = cpu.get("max_freq", 0) / 1_000_000
        cpu_class = cpu.get("class", "Entry")

        tiers = {
            "Entry Level": {"cores": 2, "threads": 4, "freq": 2.5, "score": 10},
            "Mid Range": {"cores": 6, "threads": 12, "freq": 4.0, "score": 40},
            "High End": {"cores": 12, "threads": 24, "freq": 4.5, "score": 70},
            "Professional": {"cores": 16, "threads": 32, "freq": 5.0, "score": 85},
            "Enterprise": {"cores": 32, "threads": 64, "freq": 3.5, "score": 95},
        }

        current_score = min(
            (cores / 32) * 40 + (threads / 64) * 30 + (freq / 5.0) * 30,
            100,
        )

        comparisons = []
        for tier_name, tier_spec in tiers.items():
            pct = current_score / tier_spec["score"] * 100 if tier_spec["score"] > 0 else 0
            comparisons.append({
                "tier": tier_name,
                "percent": round(pct, 1),
            })

        cpu_class_index = list(tiers.keys()).index(cpu_class) if cpu_class in tiers else 0
        return {
            "current_score": round(current_score, 1),
            "current_tier": cpu_class,
            "comparisons": comparisons,
            "above_average": cpu_class_index >= 2 if cpu_class in tiers else False,
        }

    def _compare_memory(self) -> dict[str, Any]:
        mem = self.results.get("memory", {}).get("data", {})
        total_gb = mem.get("total", 0) / (1024**3)
        freq = mem.get("frequency_mts", 0)

        tiers = {
            "Entry Level": {"gb": 8, "freq": 2400},
            "Mid Range": {"gb": 16, "freq": 3200},
            "High End": {"gb": 32, "freq": 5600},
            "Professional": {"gb": 64, "freq": 6000},
            "Enterprise": {"gb": 128, "freq": 4800},
        }

        comparisons = []
        for tier_name, tier_spec in tiers.items():
            size_pct = total_gb / tier_spec["gb"] * 100 if tier_spec["gb"] > 0 else 0
            comparisons.append({
                "tier": tier_name,
                "size_percent": round(size_pct, 1),
            })

        return {
            "current_gb": round(total_gb, 1),
            "current_freq": freq,
            "comparisons": comparisons,
        }

    def _compare_storage(self) -> dict[str, Any]:
        storage = self.results.get("storage", {}).get("data", {})
        disks = storage.get("disks", [])
        best_type = "Unknown"
        for disk in disks:
            dtype = disk.get("disk_type", "")
            if "Gen5" in dtype:
                best_type = "NVMe Gen5"
            elif "Gen4" in dtype:
                best_type = "NVMe Gen4"
            elif "Gen3" in dtype:
                best_type = "NVMe Gen3"
            elif "NVMe" in dtype:
                best_type = "NVMe"
            elif "SATA SSD" in dtype:
                best_type = "SATA SSD"
            elif "HDD" in dtype:
                best_type = "HDD"

        tiers = {
            "Entry Level": "SATA SSD",
            "Mid Range": "NVMe Gen3",
            "High End": "NVMe Gen4",
            "Professional": "NVMe Gen4",
            "Enterprise": "NVMe Gen5",
        }

        seq_speeds = {
            "HDD": 200,
            "SATA SSD": 560,
            "NVMe": 2000,
            "NVMe Gen3": 3500,
            "NVMe Gen4": 7000,
            "NVMe Gen5": 14000,
        }

        current_speed = seq_speeds.get(best_type, 0)
        comparisons = []
        for tier_name, tier_storage in tiers.items():
            tier_speed = seq_speeds.get(tier_storage, 0)
            pct = current_speed / tier_speed * 100 if tier_speed > 0 else 0
            comparisons.append({
                "tier": tier_name,
                "percent": round(pct, 1),
            })

        return {
            "current_type": best_type,
            "current_speed_mb_s": current_speed,
            "comparisons": comparisons,
        }

    def _compare_gpu(self) -> dict[str, Any]:
        gpu = self.results.get("gpu", {}).get("data", {})
        gpus = gpu.get("gpus", [])
        if not gpus:
            return {"current_gpu": "None", "comparisons": []}

        best_gpu = max(gpus, key=lambda g: g.get("vram_total_mb", 0))
        vram_gb = best_gpu.get("vram_total_mb", 0) / 1024
        model = best_gpu.get("model", "Unknown")

        tiers = {
            "Entry Level": {"vram": 4, "model": "GTX 1650"},
            "Mid Range": {"vram": 8, "model": "RTX 3060"},
            "High End": {"vram": 12, "model": "RTX 4070"},
            "Professional": {"vram": 24, "model": "RTX 4090"},
            "Enterprise": {"vram": 80, "model": "A100"},
        }

        comparisons = []
        for tier_name, tier_spec in tiers.items():
            pct = vram_gb / tier_spec["vram"] * 100 if tier_spec["vram"] > 0 else 0
            comparisons.append({
                "tier": tier_name,
                "percent": round(pct, 1),
            })

        return {
            "current_gpu": model,
            "current_vram_gb": round(vram_gb, 1),
            "comparisons": comparisons,
        }
