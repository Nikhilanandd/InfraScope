from __future__ import annotations

from typing import Any


class ScoringAnalyzer:
    def __init__(self, collector_results: dict[str, Any]):
        self.results = collector_results
        self.scores: dict[str, float] = {}

    def calculate_all(self) -> dict[str, Any]:
        self.scores["cpu"] = self._score_cpu()
        self.scores["memory"] = self._score_memory()
        self.scores["gpu"] = self._score_gpu()
        self.scores["storage"] = self._score_storage()
        self.scores["networking"] = self._score_network()
        self.scores["thermals"] = self._score_thermals()
        self.scores["overall"] = self._calculate_overall()

        return {
            "scores": self.scores,
            "overall": self.scores.get("overall", 0),
            "rating": self._get_rating(self.scores.get("overall", 0)),
        }

    def _score_cpu(self) -> float:
        cpu_data = self.results.get("cpu", {}).get("data", {})
        score = 50.0

        cores = cpu_data.get("physical_cores", 0)
        threads = cpu_data.get("logical_cores", 0)
        max_freq = cpu_data.get("max_freq", 0) / 1_000_000

        if cores >= 64:
            score += 40
        elif cores >= 32:
            score += 35
        elif cores >= 16:
            score += 30
        elif cores >= 12:
            score += 25
        elif cores >= 8:
            score += 20
        elif cores >= 6:
            score += 15
        elif cores >= 4:
            score += 10
        else:
            score += 5

        if max_freq >= 5.0:
            score += 10
        elif max_freq >= 4.5:
            score += 8
        elif max_freq >= 4.0:
            score += 6
        elif max_freq >= 3.5:
            score += 4
        elif max_freq >= 3.0:
            score += 2

        flags = set(cpu_data.get("flags", []))
        if "avx512" in str(flags):
            score += 10
        elif "avx2" in flags:
            score += 6
        elif "avx" in flags:
            score += 3

        if cpu_data.get("smt_enabled"):
            score += 5

        if cpu_data.get("numa_nodes", 1) > 1:
            score += 5

        return min(score, 100)

    def _score_memory(self) -> float:
        mem_data = self.results.get("memory", {}).get("data", {})
        score = 50.0

        total_gb = mem_data.get("total", 0) / (1024**3)
        if total_gb >= 128:
            score += 40
        elif total_gb >= 64:
            score += 35
        elif total_gb >= 32:
            score += 28
        elif total_gb >= 16:
            score += 20
        elif total_gb >= 8:
            score += 12
        else:
            score += 5

        freq = mem_data.get("frequency_mts", 0)
        if freq >= 6000:
            score += 10
        elif freq >= 4800:
            score += 8
        elif freq >= 3600:
            score += 6
        elif freq >= 3200:
            score += 5
        elif freq >= 2400:
            score += 3

        channels = mem_data.get("channels", {})
        channel_mode = channels.get("mode", "Single")
        if channel_mode == "Quad":
            score += 10
        elif channel_mode == "Triple":
            score += 7
        elif channel_mode == "Dual":
            score += 5

        if mem_data.get("ecc"):
            score += 5

        return min(score, 100)

    def _score_gpu(self) -> float:
        gpu_data = self.results.get("gpu", {}).get("data", {})
        score = 30.0

        gpus = gpu_data.get("gpus", [])
        if not gpus:
            return score

        for gpu in gpus:
            vram_gb = gpu.get("vram_total_mb", 0) / 1024
            model = gpu.get("model", "").upper()

            if "H100" in model or "A100" in model:
                score = 100
            elif "RTX 4090" in model:
                score = max(score, 95)
            elif "RTX 4080" in model:
                score = max(score, 85)
            elif "RTX 4070" in model:
                score = max(score, 75)
            elif "RTX 4060" in model:
                score = max(score, 65)
            elif "RTX 3090" in model:
                score = max(score, 90)
            elif "RTX 3080" in model:
                score = max(score, 80)
            elif "RTX 3070" in model:
                score = max(score, 70)
            elif "RTX 3060" in model:
                score = max(score, 60)
            elif "RTX 2080" in model:
                score = max(score, 55)
            elif "T4" in model:
                score = max(score, 50)
            elif "V100" in model:
                score = max(score, 85)
            else:
                if vram_gb >= 24:
                    score = max(score, 80)
                elif vram_gb >= 16:
                    score = max(score, 70)
                elif vram_gb >= 12:
                    score = max(score, 60)
                elif vram_gb >= 8:
                    score = max(score, 50)
                elif vram_gb >= 4:
                    score = max(score, 40)
                else:
                    score = max(score, 30)

            if gpu.get("tensor_cores", 0) > 0:
                score = min(score + 10, 100)

        return min(score, 100)

    def _score_storage(self) -> float:
        storage_data = self.results.get("storage", {}).get("data", {})
        score = 30.0

        disks = storage_data.get("disks", [])
        if not disks:
            return score

        has_nvme = False
        has_ssd = False
        best_gen = 0
        total_size_gb = 0

        for disk in disks:
            size_gb = disk.get("size", 0) / (1024**3)
            total_size_gb += size_gb
            dtype = disk.get("disk_type", "")
            if "Gen5" in dtype:
                has_nvme = True
                best_gen = max(best_gen, 5)
            elif "Gen4" in dtype:
                has_nvme = True
                best_gen = max(best_gen, 4)
            elif "Gen3" in dtype:
                has_nvme = True
                best_gen = max(best_gen, 3)
            elif "NVMe" in dtype:
                has_nvme = True
            elif "SATA SSD" in dtype:
                has_ssd = True

        if best_gen >= 5:
            score += 50
        elif best_gen >= 4:
            score += 40
        elif best_gen >= 3:
            score += 30
        elif has_nvme:
            score += 25
        elif has_ssd:
            score += 15
        else:
            score += 5

        if total_size_gb >= 4000:
            score += 20
        elif total_size_gb >= 2000:
            score += 15
        elif total_size_gb >= 1000:
            score += 10
        elif total_size_gb >= 500:
            score += 5

        return min(score, 100)

    def _score_network(self) -> float:
        net_data = self.results.get("network", {}).get("data", {})
        score = 40.0

        interfaces = net_data.get("interfaces", [])
        has_1g = has_10g = has_25g = has_40g = False

        for iface in interfaces:
            speed = iface.get("speed", 0)
            if speed >= 40000:
                has_40g = True
                score += 30
            elif speed >= 25000:
                has_25g = True
                score += 25
            elif speed >= 10000:
                has_10g = True
                score += 20
            elif speed >= 1000:
                has_1g = True
                score += 10

        for iface in interfaces:
            if not iface.get("is_loopback"):
                score += 5
                break

        return min(score, 100)

    def _score_thermals(self) -> float:
        cool_data = self.results.get("cooling", {}).get("data", {})
        score = 70.0

        risk = cool_data.get("throttling_risk", "None")
        if risk == "Critical":
            score -= 50
        elif risk == "High":
            score -= 30
        elif risk == "Moderate":
            score -= 15
        elif risk == "Low":
            score -= 5

        efficiency = cool_data.get("cooling_efficiency", "Unknown")
        if efficiency == "Excellent":
            score += 10
        elif efficiency == "Good":
            score += 5
        elif efficiency == "Poor":
            score -= 10

        return max(0, min(score, 100))

    def _calculate_overall(self) -> float:
        weights = {
            "cpu": 0.30,
            "memory": 0.20,
            "gpu": 0.15,
            "storage": 0.15,
            "networking": 0.10,
            "thermals": 0.10,
        }
        overall = 0.0
        for component, weight in weights.items():
            overall += self.scores.get(component, 0) * weight
        return round(overall, 1)

    @staticmethod
    def _get_rating(score: float) -> str:
        if score >= 95:
            return "Outstanding"
        if score >= 85:
            return "Excellent"
        if score >= 75:
            return "Very Good"
        if score >= 65:
            return "Good"
        if score >= 50:
            return "Acceptable"
        if score >= 35:
            return "Limited"
        return "Poor"
