from __future__ import annotations

import os
import re
from typing import Any

from infrascope.collectors.base import BaseCollector, CollectorResult
from infrascope.core.dependency import check_binary, run_cmd


class GPUCollector(BaseCollector):
    name = "gpu"
    description = "Graphics processing unit information"

    def collect(self) -> CollectorResult:
        data: dict[str, Any] = {}
        gpus: list[dict[str, Any]] = []

        nvidia_gpus = self._get_nvidia_gpus()
        gpus.extend(nvidia_gpus)

        amd_gpus = self._get_amd_gpus()
        gpus.extend(amd_gpus)

        intel_gpus = self._get_intel_gpus()
        gpus.extend(intel_gpus)

        if not gpus:
            gpus = self._get_gpus_from_lspci()

        data["gpus"] = gpus
        data["count"] = len(gpus)
        data["has_nvidia"] = any(g.get("vendor", "").lower() == "nvidia" for g in gpus)
        data["has_amd"] = any(g.get("vendor", "").lower() == "amd" for g in gpus)
        data["has_intel"] = any(g.get("vendor", "").lower() == "intel" for g in gpus)

        for gpu in gpus:
            gpu["ai_capability"] = self._estimate_ai_capability(gpu)
            gpu["llm_capability"] = self._estimate_llm_capability(gpu)

        return CollectorResult(self.name, data)

    def _get_nvidia_gpus(self) -> list[dict[str, Any]]:
        gpus: list[dict[str, Any]] = []
        try:
            import GPUtil
            nvidia_gpus = GPUtil.getGPUs()
            for gpu in nvidia_gpus:
                info: dict[str, Any] = {
                    "vendor": "NVIDIA",
                    "model": gpu.name,
                    "driver": gpu.driver,
                    "serial": gpu.serial or "",
                    "uuid": gpu.uuid or "",
                    "vram_total_mb": gpu.memoryTotal,
                    "vram_used_mb": gpu.memoryUsed,
                    "vram_free_mb": gpu.memoryFree,
                    "vram_utilization": gpu.memoryUtil * 100,
                    "gpu_utilization": gpu.load * 100,
                    "temperature_c": gpu.temperature,
                    "power_watts": gpu.powerDraw if hasattr(gpu, 'powerDraw') else 0,
                    "max_power_watts": gpu.maxPowerDraw if hasattr(gpu, 'maxPowerDraw') else 0,
                }
                info["cuda_cores"] = self._estimate_cuda_cores(info["model"])
                info["tensor_cores"] = self._estimate_tensor_cores(info["model"])
                info["rt_cores"] = self._estimate_rt_cores(info["model"])
                info["memory_type"] = self._detect_vram_type(info["model"])
                info["pcie_info"] = self._get_gpu_pcie_info(info["model"])
                gpus.append(info)
        except (ImportError, Exception):
            lspci_output = run_cmd(["lspci", "-nnk"])
            if lspci_output:
                for block in lspci_output.split("\n\n"):
                    if "NVIDIA" in block or "nvidia" in block.lower():
                        info = self._parse_lspci_gpu(block)
                        if info:
                            nvidia_info = self._get_nvidia_smi_info()
                            info.update(nvidia_info)
                            info["vendor"] = "NVIDIA"
                            gpus.append(info)
        return gpus

    def _get_nvidia_smi_info(self) -> dict[str, Any]:
        info: dict[str, Any] = {}
        output = run_cmd(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu,utilization.memory,power.draw,power.limit,clocks.current.graphics,clocks.current.memory,driver_version", "--format=csv,noheader,nounits"])
        if output:
            try:
                lines = output.strip().split("\n")
                if lines and lines[0]:
                    parts = [p.strip() for p in lines[0].split(",")]
                    if len(parts) >= 8:
                        info["model"] = parts[0]
                        try:
                            info["vram_total_mb"] = int(float(parts[1]))
                            info["vram_used_mb"] = int(float(parts[2]))
                            info["vram_free_mb"] = int(float(parts[3]))
                        except (ValueError, IndexError):
                            pass
                        try:
                            info["temperature_c"] = float(parts[4])
                        except (ValueError, IndexError):
                            pass
                        try:
                            info["gpu_utilization"] = float(parts[5])
                            info["vram_utilization"] = float(parts[6])
                        except (ValueError, IndexError):
                            pass
                        try:
                            info["power_watts"] = float(parts[7])
                        except (ValueError, IndexError):
                            pass
                        try:
                            info["max_power_watts"] = float(parts[8])
                        except (ValueError, IndexError):
                            pass
                        try:
                            info["gpu_clock_mhz"] = float(parts[9])
                            info["memory_clock_mhz"] = float(parts[10])
                        except (ValueError, IndexError):
                            pass
                        if len(parts) > 11:
                            info["driver"] = parts[11]
            except (ValueError, IndexError):
                pass
        return info

    def _get_amd_gpus(self) -> list[dict[str, Any]]:
        gpus: list[dict[str, Any]] = []
        lspci_output = run_cmd(["lspci", "-nnk"])
        if lspci_output:
            for block in lspci_output.split("\n\n"):
                if "AMD" in block or "Advanced Micro Devices" in block:
                    if "VGA" in block or "3D controller" in block or "Display" in block:
                        info = self._parse_lspci_gpu(block)
                        if info:
                            info["vendor"] = "AMD"
                            info = self._get_amdgpu_info(info)
                            gpus.append(info)
        return gpus

    def _get_amdgpu_info(self, info: dict[str, Any]) -> dict[str, Any]:
        sysfs_path = "/sys/class/drm/"
        if os.path.isdir(sysfs_path):
            for card in sorted(os.listdir(sysfs_path)):
                if card.startswith("card"):
                    device_path = os.path.join(sysfs_path, card, "device")
                    if os.path.isdir(device_path):
                        vendor = ""
                        try:
                            with open(os.path.join(device_path, "vendor")) as f:
                                vendor = f.read().strip()
                        except OSError:
                            pass
                        if vendor == "0x1002":
                            try:
                                with open(os.path.join(device_path, "gpu_busy_percent")) as f:
                                    info["gpu_utilization"] = float(f.read().strip())
                            except (OSError, ValueError):
                                pass
                            try:
                                with open(os.path.join(device_path, "mem_busy_percent")) as f:
                                    info["vram_utilization"] = float(f.read().strip())
                            except (OSError, ValueError):
                                pass
                            try:
                                vram_path = os.path.join(device_path, "mem_info_vram_total")
                                with open(vram_path) as f:
                                    info["vram_total_mb"] = int(f.read().strip()) // (1024 * 1024)
                            except (OSError, ValueError):
                                pass
                            break
        return info

    def _get_intel_gpus(self) -> list[dict[str, Any]]:
        gpus: list[dict[str, Any]] = []
        lspci_output = run_cmd(["lspci", "-nnk"])
        if lspci_output:
            for block in lspci_output.split("\n\n"):
                if "Intel" in block or "intel" in block.lower():
                    if "VGA" in block or "3D controller" in block or "Display" in block:
                        info = self._parse_lspci_gpu(block)
                        if info:
                            info["vendor"] = "Intel"
                            gpus.append(info)
        return gpus

    def _get_gpus_from_lspci(self) -> list[dict[str, Any]]:
        gpus: list[dict[str, Any]] = []
        lspci_output = run_cmd(["lspci", "-nnk"])
        if lspci_output:
            for block in lspci_output.split("\n\n"):
                if "VGA" in block or "3D controller" in block or "Display" in block:
                    info = self._parse_lspci_gpu(block)
                    if info:
                        gpus.append(info)
        return gpus

    def _parse_lspci_gpu(self, block: str) -> dict[str, Any]:
        info: dict[str, Any] = {}
        lines = block.strip().split("\n")
        if not lines:
            return info
        first_line = lines[0]
        info["pci_id"] = first_line.split()[0] if first_line else ""
        rest = " ".join(first_line.split()[1:]) if first_line else ""
        if "[" in rest and "]" in rest:
            m = re.search(r"\[([^\]]*)\]", rest)
            if m:
                info["chipset"] = m.group(1)
        info["description"] = re.sub(r"\s*\[.*?\]\s*", " ", rest).strip()
        for line in lines[1:]:
            if "Kernel driver in use" in line:
                info["driver"] = line.split(":")[1].strip() if ":" in line else ""
            elif "Subsystem" in line:
                info["subsystem"] = line.split(":")[1].strip() if ":" in line else ""
        return info

    def _get_gpu_pcie_info(self, model: str) -> dict[str, Any]:
        info: dict[str, Any] = {"width": "unknown", "speed": "unknown", "version": "unknown"}
        output = run_cmd(["lspci", "-vvv"])
        if output:
            lines = output.split("\n")
            for i, line in enumerate(lines):
                if model.lower() in line.lower() or (model.split()[0] if model else "") in line:
                    for j in range(i, min(i + 10, len(lines))):
                        if "LnkSta:" in lines[j]:
                            m = re.search(r"Speed\s+(\d+[.]?\d*)\s*GT/s", lines[j])
                            if m:
                                info["speed"] = f"{m.group(1)} GT/s"
                            m = re.search(r"Width\s+x(\d+)", lines[j])
                            if m:
                                info["width"] = f"x{m.group(1)}"
                        if "LnkCap:" in lines[j]:
                            m = re.search(r"Speed\s+(\d+[.]?\d*)\s*GT/s", lines[j])
                            if m:
                                info["max_speed"] = f"{m.group(1)} GT/s"
                            m = re.search(r"Width\s+x(\d+)", lines[j])
                            if m:
                                info["max_width"] = f"x{m.group(1)}"
        return info

    def _estimate_cuda_cores(self, model: str) -> int:
        m = model.upper()
        if "RTX 4090" in m:
            return 16384
        if "RTX 4080" in m:
            return 9728
        if "RTX 4070" in m:
            return 5888
        if "RTX 4060" in m:
            return 3072
        if "RTX 3090" in m:
            return 10496
        if "RTX 3080" in m:
            return 8704
        if "RTX 3070" in m:
            return 5888
        if "RTX 3060" in m:
            return 3584
        if "RTX 2080" in m:
            return 4352
        if "RTX 2070" in m:
            return 2304
        if "A100" in m:
            return 6912
        if "A6000" in m:
            return 10752
        if "A5000" in m:
            return 8192
        if "A4000" in m:
            return 6144
        if "H100" in m:
            return 18432
        if "V100" in m:
            return 5120
        if "T4" in m:
            return 2560
        if "GTX 1080" in m or "GTX 1070" in m:
            return 2560
        if "GTX 1060" in m:
            return 1280
        return 0

    def _estimate_tensor_cores(self, model: str) -> int:
        m = model.upper()
        if "H100" in m:
            return 528
        if "RTX 4090" in m:
            return 512
        if "A100" in m:
            return 432
        if "RTX 4080" in m:
            return 304
        if "RTX 3090" in m:
            return 328
        if "RTX 3080" in m:
            return 272
        if "RTX 4070" in m:
            return 184
        if "RTX 3070" in m:
            return 184
        if "RTX 4060" in m:
            return 96
        if "RTX 3060" in m:
            return 112
        if "V100" in m:
            return 640
        if "T4" in m:
            return 320
        if "RTX 2080" in m:
            return 544
        if "RTX 2070" in m:
            return 288
        return 0

    def _estimate_rt_cores(self, model: str) -> int:
        m = model.upper()
        if "RTX 4090" in m:
            return 128
        if "RTX 4080" in m:
            return 76
        if "RTX 4070" in m:
            return 46
        if "RTX 4060" in m:
            return 24
        if "RTX 3090" in m:
            return 82
        if "RTX 3080" in m:
            return 68
        if "RTX 3070" in m:
            return 46
        if "RTX 3060" in m:
            return 28
        if "RTX 2080" in m:
            return 46
        if "RTX 2070" in m:
            return 36
        return 0

    def _detect_vram_type(self, model: str) -> str:
        m = model.upper()
        if any(x in m for x in ["RTX 4090", "RTX 4080", "RTX 4070", "RTX 4060", "RTX 3090", "RTX 3080"]):
            return "GDDR6X"
        if "RTX 3060" in m:
            return "GDDR6"
        if "A100" in m or "H100" in m:
            return "HBM2e"
        if "V100" in m:
            return "HBM2"
        return "GDDR6"

    def _estimate_ai_capability(self, gpu: dict[str, Any]) -> dict[str, bool]:
        model = gpu.get("model", "").upper()
        vram = gpu.get("vram_total_mb", 0)
        return {
            "llm_inference": vram >= 4096 or any(x in model for x in ["RTX", "A100", "H100", "V100", "T4"]),
            "stable_diffusion": vram >= 4096,
            "cuda_supported": "NVIDIA" in gpu.get("vendor", ""),
            "pytorch": vram >= 2048,
            "tensorflow": vram >= 2048,
            "blender": vram >= 4096,
            "video_editing": vram >= 4096,
            "gaming": vram >= 2048,
            "cad": vram >= 4096,
        }

    def _estimate_llm_capability(self, gpu: dict[str, Any]) -> dict[str, str]:
        vram_gb = gpu.get("vram_total_mb", 0) / 1024
        caps: dict[str, str] = {}
        if vram_gb >= 80:
            caps["llama_70b"] = "Excellent"
            caps["llama_13b"] = "Excellent"
            caps["llama_8b"] = "Excellent"
            caps["deepseek"] = "Excellent"
            caps["qwen_72b"] = "Excellent"
            caps["mistral"] = "Excellent"
            caps["mixtral"] = "Excellent"
        elif vram_gb >= 48:
            caps["llama_70b"] = "Good (quantized)"
            caps["llama_13b"] = "Excellent"
            caps["llama_8b"] = "Excellent"
            caps["deepseek"] = "Good (quantized)"
            caps["qwen_72b"] = "Limited"
            caps["mistral"] = "Excellent"
            caps["mixtral"] = "Good"
        elif vram_gb >= 24:
            caps["llama_70b"] = "Limited"
            caps["llama_13b"] = "Good"
            caps["llama_8b"] = "Excellent"
            caps["deepseek"] = "Limited"
            caps["qwen_72b"] = "Not Recommended"
            caps["mistral"] = "Excellent"
            caps["mixtral"] = "Good"
        elif vram_gb >= 12:
            caps["llama_70b"] = "Not Recommended"
            caps["llama_13b"] = "Acceptable (quantized)"
            caps["llama_8b"] = "Good"
            caps["deepseek"] = "Not Recommended"
            caps["qwen_72b"] = "Not Recommended"
            caps["mistral"] = "Good"
            caps["mixtral"] = "Acceptable"
            caps["stable_diffusion_xl"] = "Good"
            caps["whisper"] = "Good"
            caps["ollama"] = "Good"
        elif vram_gb >= 8:
            caps["llama_8b"] = "Acceptable (quantized)"
            caps["llama_13b"] = "Not Recommended"
            caps["mistral"] = "Acceptable"
            caps["stable_diffusion"] = "Acceptable"
            caps["whisper"] = "Acceptable"
            caps["ollama"] = "Acceptable"
        else:
            caps["llm"] = "Limited"
            caps["stable_diffusion"] = "Not Recommended"

        if "NVIDIA" in gpu.get("vendor", ""):
            caps["cuda"] = "Supported"
            caps["pytorch_cuda"] = "Yes"
            caps["tensorflow_gpu"] = "Yes"
        else:
            caps["cuda"] = "Not Supported"
            caps["pytorch_cuda"] = "No"
            caps["tensorflow_gpu"] = "No"

        caps["ollama"] = "Recommended" if vram_gb >= 8 else "Not Recommended"
        return caps
