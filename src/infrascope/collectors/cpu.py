from __future__ import annotations

import os
import re
from typing import Any

import cpuinfo
import psutil

from infrascope.collectors.base import BaseCollector, CollectorResult
from infrascope.core.dependency import run_cmd
from infrascope.utils.system import parse_cpuinfo, read_int_from_sysfs, read_sysfs


class CPUCollector(BaseCollector):
    name = "cpu"
    description = "CPU hardware information"

    def collect(self) -> CollectorResult:
        data: dict[str, Any] = {}
        info = cpuinfo.get_cpu_info()

        data["vendor"] = info.get("vendor_id_raw", info.get("vendor_id", "unknown"))
        data["brand"] = info.get("brand_raw", info.get("brand", "unknown"))
        data["arch"] = info.get("arch", os.uname().machine)
        data["bits"] = info.get("bits", 64)
        data["family"] = info.get("family", "")
        data["model"] = info.get("model", 0)
        data["stepping"] = info.get("stepping", 0)
        data["microcode"] = self._get_microcode()

        data["physical_cores"] = psutil.cpu_count(logical=False)
        data["logical_cores"] = psutil.cpu_count(logical=True)
        data["smt_enabled"] = data["logical_cores"] > data["physical_cores"]

        data["l1_cache"] = self._get_cache_size("l1")
        data["l2_cache"] = self._get_cache_size("l2")
        data["l3_cache"] = self._get_cache_size("l3")

        freqs = psutil.cpu_freq(percpu=False)
        if freqs:
            data["base_freq"] = freqs.min
            data["max_freq"] = freqs.max
            data["current_freq"] = freqs.current
        else:
            data["base_freq"] = 0.0
            data["max_freq"] = 0.0
            data["current_freq"] = 0.0

        data["governor"] = self._get_governor()
        data["scaling_driver"] = self._get_scaling_driver()

        data["numa_nodes"] = self._get_numa_count()
        data["sockets"] = self._get_socket_count()

        data["flags"] = info.get("flags", [])
        data["instruction_sets"] = self._detect_instruction_sets(data["flags"])

        data["virtualization"] = self._detect_virtualization(data["flags"])
        data["thermal_throttling"] = self._detect_thermal_throttling()

        data["class"] = self._estimate_cpu_class(data)

        data["lscpu"] = self._get_lscpu_output()

        return CollectorResult(self.name, data)

    def _get_microcode(self) -> str:
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "microcode" in line:
                        return line.split(":")[1].strip()
        except OSError:
            pass
        return ""

    def _get_cache_size(self, level: str) -> str:
        for cpu_dir in sorted(os.listdir("/sys/devices/system/cpu/")):
            if cpu_dir.startswith("cpu") and cpu_dir[3:].isdigit():
                cache_dir = f"/sys/devices/system/cpu/{cpu_dir}/cache"
                if os.path.isdir(cache_dir):
                    for idx in os.listdir(cache_dir):
                        idx_path = os.path.join(cache_dir, idx)
                        type_path = os.path.join(idx_path, "type")
                        if os.path.exists(type_path):
                            try:
                                with open(type_path) as f:
                                    cache_type = f.read().strip()
                                if cache_type.lower() == level:
                                    size_path = os.path.join(idx_path, "size")
                                    if os.path.exists(size_path):
                                        with open(size_path) as f:
                                            return f.read().strip()
                            except OSError:
                                pass
        return ""

    def _get_governor(self) -> str:
        path = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
        try:
            with open(path) as f:
                return f.read().strip()
        except OSError:
            return "unknown"

    def _get_scaling_driver(self) -> str:
        path = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver"
        try:
            with open(path) as f:
                return f.read().strip()
        except OSError:
            return "unknown"

    def _get_numa_count(self) -> int:
        if os.path.isdir("/sys/devices/system/node"):
            nodes = [d for d in os.listdir("/sys/devices/system/node/") if d.startswith("node")]
            return len(nodes)
        return 1

    def _get_socket_count(self) -> int:
        try:
            with open("/sys/devices/system/cpu/cpu0/topology/physical_package_id") as f:
                return int(f.read().strip()) + 1
        except (OSError, ValueError):
            sockets = set()
            cpu_info = parse_cpuinfo()
            for proc in cpu_info:
                if "physical id" in proc:
                    sockets.add(proc["physical id"])
            return max(len(sockets), 1)

    def _detect_instruction_sets(self, flags: list[str]) -> dict[str, bool]:
        flag_set = set(flags)
        return {
            "SSE": "sse" in flag_set,
            "SSE2": "sse2" in flag_set,
            "SSE3": "sse3" in flag_set,
            "SSSE3": "ssse3" in flag_set,
            "SSE4.1": "sse4_1" in flag_set,
            "SSE4.2": "sse4_2" in flag_set,
            "AVX": "avx" in flag_set,
            "AVX2": "avx2" in flag_set,
            "AVX512": any(f.startswith("avx512") for f in flag_set),
            "AES": "aes" in flag_set,
            "SHA": "sha" in flag_set or "sha_ni" in flag_set,
            "FMA": "fma" in flag_set,
            "FMA4": "fma4" in flag_set,
            "MMX": "mmx" in flag_set,
            "SSE4a": "sse4a" in flag_set,
            "BMI1": "bmi1" in flag_set,
            "BMI2": "bmi2" in flag_set,
            "F16C": "f16c" in flag_set,
            "MOVBE": "movbe" in flag_set,
            "RDRAND": "rdrand" in flag_set,
            "RDSEED": "rdseed" in flag_set,
            "SMAP": "smap" in flag_set,
            "SMEP": "smep" in flag_set,
            "SGX": "sgx" in flag_set,
            "AMX": "amx_bf16" in flag_set or "amx_tile" in flag_set,
        }

    def _detect_virtualization(self, flags: list[str]) -> dict[str, bool]:
        flag_set = set(flags)
        return {
            "VT-x": "vmx" in flag_set,
            "AMD-V": "svm" in flag_set,
            "Supported": "vmx" in flag_set or "svm" in flag_set,
        }

    def _detect_thermal_throttling(self) -> dict[str, Any]:
        throttling: dict[str, Any] = {"supported": False, "active": False, "thresholds": {}}
        for cpu_dir in sorted(os.listdir("/sys/devices/system/cpu/")):
            if cpu_dir.startswith("cpu") and cpu_dir[3:].isdigit():
                thermal_throttle = f"/sys/devices/system/cpu/{cpu_dir}/thermal_throttle"
                if os.path.isdir(thermal_throttle):
                    throttling["supported"] = True
                    for entry in os.listdir(thermal_throttle):
                        val = read_int_from_sysfs(f"{thermal_throttle}/{entry}")
                        if entry == "core_throttle_count" and val > 0:
                            throttling["active"] = True
                    break
        return throttling

    def _estimate_cpu_class(self, data: dict[str, Any]) -> str:
        cores = data.get("physical_cores", 0)
        threads = data.get("logical_cores", 0)
        max_freq = data.get("max_freq", 0) / 1_000_000
        brand = data.get("brand", "").lower()
        flags = data.get("flags", [])
        flag_set = set(flags)

        if threads >= 64 and max_freq >= 2.0:
            return "HPC"
        if threads >= 32:
            return "Server"
        if threads >= 16 and max_freq >= 3.0:
            return "Enterprise"
        if threads >= 12 and max_freq >= 3.5:
            if "epyc" in brand or "xeon" in brand or "threadripper" in brand:
                return "Workstation"
            return "High"
        if threads >= 8 and max_freq >= 3.0:
            return "High"
        if threads >= 4 and max_freq >= 2.5:
            if "avx512" in str(flags):
                return "Workstation"
            return "Mid"
        return "Entry"

    def _get_lscpu_output(self) -> dict[str, str]:
        output = run_cmd(["lscpu"])
        result: dict[str, str] = {}
        for line in output.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                result[key.strip()] = value.strip()
        return result
