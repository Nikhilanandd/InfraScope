from __future__ import annotations

from typing import Any


class WorkloadAnalyzer:
    def __init__(self, collector_results: dict[str, Any]):
        self.results = collector_results
        cpu = self.results.get("cpu", {}).get("data", {})
        mem = self.results.get("memory", {}).get("data", {})
        gpu = self.results.get("gpu", {}).get("data", {})
        storage = self.results.get("storage", {}).get("data", {})

        self.cores = cpu.get("physical_cores", 0)
        self.threads = cpu.get("logical_cores", 0)
        self.ram_gb = mem.get("total", 0) / (1024**3)
        self.cpu_class = cpu.get("class", "Entry")
        self.has_nvidia = gpu.get("has_nvidia", False)
        self.has_dedicated_gpu = gpu.get("count", 0) > 0
        self.max_vram_gb = max(
            (g.get("vram_total_mb", 0) for g in gpu.get("gpus", [])), default=0
        ) / 1024
        self.has_nvme = any(
            "NVMe" in d.get("disk_type", "") for d in storage.get("disks", [])
        )
        self.has_ssd = any(
            "SSD" in d.get("disk_type", "") for d in storage.get("disks", [])
        )

    def analyze_all(self) -> dict[str, str]:
        return {
            "general": self._general(),
            "office": self._office(),
            "programming": self._programming(),
            "web_development": self._web_development(),
            "android_studio": self._android_studio(),
            "docker": self._docker(),
            "kubernetes": self._kubernetes(),
            "virtual_machines": self._virtual_machines(),
            "media_server": self._media_server(),
            "video_editing": self._video_editing(),
            "photo_editing": self._photo_editing(),
            "cad": self._cad(),
            "gaming": self._gaming(),
            "machine_learning": self._machine_learning(),
            "llm_inference": self._llm_inference(),
            "stable_diffusion": self._stable_diffusion(),
            "ci_cd": self._ci_cd(),
            "monitoring": self._monitoring(),
            "database": self._database(),
            "web_server": self._web_server(),
            "devops_workstation": self._devops_workstation(),
            "homelab": self._homelab(),
        }

    def _rate(self, conditions: list[bool]) -> str:
        true_count = sum(conditions)
        if true_count >= len(conditions):
            return "Excellent"
        ratio = true_count / len(conditions) if conditions else 0
        if ratio >= 0.8:
            return "Excellent"
        if ratio >= 0.6:
            return "Good"
        if ratio >= 0.4:
            return "Acceptable"
        if ratio >= 0.2:
            return "Limited"
        return "Not Recommended"

    def _general(self) -> str:
        return self._rate([
            self.ram_gb >= 8,
            self.cores >= 4,
            self.has_ssd,
        ])

    def _office(self) -> str:
        return self._rate([
            self.ram_gb >= 8,
            self.cores >= 4,
            self.has_ssd,
        ])

    def _programming(self) -> str:
        return self._rate([
            self.ram_gb >= 16,
            self.cores >= 6,
            self.has_ssd,
            self.threads >= 8,
        ])

    def _web_development(self) -> str:
        return self._rate([
            self.ram_gb >= 16,
            self.cores >= 6,
            self.has_ssd,
        ])

    def _android_studio(self) -> str:
        return self._rate([
            self.ram_gb >= 32,
            self.cores >= 8,
            self.has_ssd,
            self.has_dedicated_gpu,
        ])

    def _docker(self) -> str:
        return self._rate([
            self.ram_gb >= 16,
            self.cores >= 4,
            self.has_ssd,
            self.threads >= 8,
        ])

    def _kubernetes(self) -> str:
        return self._rate([
            self.ram_gb >= 32,
            self.cores >= 8,
            self.has_ssd,
            self.threads >= 16,
        ])

    def _virtual_machines(self) -> str:
        return self._rate([
            self.ram_gb >= 32,
            self.cores >= 8,
            self.has_ssd,
            self.threads >= 16,
        ])

    def _media_server(self) -> str:
        return self._rate([
            self.ram_gb >= 8,
            self.cores >= 4,
            self.has_ssd,
        ])

    def _video_editing(self) -> str:
        return self._rate([
            self.ram_gb >= 32,
            self.cores >= 8,
            self.has_dedicated_gpu,
            self.has_ssd,
            self.max_vram_gb >= 6,
        ])

    def _photo_editing(self) -> str:
        return self._rate([
            self.ram_gb >= 16,
            self.cores >= 6,
            self.has_dedicated_gpu,
            self.has_ssd,
        ])

    def _cad(self) -> str:
        return self._rate([
            self.ram_gb >= 32,
            self.cores >= 8,
            self.has_dedicated_gpu,
            self.max_vram_gb >= 6,
        ])

    def _gaming(self) -> str:
        return self._rate([
            self.has_dedicated_gpu,
            self.ram_gb >= 16,
            self.cores >= 6,
            self.max_vram_gb >= 6,
        ])

    def _machine_learning(self) -> str:
        return self._rate([
            self.has_nvidia,
            self.ram_gb >= 32,
            self.max_vram_gb >= 8,
            self.cores >= 8,
        ])

    def _llm_inference(self) -> str:
        return self._rate([
            self.has_nvidia,
            self.ram_gb >= 32,
            self.max_vram_gb >= 12,
        ])

    def _stable_diffusion(self) -> str:
        return self._rate([
            self.has_nvidia,
            self.max_vram_gb >= 8,
            self.ram_gb >= 16,
        ])

    def _ci_cd(self) -> str:
        return self._rate([
            self.ram_gb >= 32,
            self.cores >= 8,
            self.has_ssd,
            self.threads >= 16,
        ])

    def _monitoring(self) -> str:
        return self._rate([
            self.ram_gb >= 16,
            self.cores >= 4,
            self.has_ssd,
            self.has_nvme,
        ])

    def _database(self) -> str:
        return self._rate([
            self.ram_gb >= 32,
            self.cores >= 8,
            self.has_nvme,
            self.threads >= 16,
        ])

    def _web_server(self) -> str:
        return self._rate([
            self.ram_gb >= 16,
            self.cores >= 4,
            self.has_ssd,
            self.threads >= 8,
        ])

    def _devops_workstation(self) -> str:
        return self._rate([
            self.ram_gb >= 32,
            self.cores >= 8,
            self.has_ssd,
            self.has_nvme,
            self.threads >= 16,
        ])

    def _homelab(self) -> str:
        return self._rate([
            self.ram_gb >= 16,
            self.cores >= 4,
            self.has_ssd,
            self.threads >= 8,
        ])
