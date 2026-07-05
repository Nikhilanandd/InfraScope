from __future__ import annotations

from typing import Any


class UpgradeAdvisor:
    def __init__(self, collector_results: dict[str, Any]):
        self.results = collector_results

    def analyze_all(self) -> dict[str, Any]:
        return {
            "ram": self._suggest_ram_upgrade(),
            "storage": self._suggest_storage_upgrade(),
            "cpu": self._suggest_cpu_upgrade(),
            "gpu": self._suggest_gpu_upgrade(),
            "network": self._suggest_network_upgrade(),
        }

    def _suggest_ram_upgrade(self) -> dict[str, Any]:
        mem = self.results.get("memory", {}).get("data", {})
        suggestion: dict[str, Any] = {
            "needed": False,
            "current": {"size_gb": 0, "type": "", "frequency_mts": 0, "channels": ""},
            "recommended": {"size_gb": 0, "type": "", "frequency_mts": 0, "channels": ""},
            "improvements": [],
            "priority": "low",
        }

        total_gb = mem.get("total", 0) / (1024**3)
        freq = mem.get("frequency_mts", 0)
        channels = mem.get("channels", {})
        channel_mode = channels.get("mode", "Single")

        suggestion["current"]["size_gb"] = round(total_gb, 1)
        suggestion["current"]["type"] = mem.get("ddr_generation", "Unknown")
        suggestion["current"]["frequency_mts"] = freq
        suggestion["current"]["channels"] = channel_mode

        if total_gb < 8:
            suggestion["needed"] = True
            suggestion["recommended"]["size_gb"] = 16
            suggestion["priority"] = "critical"
            suggestion["improvements"] = [
                "+300% multitasking",
                "+200% Chrome tabs",
                "+150% basic productivity",
                "Run modern operating systems comfortably",
            ]
        elif total_gb < 16:
            suggestion["needed"] = True
            suggestion["recommended"]["size_gb"] = 32
            suggestion["priority"] = "high"
            suggestion["improvements"] = [
                "+40% virtualization",
                "+30% compilation speed",
                "+60% Chrome multitasking",
                "+50% Docker workloads",
            ]
        elif total_gb < 32:
            suggestion["needed"] = True
            suggestion["recommended"]["size_gb"] = 32
            suggestion["priority"] = "medium"
            suggestion["improvements"] = [
                "+25% virtualization capacity",
                "+20% database performance",
                "+15% development workflow",
            ]
        elif total_gb < 64:
            suggestion["recommended"]["size_gb"] = 64
            suggestion["priority"] = "low"
            suggestion["improvements"] = [
                "Run more VMs simultaneously",
                "Larger in-memory databases",
            ]

        if channel_mode in ("Single", "Unknown") and len(mem.get("dimms", [])) >= 1:
            suggestion["needed"] = True
            if suggestion["priority"] == "low":
                suggestion["priority"] = "medium"
            dimm_count = len(mem.get("dimms", []))
            slot_pop = mem.get("slot_population", "")
            free_slots = 0
            if "/" in slot_pop:
                parts = slot_pop.split("/")
                try:
                    free_slots = int(parts[1]) - int(parts[0])
                except (ValueError, IndexError):
                    free_slots = 0
            if free_slots > 0:
                suggestion["improvements"].append(
                    f"Enable dual-channel: add DIMM to empty slot ({free_slots} available)"
                )
            elif dimm_count == 1:
                suggestion["improvements"].append(
                    "Single-channel active. Install matching DIMM for dual-channel (+50% bandwidth)"
                )

        if freq < 3200 and total_gb >= 8:
            suggestion["needed"] = True
            suggestion["improvements"].append(
                f"RAM at {freq} MHz; upgrade to 3200+ MHz for better CPU performance"
            )

        return suggestion

    def _suggest_storage_upgrade(self) -> dict[str, Any]:
        storage = self.results.get("storage", {}).get("data", {})
        suggestion: dict[str, Any] = {
            "needed": False,
            "current": {"type": "", "size_gb": 0},
            "recommended": {"type": "", "size_gb": 0},
            "improvements": [],
            "priority": "low",
        }

        disks = storage.get("disks", [])
        for disk in disks:
            dtype = disk.get("disk_type", "")
            size_gb = disk.get("size", 0) / (1024**3)

            if dtype == "HDD":
                suggestion["needed"] = True
                suggestion["current"]["type"] = "HDD"
                suggestion["current"]["size_gb"] = round(size_gb)
                suggestion["recommended"]["type"] = "NVMe Gen4"
                suggestion["recommended"]["size_gb"] = max(round(size_gb), 500)
                suggestion["priority"] = "critical"
                suggestion["improvements"] = [
                    "6x storage throughput",
                    "5x boot speed",
                    "4x application loading",
                    "3x Docker image extraction",
                    "10x random IOPS",
                ]
                break
            elif dtype == "SATA SSD":
                suggestion["needed"] = True
                suggestion["current"]["type"] = "SATA SSD"
                suggestion["current"]["size_gb"] = round(size_gb)
                suggestion["recommended"]["type"] = "NVMe Gen4"
                suggestion["recommended"]["size_gb"] = max(round(size_gb), 500)
                suggestion["priority"] = "medium"
                suggestion["improvements"] = [
                    "5x sequential throughput (560 → 7000 MB/s)",
                    "3x application loading speed",
                    "2x game loading times",
                    "Large AI datasets load much faster",
                ]
                break
            elif "NVMe" in dtype and "Gen3" in dtype:
                suggestion["needed"] = True
                suggestion["current"]["type"] = dtype
                suggestion["current"]["size_gb"] = round(size_gb)
                suggestion["recommended"]["type"] = "NVMe Gen4"
                suggestion["recommended"]["size_gb"] = round(size_gb)
                suggestion["priority"] = "low"
                suggestion["improvements"] = [
                    "2x throughput (3500 → 7000 MB/s)",
                    "DirectStorage support",
                    "Future-proof for PCIe Gen5",
                ]
                break

        return suggestion

    def _suggest_cpu_upgrade(self) -> dict[str, Any]:
        cpu = self.results.get("cpu", {}).get("data", {})
        suggestion: dict[str, Any] = {
            "needed": False,
            "current": {"model": "", "cores": 0, "freq_ghz": 0},
            "recommended": {"model": "", "cores": 0, "freq_ghz": 0},
            "improvements": [],
            "priority": "low",
        }

        brand = cpu.get("brand", "")
        cores = cpu.get("physical_cores", 0)
        freq = cpu.get("max_freq", 0) / 1_000_000
        cpu_class = cpu.get("class", "")

        suggestion["current"]["model"] = brand
        suggestion["current"]["cores"] = cores
        suggestion["current"]["freq_ghz"] = round(freq, 2)

        if cpu_class in ("Entry", "Low"):
            suggestion["needed"] = True
            suggestion["priority"] = "high"
            suggestion["recommended"]["cores"] = 8
            suggestion["recommended"]["freq_ghz"] = 4.5
            suggestion["improvements"] = [
                "+85% software compilation",
                "+120% virtual machines",
                "+300% AI inference capability",
                "+200% multitasking",
            ]
            if "Intel" in brand:
                suggestion["recommended"]["model"] = "Intel Core i7-14700K"
            else:
                suggestion["recommended"]["model"] = "AMD Ryzen 7 7800X3D"

        elif cpu_class == "Mid" and cores < 12:
            suggestion["needed"] = True
            suggestion["priority"] = "medium"
            suggestion["recommended"]["cores"] = 12
            suggestion["recommended"]["freq_ghz"] = 4.5
            suggestion["improvements"] = [
                "+50% multi-threaded performance",
                "+40% compilation speed",
                "+60% VM density",
            ]
            if "Intel" in brand:
                suggestion["recommended"]["model"] = "Intel Core i7-14700K"
            else:
                suggestion["recommended"]["model"] = "AMD Ryzen 9 7900X"

        return suggestion

    def _suggest_gpu_upgrade(self) -> dict[str, Any]:
        gpu = self.results.get("gpu", {}).get("data", {})
        suggestion: dict[str, Any] = {
            "needed": False,
            "current": {"model": "", "vram_gb": 0},
            "recommended": {"model": "", "vram_gb": 0},
            "improvements": [],
            "priority": "low",
        }

        gpus = gpu.get("gpus", [])
        if not gpus:
            suggestion["needed"] = True
            suggestion["current"]["model"] = "Integrated Graphics"
            suggestion["current"]["vram_gb"] = 0
            suggestion["recommended"]["model"] = "NVIDIA RTX 4060"
            suggestion["recommended"]["vram_gb"] = 12
            suggestion["priority"] = "medium"
            suggestion["improvements"] = [
                "CUDA acceleration",
                "LLM inference (Llama 8B quantized)",
                "Stable Diffusion",
                "Hardware video encoding",
                "Gaming (1080p-1440p)",
            ]
            return suggestion

        for g in gpus:
            vram_gb = g.get("vram_total_mb", 0) / 1024
            model = g.get("model", "")

            suggestion["current"]["model"] = model
            suggestion["current"]["vram_gb"] = round(vram_gb, 1)

            if vram_gb < 8:
                suggestion["needed"] = True
                suggestion["priority"] = "medium"
                suggestion["recommended"]["vram_gb"] = 12
                suggestion["recommended"]["model"] = "NVIDIA RTX 4070"
                suggestion["improvements"] = [
                    "LLM inference (7B-13B models)",
                    "Stable Diffusion XL",
                    "CUDA/GPU acceleration for ML",
                    "1440p gaming",
                ]
            elif vram_gb < 12:
                suggestion["needed"] = True
                suggestion["priority"] = "low"
                suggestion["recommended"]["vram_gb"] = 16
                suggestion["recommended"]["model"] = "NVIDIA RTX 4080"
                suggestion["improvements"] = [
                    "Larger LLM models (30B+)",
                    "Higher resolution AI generation",
                    "4K gaming",
                ]

        return suggestion

    def _suggest_network_upgrade(self) -> dict[str, Any]:
        net = self.results.get("network", {}).get("data", {})
        suggestion: dict[str, Any] = {
            "needed": False,
            "current": {"speed_mbps": 0},
            "recommended": {"speed_mbps": 0},
            "improvements": [],
            "priority": "low",
        }

        interfaces = net.get("interfaces", [])
        max_speed = 0
        for iface in interfaces:
            if not iface.get("is_loopback"):
                speed = iface.get("speed", 0)
                max_speed = max(max_speed, speed)

        suggestion["current"]["speed_mbps"] = max_speed
        if max_speed <= 100:
            suggestion["needed"] = True
            suggestion["priority"] = "high"
            suggestion["recommended"]["speed_mbps"] = 1000
            suggestion["improvements"] = [
                "10x network throughput",
                "Faster file transfers",
                "Reduced latency",
            ]
        elif max_speed <= 1000:
            suggestion["recommended"]["speed_mbps"] = 10000
            suggestion["priority"] = "low"
            suggestion["improvements"] = [
                "10x network throughput",
                "NAS performance improvement",
                "Reduced backup times",
            ]

        return suggestion
