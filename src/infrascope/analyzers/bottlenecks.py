from __future__ import annotations

from typing import Any


class BottleneckDetector:
    def __init__(self, collector_results: dict[str, Any]):
        self.results = collector_results

    def detect_all(self) -> dict[str, Any]:
        bottlenecks: dict[str, Any] = {
            "cpu": self._detect_cpu_bottleneck(),
            "memory": self._detect_memory_bottleneck(),
            "gpu": self._detect_gpu_bottleneck(),
            "storage": self._detect_storage_bottleneck(),
            "pcie": self._detect_pcie_bottleneck(),
            "thermal": self._detect_thermal_bottleneck(),
            "network": self._detect_network_bottleneck(),
            "power": self._detect_power_bottleneck(),
        }
        bottlenecks["critical"] = [
            k for k, v in bottlenecks.items()
            if v.get("severity") in ("critical", "high")
        ]
        bottlenecks["count"] = len(bottlenecks["critical"])
        return bottlenecks

    def _detect_cpu_bottleneck(self) -> dict[str, Any]:
        cpu = self.results.get("cpu", {}).get("data", {})
        result: dict[str, Any] = {
            "bottleneck": False,
            "severity": "none",
            "details": [],
        }

        cores = cpu.get("physical_cores", 0)
        freq = cpu.get("max_freq", 0) / 1_000_000
        cpu_class = cpu.get("class", "")
        smt = cpu.get("smt_enabled", False)

        if cores < 4:
            result["bottleneck"] = True
            result["severity"] = "high"
            result["details"].append("Only {} physical cores; multitasking will suffer".format(cores))

        if freq < 2.0:
            result["bottleneck"] = True
            result["details"].append("Low max frequency ({:.1f} GHz); responsive tasks).".format(freq))

        if cores >= 8 and not smt:
            result["details"].append("SMT/HT disabled; {} logical cores unused".format(cores))

        if cpu_class == "Entry":
            result["bottleneck"] = True
            if result["severity"] == "none":
                result["severity"] = "medium"
            result["details"].append("Entry-level CPU detected; upgrade recommended for demanding workloads")

        if result["severity"] == "none":
            result["severity"] = "low" if result["bottleneck"] else "none"

        return result

    def _detect_memory_bottleneck(self) -> dict[str, Any]:
        mem = self.results.get("memory", {}).get("data", {})
        result: dict[str, Any] = {
            "bottleneck": False,
            "severity": "none",
            "details": [],
        }

        total_gb = mem.get("total", 0) / (1024**3)
        percent = mem.get("percent_used", 0)
        channels = mem.get("channels", {})
        channel_mode = channels.get("mode", "Single")
        freq = mem.get("frequency_mts", 0)

        if total_gb < 8:
            result["bottleneck"] = True
            result["severity"] = "critical"
            result["details"].append("Only {:.0f} GB RAM; severe limitation for modern workloads".format(total_gb))
        elif total_gb < 16:
            result["bottleneck"] = True
            result["severity"] = "high"
            result["details"].append("{:.0f} GB RAM; upgrade to 32 GB recommended".format(total_gb))
        elif total_gb < 32:
            result["bottleneck"] = True
            result["severity"] = result.get("severity", "medium")
            result["details"].append("{:.0f} GB RAM may limit virtualization and development".format(total_gb))

        if percent > 90:
            result["bottleneck"] = True
            result["severity"] = "critical"
            result["details"].append("RAM usage at {:.0f}%; system is memory starved".format(percent))
        elif percent > 75:
            result["bottleneck"] = True
            if result["severity"] in ("none", "low"):
                result["severity"] = "medium"
            result["details"].append("High RAM usage ({:.0f}%)".format(percent))

        if channel_mode in ("Single", "Unknown") and total_gb >= 8:
            result["bottleneck"] = True
            if result["severity"] in ("none", "low"):
                result["severity"] = "medium"
            result["details"].append(f"Single-channel memory; dual-channel would improve bandwidth by up to 50%")

        if freq < 2400:
            result["details"].append(f"Low memory frequency ({freq} MHz)")
        elif freq < 3200 and total_gb >= 16:
            result["details"].append(f"Consider upgrading memory speed")

        if not result["bottleneck"]:
            result["severity"] = "none"

        return result

    def _detect_gpu_bottleneck(self) -> dict[str, Any]:
        gpu = self.results.get("gpu", {}).get("data", {})
        result: dict[str, Any] = {
            "bottleneck": False,
            "severity": "none",
            "details": [],
        }

        gpus = gpu.get("gpus", [])
        if not gpus:
            result["details"].append("No dedicated GPU detected; integrated graphics only")
            result["bottleneck"] = True
            result["severity"] = "medium"
            return result

        for g in gpus:
            vram_gb = g.get("vram_total_mb", 0) / 1024
            model = g.get("model", "")

            if vram_gb < 4:
                result["bottleneck"] = True
                result["severity"] = "high"
                result["details"].append(f"{model}: only {vram_gb:.0f} GB VRAM; insufficient for modern workloads")
            elif vram_gb < 8:
                result["bottleneck"] = True
                if result["severity"] == "none":
                    result["severity"] = "medium"
                result["details"].append(f"{model}: {vram_gb:.0f} GB VRAM may limit AI/ML workloads")

            pcie = g.get("pcie_info", {})
            width = pcie.get("width", "x16")
            if width and width != "x16" and width != "unknown":
                result["bottleneck"] = True
                result["details"].append(f"{model} running at {width}; may limit performance")

        return result

    def _detect_storage_bottleneck(self) -> dict[str, Any]:
        storage = self.results.get("storage", {}).get("data", {})
        result: dict[str, Any] = {
            "bottleneck": False,
            "severity": "none",
            "details": [],
        }

        disks = storage.get("disks", [])
        if not disks:
            return result

        for disk in disks:
            dtype = disk.get("disk_type", "")
            remaining = disk.get("remaining_life_pct", 100)
            disk_name = disk.get("name", "")

            if dtype == "HDD":
                result["bottleneck"] = True
                result["severity"] = "high"
                result["details"].append(f"/dev/{disk_name} is HDD; upgrade to SSD for 5-10x performance")
            elif dtype == "SATA SSD":
                result["bottleneck"] = True
                if result["severity"] in ("none", "low"):
                    result["severity"] = "medium"
                result["details"].append(f"/dev/{disk_name} is SATA SSD; upgrade to NVMe for up to 5x throughput")
            elif dtype == "NVMe Gen3":
                result["details"].append(f"/dev/{disk_name} is Gen3 NVMe; Gen4 offers 2x bandwidth")
            elif "USB" in dtype:
                result["details"].append(f"/dev/{disk_name} is USB drive; not ideal for system disk")

            if remaining < 50:
                result["bottleneck"] = True
                if result["severity"] in ("none", "low"):
                    result["severity"] = "high"
                result["details"].append(f"/dev/{disk_name} has only {remaining}% life remaining")
            elif remaining < 80:
                result["details"].append(f"/dev/{disk_name} at {remaining}% life remaining")

            smart_status = disk.get("smart_status", "")
            if smart_status == "FAILED":
                result["bottleneck"] = True
                result["severity"] = "critical"
                result["details"].append(f"/dev/{disk_name} SMART status FAILED; replace immediately!")

        return result

    def _detect_pcie_bottleneck(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "bottleneck": False,
            "severity": "none",
            "details": [],
        }

        gpu = self.results.get("gpu", {}).get("data", {})
        for g in gpu.get("gpus", []):
            pcie = g.get("pcie_info", {})
            width = pcie.get("width")
            max_width = pcie.get("max_width")
            speed = pcie.get("speed")
            max_speed = pcie.get("max_speed")
            if width and max_width and width != max_width:
                result["bottleneck"] = True
                result["severity"] = "medium"
                result["details"].append(
                    f"GPU running at {width} instead of {max_width}; PCIe bandwidth limited"
                )

        # Check NVMe PCIe width
        storage = self.results.get("storage", {}).get("data", {})
        for disk in storage.get("disks", []):
            pcie_width = disk.get("pcie_width", "")
            max_pcie_width = disk.get("max_pcie_width", "")
            if pcie_width and max_pcie_width and pcie_width != max_pcie_width:
                result["bottleneck"] = True
                result["severity"] = "medium"
                result["details"].append(
                    f"NVMe running at {pcie_width} instead of {max_pcie_width}"
                )

        return result

    def _detect_thermal_bottleneck(self) -> dict[str, Any]:
        cooling = self.results.get("cooling", {}).get("data", {})
        result: dict[str, Any] = {
            "bottleneck": False,
            "severity": "none",
            "details": [],
        }

        risk = cooling.get("throttling_risk", "None")
        if risk == "Critical":
            result["bottleneck"] = True
            result["severity"] = "critical"
            result["details"].append("Critical thermal throttling risk; system will significantly downclock")
        elif risk == "High":
            result["bottleneck"] = True
            result["severity"] = "high"
            result["details"].append("High thermal throttling risk; sustained loads will degrade performance")
        elif risk == "Moderate":
            result["bottleneck"] = True
            result["severity"] = "medium"
            result["details"].append("Moderate thermal risk; consider improving cooling")
        elif risk == "Low":
            result["details"].append("Low thermal risk; cooling is adequate")

        efficiency = cooling.get("cooling_efficiency", "Unknown")
        if efficiency == "Poor":
            result["bottleneck"] = True
            result["severity"] = "high"
            result["details"].append("Poor cooling efficiency; upgrade cooling solution recommended")
        elif efficiency == "Critical":
            result["bottleneck"] = True
            result["severity"] = "critical"
            result["details"].append("Cooling system failure imminent")

        return result

    def _detect_network_bottleneck(self) -> dict[str, Any]:
        net = self.results.get("network", {}).get("data", {})
        result: dict[str, Any] = {
            "bottleneck": False,
            "severity": "none",
            "details": [],
        }

        interfaces = net.get("interfaces", [])
        max_speed = 0
        for iface in interfaces:
            if not iface.get("is_loopback"):
                speed = iface.get("speed", 0)
                max_speed = max(max_speed, speed)

        if max_speed == 0:
            result["details"].append("Unable to determine network speeds")
        elif max_speed <= 100:
            result["bottleneck"] = True
            result["severity"] = "high"
            result["details"].append(f"Max link speed {max_speed} Mbps; upgrade to Gigabit Ethernet recommended")
        elif max_speed <= 1000:
            result["details"].append(f"Max link speed {max_speed} Mbps; adequate for general use")

        return result

    def _detect_power_bottleneck(self) -> dict[str, Any]:
        power = self.results.get("power", {}).get("data", {})
        result: dict[str, Any] = {
            "bottleneck": False,
            "severity": "none",
            "details": [],
        }

        governors = power.get("governors", {})
        current_gov = governors.get("current", "")
        if current_gov in ("powersave", "conservative"):
            result["details"].append(f"CPU governor set to '{current_gov}'; performance may be limited")
            result["bottleneck"] = True
            result["severity"] = "low"

        batteries = power.get("batteries", [])
        for bat in batteries:
            capacity = bat.get("capacity_pct", 100)
            if capacity < 50:
                result["bottleneck"] = True
                result["severity"] = "medium"
                result["details"].append(f"Battery at {capacity}% capacity; consider replacement")

        return result
